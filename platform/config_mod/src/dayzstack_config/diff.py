"""Diff between two ParsedConfigs of the same type.

types.xml diff is the priority case (every server modifies it; diffs are
the most useful single artifact). cfgspawnabletypes diff is a shallower
extension. Other formats fall back to a generic JSON diff.
"""

from __future__ import annotations

from typing import Any

from .types import ParsedConfig, TypesDiffEntry


# Fields we care about for types.xml semantic diff (ignoring extras_elements / passthrough)
_TYPES_COMPARE_FIELDS = (
    "nominal", "lifetime", "restock", "min", "quantmin", "quantmax", "cost",
    "category", "flags", "usages", "values", "tags",
)


def diff_types_xml(a: ParsedConfig, b: ParsedConfig) -> dict[str, Any]:
    """Diff two types.xml configs by item name.

    Returns:
      {
        "summary": {"added": N, "removed": N, "modified": N, "unchanged": N},
        "entries": [TypesDiffEntry, ...]   # sorted: removed, added, modified-by-impact
      }
    """
    if a.config_type != "types_xml" or b.config_type != "types_xml":
        raise ValueError("diff_types_xml requires both inputs to be types_xml")

    items_a = a.data.get("items") or {}
    items_b = b.data.get("items") or {}
    names_a = set(items_a)
    names_b = set(items_b)

    added = sorted(names_b - names_a)
    removed = sorted(names_a - names_b)
    common = names_a & names_b

    entries: list[TypesDiffEntry] = []

    for name in removed:
        entries.append(TypesDiffEntry(name=name, change="removed"))
    for name in added:
        entries.append(TypesDiffEntry(name=name, change="added"))

    modified_count = 0
    unchanged_count = 0
    for name in common:
        ia = items_a[name]
        ib = items_b[name]
        field_changes: dict[str, tuple[Any, Any]] = {}
        for field in _TYPES_COMPARE_FIELDS:
            va = ia.get(field)
            vb = ib.get(field)
            if va != vb:
                field_changes[field] = (va, vb)
        if field_changes:
            entries.append(TypesDiffEntry(name=name, change="modified", field_changes=field_changes))
            modified_count += 1
        else:
            unchanged_count += 1

    # Sort modified by # of changed fields (high-impact first), then alpha
    entries.sort(key=lambda e: (
        {"removed": 0, "added": 1, "modified": 2}[e.change],
        -len(e.field_changes),
        e.name,
    ))

    return {
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "modified": modified_count,
            "unchanged": unchanged_count,
            "label_a": a.source_label,
            "label_b": b.source_label,
        },
        "entries": [e.model_dump() for e in entries],
    }


def render_types_diff_markdown(diff: dict[str, Any], max_modified: int = 50) -> str:
    """Human-readable markdown rendering of a types.xml diff."""
    s = diff["summary"]
    out = [
        f"# types.xml diff — `{s['label_a']}` → `{s['label_b']}`",
        "",
        f"| Change | Count |",
        f"|---|---|",
        f"| Added items | {s['added']} |",
        f"| Removed items | {s['removed']} |",
        f"| Modified items | {s['modified']} |",
        f"| Unchanged items | {s['unchanged']} |",
        "",
    ]

    removed = [e for e in diff["entries"] if e["change"] == "removed"]
    added = [e for e in diff["entries"] if e["change"] == "added"]
    modified = [e for e in diff["entries"] if e["change"] == "modified"]

    if removed:
        out.append("## Removed")
        out.append("")
        for e in removed[:50]:
            out.append(f"- {e['name']}")
        if len(removed) > 50:
            out.append(f"- _...and {len(removed)-50} more_")
        out.append("")

    if added:
        out.append("## Added")
        out.append("")
        for e in added[:50]:
            out.append(f"- {e['name']}")
        if len(added) > 50:
            out.append(f"- _...and {len(added)-50} more_")
        out.append("")

    if modified:
        out.append(f"## Modified (top {min(max_modified, len(modified))} by impact)")
        out.append("")
        out.append("| Item | Field | From | To |")
        out.append("|---|---|---|---|")
        for e in modified[:max_modified]:
            for field, (va, vb) in e["field_changes"].items():
                out.append(f"| `{e['name']}` | {field} | `{va}` | `{vb}` |")
        if len(modified) > max_modified:
            out.append(f"\n_...and {len(modified) - max_modified} more modified items_")
        out.append("")

    return "\n".join(out)
