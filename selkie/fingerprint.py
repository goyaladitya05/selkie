"""Turn a failure into a stable signature.

Deduplication is deterministic on purpose: the same underlying flake must
collapse to one pattern no matter which run, PR, distro or privilege level it
surfaced on.  Doing this in plain code (rather than asking a model) keeps the
result reproducible and keeps model cost proportional to *unique* failures.

The rules below strip the tokens that vary between two runs of the same flake.
They are deliberately Podman-specific: the container/pod names, socket paths and
BATS temp dirs below are the noise this project's logs actually contain.
"""

from __future__ import annotations

import hashlib
import re

# Order matters: earlier rules are more specific than later ones.
_NORMALIZERS: list[tuple[re.Pattern, str]] = [
    # Timestamps: "08/15/26 20:38:15.857", "2026-08-14T12:19:41Z", "[12:19:41]"
    (re.compile(r"\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?"), "<TIME>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?"), "<TIME>"),
    (re.compile(r"\[\d{2}:\d{2}:\d{2}\]"), "<TIME>"),
    # Durations: "in 10466ms", "[10.082 seconds]", "(9.646s)", "<+622ms>"
    (re.compile(r"\b\d+(?:\.\d+)?\s*(?:ms|s|seconds|sec)\b"), "<DUR>"),
    (re.compile(r"<\+\s*[\d.]+\s*\w*>"), "<DUR>"),
    # Go stack-trace addresses and offsets
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<ADDR>"),
    # Full and short container/image IDs
    (re.compile(r"\b[0-9a-f]{64}\b"), "<SHA256>"),
    (re.compile(r"\b[0-9a-f]{12,63}\b"), "<ID>"),
    # Paths first: the checkout prefix contains hyphenated words that the
    # random-suffix rule below would otherwise mangle inconsistently.
    (re.compile(r"/tmp/CI_\w+"), "/tmp/CI_<RAND>"),
    (re.compile(r"podman_bats\.\w+"), "podman_bats.<RAND>"),
    (re.compile(r"/var/tmp/[\w.-]+/podman/"), ""),
    (re.compile(r"/home/[^/\s]+/"), "/<HOME>/"),
    # Podman test resource names carry a random suffix, e.g.
    # "c-ltfu-t93-uxvehj2c", "podman-build-secret-3514236085"
    (re.compile(r"\b([a-zA-Z][\w-]*?)-[0-9a-z]{6,}\b"), r"\1-<RAND>"),
    # Ports and PIDs
    (re.compile(r":\d{4,5}\b"), ":<PORT>"),
    (re.compile(r"\bpid[= ]\d+\b", re.I), "pid=<PID>"),
    # Any remaining bare numbers (line numbers, counters, byte sizes)
    (re.compile(r"\b\d+\b"), "<N>"),
    # Collapse whitespace last
    (re.compile(r"\s+"), " "),
]


def normalize(text: str) -> str:
    """Strip run-to-run variable tokens from an error excerpt."""
    out = text.strip()
    for pattern, repl in _NORMALIZERS:
        out = pattern.sub(repl, out)
    return out.strip()


def signature(test_name: str, error_excerpt: str) -> str:
    """Build the human-readable signature string for a failure.

    The test identity is included alongside the normalized error so that the
    same generic message ("Command failed with exit status 125") occurring in
    two unrelated tests does not collapse into a single pattern.
    """
    return f"{normalize(test_name)}|{normalize(error_excerpt)}"


def signature_hash(sig: str) -> str:
    return hashlib.sha256(sig.encode("utf-8")).hexdigest()[:16]


def fingerprint(record) -> tuple[str, str]:
    """Return (signature, signature_hash) for a FailureRecord."""
    sig = signature(record.test_name, record.error_excerpt)
    return sig, signature_hash(sig)
