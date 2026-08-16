"""Pattern knowledge base.

One JSON file per failure signature, plus an index.  Designed to live on a
dedicated git branch of the repository, so there is no database or service for
maintainers to operate: `git log` is the audit trail and `git diff` shows what
changed in a given ingest.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path

SCHEMA_VERSION = "1.0"


@dataclass
class Pattern:
    signature: str
    signature_hash: str
    title: str
    schema_version: str = SCHEMA_VERSION
    count: int = 0
    first_seen: str = ""
    last_seen: str = ""
    tests: list[str] = field(default_factory=list)
    # Repo-relative source files the failures came from. This is what ties a
    # pattern to an in-tree skip marker, which is recorded per file.
    test_files: list[str] = field(default_factory=list)
    # Per-axis occurrence counts, e.g. {"distro": {"fedora-prior": 3}}.
    dimensions: dict[str, dict[str, int]] = field(default_factory=dict)
    recent_runs: list[dict] = field(default_factory=list)
    # Filled by the optional analysis layer.
    category: str = ""
    confidence: str = ""
    analysis: str = ""
    mitigation: str = ""
    linked_issues: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Pattern":
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)


class Store:
    """Read-modify-write access to the pattern knowledge base."""

    MAX_RECENT_RUNS = 10

    def __init__(self, root: str | Path = "flake-db"):
        self.root = Path(root)
        self.patterns_dir = self.root / "patterns"

    def load(self, sig_hash: str) -> Pattern | None:
        path = self.patterns_dir / f"{sig_hash}.json"
        if not path.exists():
            return None
        return Pattern.from_dict(json.loads(path.read_text()))

    def save(self, pattern: Pattern) -> None:
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
        path = self.patterns_dir / f"{pattern.signature_hash}.json"
        path.write_text(json.dumps(pattern.to_dict(), indent=2, sort_keys=True) + "\n")

    def all_patterns(self) -> list[Pattern]:
        if not self.patterns_dir.exists():
            return []
        out = []
        for p in sorted(self.patterns_dir.glob("*.json")):
            try:
                out.append(Pattern.from_dict(json.loads(p.read_text())))
            except (json.JSONDecodeError, TypeError):
                continue
        return out

    def record(self, rec, sig: str, sig_hash: str) -> tuple[Pattern, bool]:
        """Fold one FailureRecord into the knowledge base.

        Returns the updated pattern and whether it was newly created.
        """
        pattern = self.load(sig_hash)
        is_new = pattern is None
        if is_new:
            pattern = Pattern(
                signature=sig,
                signature_hash=sig_hash,
                title=rec.test_name[:120],
                first_seen=rec.created_at,
            )

        run_key = (rec.run_id, rec.dimensions.label())
        already = any(
            (r.get("run_id"), r.get("dimensions")) == run_key
            for r in pattern.recent_runs
        )
        if already:
            return pattern, False

        pattern.count += 1
        if rec.created_at:
            if not pattern.first_seen or rec.created_at < pattern.first_seen:
                pattern.first_seen = rec.created_at
            if rec.created_at > pattern.last_seen:
                pattern.last_seen = rec.created_at

        if rec.test_name and rec.test_name not in pattern.tests:
            pattern.tests.append(rec.test_name)

        # Store the file without its line number: a skip marker and a failure
        # rarely sit on the same line, but they do share the file.
        if rec.test_file:
            src = rec.test_file.split(":")[0]
            if src not in pattern.test_files:
                pattern.test_files.append(src)

        for axis in ("suite", "mode", "priv", "distro"):
            value = getattr(rec.dimensions, axis, "")
            if value:
                pattern.dimensions.setdefault(axis, {})
                pattern.dimensions[axis][value] = (
                    pattern.dimensions[axis].get(value, 0) + 1
                )

        pattern.recent_runs.insert(
            0,
            {
                "run_id": rec.run_id,
                "url": rec.run_url,
                "event": rec.run_event,
                "sha": rec.head_sha[:12],
                "created_at": rec.created_at,
                "dimensions": rec.dimensions.label(),
            },
        )
        del pattern.recent_runs[self.MAX_RECENT_RUNS :]

        self.save(pattern)
        return pattern, is_new

    def write_index(self, run_ids: list[int] | None = None) -> dict:
        patterns = self.all_patterns()

        # Coverage is tracked as the set of run IDs seen, not a running total.
        # Scheduled ingests re-scan overlapping windows, so counting runs would
        # inflate the figure every time the tool runs.
        seen: set[int] = set()
        index_path = self.root / "index.json"
        if index_path.exists():
            try:
                seen = set(json.loads(index_path.read_text()).get("run_ids", []))
            except json.JSONDecodeError:
                seen = set()
        seen.update(run_ids or [])

        index = {
            "schema_version": SCHEMA_VERSION,
            "pattern_count": len(patterns),
            "runs_scanned": len(seen),
            "run_ids": sorted(seen),
            "total_occurrences": sum(p.count for p in patterns),
            "categories": dict(
                Counter(p.category or "uncategorized" for p in patterns)
            ),
            "patterns": [
                {
                    "signature_hash": p.signature_hash,
                    "title": p.title,
                    "count": p.count,
                    "category": p.category,
                    "last_seen": p.last_seen,
                }
                for p in sorted(patterns, key=lambda x: -x.count)
            ],
        }
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n"
        )
        return index
