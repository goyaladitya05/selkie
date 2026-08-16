"""Markdown flake report."""

from __future__ import annotations

from datetime import datetime, timezone


def _dim_summary(pattern) -> str:
    """Render the dimensions a pattern was seen on.

    A pattern confined to one value of an axis is the interesting case: it
    means the flake is rootless-only, or debian-only, which is usually the
    first thing a maintainer wants to know.
    """
    parts = []
    for axis in ("suite", "mode", "priv", "distro"):
        vals = pattern.dimensions.get(axis) or {}
        if not vals:
            continue
        if len(vals) == 1:
            parts.append(f"**{next(iter(vals))}**")
        else:
            parts.append("/".join(sorted(vals)))
    return ", ".join(parts) or "-"


def render(patterns, *, repo: str, runs_scanned: int, window: str = "") -> str:
    patterns = sorted(patterns, key=lambda p: (-p.count, p.title))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    total = sum(p.count for p in patterns)
    categorized = [p for p in patterns for _ in [0] if p.category]

    out: list[str] = []
    out.append("# Podman CI flake report")
    out.append("")
    out.append(f"Generated {now} from `{repo}`.")
    out.append("")
    out.append(
        f"Scanned **{runs_scanned}** failed CI runs{window} and found "
        f"**{len(patterns)}** distinct failure patterns across "
        f"**{total}** occurrences."
    )
    out.append("")

    if not patterns:
        out.append("No failures ingested.")
        return "\n".join(out) + "\n"

    recurring = [p for p in patterns if p.count > 1]
    if recurring:
        out.append(
            f"**{len(recurring)}** pattern(s) occurred more than once; these are "
            "the strongest flake candidates."
        )
        out.append("")

    out.append("## Patterns by frequency")
    out.append("")
    out.append("| # | Count | Pattern | Dimensions | Category |")
    out.append("|---|-------|---------|------------|----------|")
    for i, p in enumerate(patterns, 1):
        title = p.title.replace("|", "\\|")[:80]
        cat = p.category or "_uncategorized_"
        out.append(
            f"| {i} | {p.count} | {title} | {_dim_summary(p)} | {cat} |"
        )
    out.append("")

    out.append("## Details")
    out.append("")
    for i, p in enumerate(patterns, 1):
        out.append(f"### {i}. {p.title}")
        out.append("")
        out.append(f"- **Occurrences:** {p.count}")
        out.append(f"- **Signature:** `{p.signature_hash}`")
        if p.first_seen:
            out.append(f"- **First seen:** {p.first_seen[:10]}")
        if p.last_seen:
            out.append(f"- **Last seen:** {p.last_seen[:10]}")
        out.append(f"- **Dimensions:** {_dim_summary(p)}")
        if p.linked_issues:
            issues = ", ".join(f"#{n}" for n in p.linked_issues)
            out.append(f"- **Known / tracked by:** {issues}")
        if p.category:
            conf = f" (confidence: {p.confidence})" if p.confidence else ""
            out.append(f"- **Category:** {p.category}{conf}")
        out.append("")

        if p.analysis:
            out.append(f"{p.analysis}")
            out.append("")
        if p.mitigation:
            out.append(f"**Suggested next step:** {p.mitigation}")
            out.append("")

        out.append("<details><summary>Normalized signature</summary>")
        out.append("")
        out.append("```")
        out.append(p.signature[:1200])
        out.append("```")
        out.append("")
        out.append("</details>")
        out.append("")

        if p.recent_runs:
            out.append("Recent runs:")
            out.append("")
            for r in p.recent_runs[:5]:
                dims = r.get("dimensions", "")
                url = r.get("url", "")
                event = r.get("event", "")
                when = (r.get("created_at") or "")[:10]
                out.append(f"- [{dims}]({url}) - {event}, {when}")
            out.append("")

    if categorized:
        out.append("## Category breakdown")
        out.append("")
        counts: dict[str, int] = {}
        for p in patterns:
            key = p.category or "uncategorized"
            counts[key] = counts.get(key, 0) + p.count
        out.append("| Category | Occurrences |")
        out.append("|----------|-------------|")
        for key, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            out.append(f"| {key} | {n} |")
        out.append("")

    return "\n".join(out) + "\n"


def render_stale_skips(markers) -> str:
    """Report skip markers with no matching recently-observed pattern."""
    if not markers:
        return ""
    out = ["## Skip markers with no recent matching failure", ""]
    out.append(
        "These tests are skipped for a tracked flake that was not observed in "
        "the scanned window. They may be candidates for re-enabling, but note "
        "that a skipped test cannot produce the failures this tool detects, so "
        "each needs a human check before removal."
    )
    out.append("")
    out.append("| Issue | File | Line |")
    out.append("|-------|------|------|")
    seen = set()
    for mk in sorted(markers, key=lambda m: m.issue):
        key = (mk.issue, mk.file)
        if key in seen:
            continue
        seen.add(key)
        out.append(f"| #{mk.issue} | `{mk.file}` | {mk.line} |")
    out.append("")
    return "\n".join(out)
