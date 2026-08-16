"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import analyze, report, skipmarkers
from .fingerprint import fingerprint
from .github import Client, DEFAULT_REPO, GitHubError
from .parse import parse_artifact_name, parse_log
from .store import Store


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def cmd_ingest(args) -> int:
    client = Client(repo=args.repo)
    store = Store(args.db)

    try:
        runs = client.failed_runs(limit=args.runs, event=args.event)
    except GitHubError as e:
        _log(f"error: {e}")
        return 1

    _log(f"found {len(runs)} failed runs in {args.repo}")

    seen_hashes: set[str] = set()
    new_patterns = 0
    total_failures = 0

    for i, run in enumerate(runs, 1):
        run_id = run["id"]
        _log(f"[{i}/{len(runs)}] run {run_id} ({run.get('event')})")

        try:
            artifacts = client.artifacts(run_id)
        except GitHubError as e:
            _log(f"  skipping: {e}")
            continue

        # Only the per-job .logs artifacts carry logformatter HTML.
        log_artifacts = [a for a in artifacts if a["name"].endswith(".logs")]
        if not log_artifacts:
            _log("  no log artifacts (expired or none produced)")
            continue

        for art in log_artifacts:
            dims = parse_artifact_name(art["name"])
            if args.suite and dims.suite != args.suite:
                continue
            try:
                files = client.download_logs(art["id"])
            except GitHubError as e:
                _log(f"  {art['name']}: {e}")
                continue

            for _, raw in files.items():
                records = parse_log(raw, dims)
                for rec in records:
                    rec.run_id = run_id
                    rec.run_url = run.get("html_url", "")
                    rec.run_event = run.get("event", "")
                    rec.head_sha = run.get("head_sha", "")
                    rec.created_at = run.get("created_at", "")

                    sig, sig_hash = fingerprint(rec)
                    pattern, is_new = store.record(rec, sig, sig_hash)
                    total_failures += 1
                    seen_hashes.add(sig_hash)
                    if is_new:
                        new_patterns += 1

            if files:
                n = sum(len(parse_log(r, dims)) for r in files.values())
                if n:
                    _log(f"  {art['name']}: {n} failure(s)")

        # Checkpoint after every run. Ingesting a full window takes a while and
        # can be cut short by a timeout or rate limit; the work already done
        # should survive, and the run count should stay truthful.
        index = store.write_index(run_ids=[run_id])

    index = store.write_index()
    _log("")
    _log(
        f"ingested {total_failures} failures into {len(seen_hashes)} distinct "
        f"patterns ({new_patterns} new); database now holds "
        f"{index['pattern_count']} patterns"
    )
    return 0


def cmd_link(args) -> int:
    store = Store(args.db)
    patterns = store.all_patterns()
    markers = skipmarkers.scan(args.podman)
    _log(f"scanned {len(markers)} skip markers in {args.podman}")

    links = skipmarkers.link_patterns(patterns, markers)
    for p in patterns:
        issues = links.get(p.signature_hash, [])
        if issues and issues != p.linked_issues:
            p.linked_issues = issues
            store.save(p)
    store.write_index()

    _log(f"linked {len(links)} pattern(s) to tracked issues")
    return 0


def cmd_analyze(args) -> int:
    store = Store(args.db)
    patterns = store.all_patterns()

    if not analyze.available():
        _log(
            "no model endpoint configured; set SELKIE_LLM_BASE_URL to enable "
            "categorization (patterns remain uncategorized)"
        )
        return 0

    todo = [p for p in patterns if not p.category or args.force]
    _log(f"categorizing {len(todo)} of {len(patterns)} pattern(s)")

    done = 0
    for p in todo:
        result = analyze.categorize(p)
        if not result.get("category"):
            _log(f"  {p.signature_hash}: no usable response, leaving uncategorized")
            continue
        p.category = result["category"]
        p.confidence = result.get("confidence", "")
        p.analysis = result.get("analysis", "")
        p.mitigation = result.get("mitigation", "")
        store.save(p)
        done += 1
        _log(f"  {p.signature_hash}: {p.category} ({p.confidence})")

    store.write_index()
    _log(f"categorized {done} pattern(s)")
    return 0


def cmd_report(args) -> int:
    store = Store(args.db)
    patterns = store.all_patterns()
    index_path = Path(args.db) / "index.json"
    runs_scanned = 0
    if index_path.exists():
        runs_scanned = json.loads(index_path.read_text()).get("runs_scanned", 0)

    md = report.render(patterns, repo=args.repo, runs_scanned=runs_scanned)

    if args.podman:
        markers = skipmarkers.scan(args.podman)
        stale = skipmarkers.stale_skips(markers, patterns)
        md += "\n" + report.render_stale_skips(stale)

    if args.output:
        Path(args.output).write_text(md)
        _log(f"wrote {args.output}")
    else:
        print(md)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="selkie",
        description="Flake triage for Podman's GitHub Actions CI.",
    )
    parser.add_argument("--repo", default=DEFAULT_REPO, help="owner/name to analyze")
    parser.add_argument("--db", default="flake-db", help="pattern database directory")

    # Repeat the global options on every subcommand so that both
    # "selkie --db X ingest" and "selkie ingest --db X" work. SUPPRESS keeps the
    # subparser from overwriting a value given before the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    common.add_argument("--db", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    sub = parser.add_subparsers(dest="command", required=True)

    p_ing = sub.add_parser(
        "ingest",
        help="fetch failed runs and fingerprint failures",
        parents=[common],
    )
    p_ing.add_argument("--runs", type=int, default=10, help="how many failed runs")
    p_ing.add_argument(
        "--event",
        choices=["push", "pull_request"],
        help="restrict to one trigger; 'push' means post-merge runs on main, "
        "the highest-precision flake signal",
    )
    p_ing.add_argument("--suite", help="restrict to one suite, e.g. int or sys")
    p_ing.set_defaults(func=cmd_ingest)

    p_link = sub.add_parser(
        "link", help="cross-reference in-tree skip markers", parents=[common]
    )
    p_link.add_argument("podman", help="path to a podman checkout")
    p_link.set_defaults(func=cmd_link)

    p_an = sub.add_parser(
        "analyze", help="categorize patterns with an LLM", parents=[common]
    )
    p_an.add_argument("--force", action="store_true", help="re-categorize everything")
    p_an.set_defaults(func=cmd_analyze)

    p_rep = sub.add_parser(
        "report", help="render the Markdown flake report", parents=[common]
    )
    p_rep.add_argument("-o", "--output", help="write to a file instead of stdout")
    p_rep.add_argument("--podman", help="podman checkout, to add stale-skip section")
    p_rep.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
