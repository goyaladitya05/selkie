"""Cross-reference the pattern database against in-tree skip markers.

Podman already tracks known flakes in the source tree: tests carry markers like

    skip "FIXME #27759: There is a selinux problem with this test"
    skip_if_aarch64 "FIXME #28576: selinux problem only on aarch64"

and hack/ci/pr-removes-fixed-skips enforces that a PR closing an issue also
removes the matching skip.  Reading those markers lets the tool answer two
questions no log-only view can:

  1. Is this newly observed pattern already known and tracked?  If so, annotate
     it instead of filing a duplicate issue.
  2. Has a tracked flake stopped firing?  If so, its skip may now be removable,
     which turns the weekly report into a tool for shrinking the skip list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Matches an issue reference in a skip or FIXME comment, in .go and .bats alike.
_MARKER_RE = re.compile(
    r"(?P<kind>skip\w*|FIXME|Skip)\b[^\n]{0,80}?#(?P<issue>\d{4,6})", re.IGNORECASE
)

_TEST_DIRS = ("test/e2e", "test/system", "test/upgrade", "test/farm")


@dataclass
class SkipMarker:
    issue: int
    file: str
    line: int
    text: str


def scan(podman_root: str | Path) -> list[SkipMarker]:
    """Collect every issue-referencing skip/FIXME marker under test/."""
    root = Path(podman_root)
    markers: list[SkipMarker] = []

    for rel in _TEST_DIRS:
        d = root / rel
        if not d.is_dir():
            continue
        for path in sorted(list(d.rglob("*.go")) + list(d.rglob("*.bats"))):
            try:
                lines = path.read_text(errors="replace").splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines, 1):
                m = _MARKER_RE.search(line)
                if m:
                    markers.append(
                        SkipMarker(
                            issue=int(m.group("issue")),
                            file=str(path.relative_to(root)),
                            line=n,
                            text=line.strip()[:200],
                        )
                    )
    return markers


def link_patterns(patterns, markers: list[SkipMarker]) -> dict[str, list[int]]:
    """Map each pattern to issue numbers whose skip marker sits in the same file.

    File-level matching is intentional. A skip marker guards a test that no
    longer runs, so the flake it describes cannot produce failures under that
    exact name; the reliable association is the test file they share.
    """
    by_file: dict[str, set[int]] = {}
    for mk in markers:
        by_file.setdefault(mk.file, set()).add(mk.issue)

    links: dict[str, list[int]] = {}
    for p in patterns:
        found: set[int] = set()
        for src in getattr(p, "test_files", []):
            for f, issues in by_file.items():
                # Compare on basename so a marker recorded as
                # "test/system/035-logs.bats" still matches a failure whose
                # path was captured relative to a different checkout root.
                if Path(f).name == Path(src).name:
                    found |= issues
        if found:
            links[p.signature_hash] = sorted(found)
    return links


def stale_skips(
    markers: list[SkipMarker], patterns, window_days: int = 90
) -> list[SkipMarker]:
    """Markers whose issue is not backed by any recently seen pattern.

    These are candidates for removal: the flake they guard against has not been
    observed in the ingested window. A human still confirms before deleting,
    since a skip also suppresses the very failures we would detect.
    """
    live_issues: set[int] = set()
    for p in patterns:
        live_issues.update(p.linked_issues)
    return [mk for mk in markers if mk.issue not in live_issues]
