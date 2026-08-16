"""Optional agentic categorization layer.

Everything up to this point is deterministic.  This module is the only place a
model is involved, and it runs once per *unique* signature rather than once per
failure, so cost scales with distinct flakes rather than CI volume.

Model access goes through an OpenAI-compatible endpoint so a locally served
model works unchanged:

    ramalama serve qwen2.5-coder
    export SELKIE_LLM_BASE_URL=http://localhost:8080/v1
    selkie analyze

CI logs can carry hostnames, infrastructure detail and tokens leaked into error
output, so local serving is the default and hosted APIs are opt-in via
SELKIE_LLM_API_KEY.  With no endpoint configured the pipeline still works: every
pattern simply stays uncategorized.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

# Grounded in Podman's own flake history rather than invented. Each category
# names a real, recurring failure mode from the flakes-labeled issue corpus.
CATEGORIES = [
    "test-race",  # timing assumption in the test itself
    "product-race",  # genuine concurrency bug in Podman
    "network-registry",  # quay.io / registry / DNS flakiness
    "platform-specific",  # only on one distro or arch
    "storage-environment",  # composefs, overlay, disk state
    "infrastructure",  # runner, VM provisioning, image fetch
    "deterministic-regression",  # not a flake; real breakage
]

_PROMPT = """You are triaging a failure from Podman's CI.

Test: {title}
Observed {count} time(s). Dimensions seen: {dimensions}

Normalized failure signature:
{signature}

Sample error output:
{excerpt}

Classify the root cause into exactly one category:
{categories}

Note: "deterministic-regression" means this is NOT a flake but real breakage
that a re-run cannot fix. Use it when the evidence points to a genuine code
defect rather than a timing, environment or infrastructure problem.

Respond with a JSON object only, no prose, with keys:
  category    one of the categories above
  confidence  "high", "medium" or "low"
  analysis    two or three sentences explaining the likely root cause
  mitigation  one concrete suggested next step for a maintainer
"""


class NotConfigured(RuntimeError):
    pass


def _config() -> tuple[str, str, str]:
    base = os.environ.get("SELKIE_LLM_BASE_URL", "").rstrip("/")
    if not base:
        raise NotConfigured(
            "set SELKIE_LLM_BASE_URL to an OpenAI-compatible endpoint "
            "(e.g. http://localhost:8080/v1 for a locally served model)"
        )
    return (
        base,
        os.environ.get("SELKIE_LLM_MODEL", "local-model"),
        os.environ.get("SELKIE_LLM_API_KEY", ""),
    )


def available() -> bool:
    return bool(os.environ.get("SELKIE_LLM_BASE_URL"))


def categorize(pattern, excerpt: str = "") -> dict:
    """Ask the model to categorize one pattern. Returns {} on any failure.

    Failing soft is deliberate: a model being unreachable or returning
    malformed JSON must never cost us the deterministic bookkeeping that
    already succeeded.
    """
    base, model, api_key = _config()

    dims = ", ".join(
        f"{axis}={'/'.join(sorted(vals))}" for axis, vals in pattern.dimensions.items()
    ) or "none recorded"

    prompt = _PROMPT.format(
        title=pattern.title,
        count=pattern.count,
        dimensions=dims,
        signature=pattern.signature[:1500],
        excerpt=(excerpt or "not captured")[:1500],
        categories="\n".join(f"  - {c}" for c in CATEGORIES),
    )

    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 500,
        }
    ).encode()

    req = urllib.request.Request(f"{base}/chat/completions", data=body)
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read())
        content = payload["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError, OSError):
        return {}

    return _parse(content)


def _parse(content: str) -> dict:
    """Extract the JSON object from a model reply, tolerating code fences."""
    if "```" in content:
        parts = content.split("```")
        for part in parts:
            part = part.removeprefix("json").strip()
            if part.startswith("{"):
                content = part
                break

    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        data = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return {}

    category = str(data.get("category", "")).strip()
    if category not in CATEGORIES:
        category = ""

    return {
        "category": category,
        "confidence": str(data.get("confidence", "")).strip()[:16],
        "analysis": str(data.get("analysis", "")).strip()[:800],
        "mitigation": str(data.get("mitigation", "")).strip()[:800],
    }
