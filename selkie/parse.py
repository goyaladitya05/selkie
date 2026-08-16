"""Parsers for Podman's logformatter HTML output.

Podman pipes every CI test job through hack/ci/logformatter, which turns raw
Ginkgo (test/e2e) and BATS (test/system) output into HTML.  We strip the markup
and parse the underlying text, because logformatter's own classes mark only a
subset of failures reliably; the text shapes below are stable and cover both.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field, asdict
from typing import Iterator

# Artifact names look like "{test}-{mode}-{priv}-{distro}.logs", where mode and
# priv are empty for suites that do not vary along those axes (build, unit).
ARTIFACT_RE = re.compile(
    r"^(?P<suite>[a-z_]+)-(?P<mode>local|remote|)-(?P<priv>root|rootless|)-(?P<distro>[a-z0-9._-]+?)(?:\.logs)?$"
)

_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Dimensions:
    """The analysis axes encoded in a log artifact's name."""

    suite: str = ""
    mode: str = ""
    priv: str = ""
    distro: str = ""

    def label(self) -> str:
        return "-".join(p for p in (self.suite, self.mode, self.priv, self.distro) if p)


@dataclass
class FailureRecord:
    """One failed test, extracted from one log artifact."""

    test_name: str
    suite_name: str = ""
    test_file: str = ""
    error_excerpt: str = ""
    dimensions: Dimensions = field(default_factory=Dimensions)
    run_id: int = 0
    run_url: str = ""
    run_event: str = ""
    head_sha: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["dimensions"] = asdict(self.dimensions)
        return d


def parse_artifact_name(name: str) -> Dimensions:
    """Split an artifact name into its analysis dimensions."""
    m = ARTIFACT_RE.match(name.removesuffix(".logs"))
    if not m:
        return Dimensions(suite=name.removesuffix(".logs"))
    return Dimensions(**m.groupdict())


def strip_html(raw: str) -> str:
    """Recover the plain test log from logformatter's HTML."""
    return html.unescape(_TAG_RE.sub("", raw))


# --------------------------------------------------------------------------
# Ginkgo (test/e2e)
# --------------------------------------------------------------------------

# Ginkgo prints a block header per failure. logformatter prefixes each line
# with an elapsed-time marker, so the bullet is not at the start of the line:
#     [+0350s] • [FAILED] [10.082 seconds]
#     Podman build
#     /path/to/test/e2e/build_test.go:22
#       [It] podman build with a secret from file
#       /path/to/test/e2e/build_test.go:92
_GINKGO_HEADER_RE = re.compile(
    r"^(?:\[\+[^\]\n]*\]\s*)?[•*]\s*\[FAILED\].*?\n"
    r"(?P<suite>.+?)\n"
    r"\s*(?P<suite_loc>\S*?test/e2e/\S+?:\d+)\s*\n"
    r"\s*\[It\]\s*(?P<test>.+?)\n"
    r"\s*(?P<test_loc>\S*?test/e2e/\S+?:\d+)",
    re.MULTILINE,
)

# The assertion itself appears later inside the block:
#     [FAILED] Command failed with exit status 125. See above for error message.
#     In [It] at: /path/test/e2e/build_test.go:116 @ 08/15/26 20:38:15.857
_GINKGO_DETAIL_RE = re.compile(
    r"^\s*\[FAILED\]\s*(?P<message>.+?)\n\s*In \[\w+\] at:\s*(?P<where>\S+:\d+)",
    re.MULTILINE | re.DOTALL,
)


def parse_ginkgo(text: str) -> Iterator[FailureRecord]:
    """Yield a FailureRecord per Ginkgo failure block."""
    starts = [m for m in _GINKGO_HEADER_RE.finditer(text)]
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        block = text[m.end() : end]

        detail = _GINKGO_DETAIL_RE.search(block)
        if detail:
            excerpt = detail.group("message").strip()
            where = detail.group("where")
        else:
            # No assertion line (panic, timeout, interrupted run). Fall back to
            # the first few non-empty lines so the failure is still fingerprinted.
            excerpt = "\n".join(
                ln.strip() for ln in block.splitlines() if ln.strip()
            )[:600]
            where = m.group("test_loc")

        yield FailureRecord(
            test_name=m.group("test").strip(),
            suite_name=m.group("suite").strip(),
            test_file=_repo_relative(where),
            error_excerpt=excerpt[:2000],
        )


# --------------------------------------------------------------------------
# BATS (test/system)
# --------------------------------------------------------------------------

# BATS/TAP prints:
#     not ok 93 |035| podman logs - --until --follow journald in 10466ms
# followed by "#"-prefixed diagnostic lines until the next ok/not ok.
_BATS_FAIL_RE = re.compile(
    r"^\s*not ok\s+(?P<num>\d+)\s*(?:\|(?P<file>[^|]*)\|)?\s*(?P<test>.+?)"
    r"(?:\s+in\s+\d+ms)?\s*$",
    re.MULTILINE,
)
_BATS_NEXT_RE = re.compile(r"^\s*(?:not ok|ok)\s+\d+", re.MULTILINE)

# The most useful diagnostic line is the one naming the failed assertion:
#     #   `_log_test_follow_until journald' failed
_BATS_CAUSE_RE = re.compile(r"^\s*#\s+`(?P<cmd>.+?)'\s+failed(?P<rest>.*)$", re.MULTILINE)
# ... and the test file it came from:
#     #  in test file test/system/035-logs.bats, line 399)
_BATS_INFILE_RE = re.compile(
    r"in test file (?P<file>\S+\.bats), line (?P<line>\d+)", re.MULTILINE
)


def parse_bats(text: str) -> Iterator[FailureRecord]:
    """Yield a FailureRecord per BATS failure."""
    for m in _BATS_FAIL_RE.finditer(text):
        nxt = _BATS_NEXT_RE.search(text, m.end())
        block = text[m.end() : nxt.start() if nxt else len(text)]

        diag = [
            ln.strip()[1:].strip()
            for ln in block.splitlines()
            if ln.strip().startswith("#")
        ]

        cause = _BATS_CAUSE_RE.search(block)
        infile = _BATS_INFILE_RE.search(block)

        if cause:
            excerpt = f"`{cause.group('cmd')}' failed{cause.group('rest').rstrip()}"
        else:
            excerpt = "\n".join(diag[:12])

        test_file = ""
        if infile:
            test_file = f"{infile.group('file')}:{infile.group('line')}"
        elif m.group("file"):
            test_file = m.group("file").strip()

        yield FailureRecord(
            test_name=m.group("test").strip(),
            suite_name=(m.group("file") or "").strip(),
            test_file=_repo_relative(test_file),
            error_excerpt=excerpt[:2000],
        )


# --------------------------------------------------------------------------


def _repo_relative(path: str) -> str:
    """Trim CI checkout prefixes so paths compare across runners."""
    if not path:
        return ""
    for marker in ("/test/", "/pkg/", "/libpod/", "/cmd/"):
        idx = path.find(marker)
        if idx != -1:
            return path[idx + 1 :]
    return path


def parse_log(raw_html: str, dimensions: Dimensions) -> list[FailureRecord]:
    """Parse one log artifact, dispatching on suite.

    Both parsers are run for unknown suites; each is anchored on a distinct
    line shape, so running both is safe and costs one extra scan.
    """
    text = strip_html(raw_html)

    if dimensions.suite == "int":
        records = list(parse_ginkgo(text))
    elif dimensions.suite == "sys":
        records = list(parse_bats(text))
    else:
        records = list(parse_ginkgo(text)) + list(parse_bats(text))

    for r in records:
        r.dimensions = dimensions
    return records
