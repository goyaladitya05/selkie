"""Minimal GitHub Actions API client.

Standard library only, so the tool runs on any machine with Python and a token
and needs no pip install.  Auth comes from GITHUB_TOKEN, GH_TOKEN, or whatever
`gh auth token` reports, in that order.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

API = "https://api.github.com"
DEFAULT_REPO = "podman-container-tools/podman"
CI_WORKFLOW = "ci.yml"


class GitHubError(RuntimeError):
    pass


class _StripAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Drop credentials when a redirect leaves the GitHub API host.

    Artifact downloads 302 to blob storage, which rejects a request carrying a
    GitHub Authorization header with 401. urllib replays every header on the
    redirected request by default, so it has to be removed explicitly.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            old_host = urllib.parse.urlsplit(req.full_url).netloc
            if urllib.parse.urlsplit(newurl).netloc != old_host:
                new.remove_header("Authorization")
        return new


_OPENER = urllib.request.build_opener(_StripAuthOnRedirect)


def _token() -> str:
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        out = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=10
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    raise GitHubError(
        "no GitHub token found: set GITHUB_TOKEN or run `gh auth login`"
    )


class Client:
    def __init__(self, repo: str = DEFAULT_REPO, token: str | None = None):
        self.repo = repo
        self.token = token or _token()

    def _request(self, url: str, raw: bool = False):
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "selkie")

        for attempt in range(4):
            try:
                with _OPENER.open(req, timeout=120) as resp:
                    body = resp.read()
                    return body if raw else json.loads(body)
            except urllib.error.HTTPError as e:
                # Secondary rate limits and transient 5xx are worth retrying.
                if e.code in (403, 429, 500, 502, 503) and attempt < 3:
                    reset = e.headers.get("x-ratelimit-reset")
                    delay = 2 ** attempt
                    if e.code in (403, 429) and reset:
                        delay = max(delay, min(int(reset) - int(time.time()) + 1, 120))
                    time.sleep(delay)
                    continue
                raise GitHubError(f"{e.code} {e.reason} for {url}") from e
        raise GitHubError(f"giving up on {url}")

    def _get(self, path: str, **params):
        if params:
            path = f"{path}?{urllib.parse.urlencode(params)}"
        return self._request(f"{API}/repos/{self.repo}/{path}")

    def failed_runs(self, limit: int = 20, event: str | None = None) -> list[dict]:
        """Most recent failed ci.yml runs, newest first.

        `event="push"` selects post-merge runs, the highest-precision flake
        signal this repo has: that code already passed the identical suite on
        its pull request, so a failure on main is very unlikely to be a real
        regression.
        """
        runs: list[dict] = []
        page = 1
        while len(runs) < limit:
            params = {
                "status": "failure",
                "per_page": min(100, limit - len(runs)),
                "page": page,
            }
            if event:
                params["event"] = event
            batch = self._get(
                f"actions/workflows/{CI_WORKFLOW}/runs", **params
            ).get("workflow_runs", [])
            if not batch:
                break
            runs.extend(batch)
            page += 1
        return runs[:limit]

    def failed_jobs(self, run_id: int) -> list[dict]:
        jobs = self._get(f"actions/runs/{run_id}/jobs", per_page=100).get("jobs", [])
        return [j for j in jobs if j.get("conclusion") == "failure"]

    def artifacts(self, run_id: int) -> list[dict]:
        arts = self._get(f"actions/runs/{run_id}/artifacts", per_page=100).get(
            "artifacts", []
        )
        return [a for a in arts if not a.get("expired")]

    def download_logs(self, artifact_id: int) -> dict[str, str]:
        """Download a .logs artifact and return {filename: text} for its HTML."""
        blob = self._request(
            f"{API}/repos/{self.repo}/actions/artifacts/{artifact_id}/zip", raw=True
        )
        out: dict[str, str] = {}
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            for name in zf.namelist():
                if name.endswith(".html"):
                    out[name] = zf.read(name).decode("utf-8", errors="replace")
        return out
