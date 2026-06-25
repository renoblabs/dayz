"""dayz-kb MCP server — exposes search/lookup/examples/get_source as tools.

Run via stdio (Claude Code):
    uv run python -m dayzstack_kb.mcp.server

Run via HTTP (Antigravity etc.):
    uv run python -m dayzstack_kb.mcp.server --transport sse --port 8765
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..search import hybrid_search

mcp = FastMCP("dayz-kb")


@mcp.tool()
async def search_enforce_docs(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Hybrid (BM25 + vector cosine, fused via RRF) search across all KB sources.

    Returns ranked chunks with source attribution. Use this for natural-language
    questions like 'how do I hook OnEntityKilled in CF' — it'll find both the
    canonical wiki page and real-world examples from open-source mods.

    Args:
        query: natural language or symbol-like search.
        limit: max hits to return (default 8).
    """
    hits = await hybrid_search(query, limit=limit)
    return [h.as_dict() for h in hits]


@mcp.tool()
async def lookup_class(name: str) -> dict[str, Any] | None:
    """Look up a class by exact name. Returns signature, parent, methods, examples.

    NOTE: symbol extraction is not yet implemented (Layer 1 v0.2 work).
    Returns None until the symbols table is populated.
    """
    # Placeholder until symbol extraction is wired up
    return None


@mcp.tool()
async def find_examples(pattern: str, source_filter: list[str] | None = None) -> list[dict[str, Any]]:
    """Find real-world examples matching a pattern. Search filtered by source type.

    Args:
        pattern: search query (acts like search but returns full chunks).
        source_filter: optional list of source_type values, e.g. ['github_mod_file', 'local_repo']
    """
    hits = await hybrid_search(pattern, limit=10, source_type_filter=source_filter)
    return [h.as_dict() for h in hits]


@mcp.tool()
async def lookup_config_item(config_type: str, item_name: str, source_label: str | None = None) -> list[dict[str, Any]]:
    """Look up an item across parsed DayZ configs (e.g. AKM nominal/lifetime values across types.xml variants).

    Args:
        config_type: 'types_xml' (most common), 'cfgspawnabletypes_xml', etc.
        item_name: exact item classname (case-sensitive — `AKM` not `akm`).
        source_label: optional, restrict to one parsed config.
    """
    try:
        from dayzstack_config.persistence import lookup_types_item  # noqa: PLC0415
    except ImportError:
        return [{"error": "config_mod package not installed; run `uv pip install -e ./config_mod`"}]
    if config_type != "types_xml":
        return [{"error": f"lookup_config_item currently only supports types_xml (got {config_type!r})"}]
    return await lookup_types_item(item_name, source_label)


@mcp.tool()
async def list_known_configs(config_type: str | None = None) -> list[dict[str, Any]]:
    """List parsed DayZ configs available in the KB.

    Pass config_type to filter ('types_xml', 'cfgspawnabletypes_xml', 'cfgeventspawns_xml',
    'expansion_json', etc.). Pass nothing to see all.
    """
    try:
        from dayzstack_config.persistence import list_known  # noqa: PLC0415
    except ImportError:
        return [{"error": "config_mod package not installed"}]
    return await list_known(config_type)


@mcp.tool()
async def compare_configs(label_a: str, label_b: str, config_type: str = "types_xml", max_modified: int = 30) -> dict[str, Any]:
    """Diff two parsed configs by source_label. Currently supports types_xml only.

    Returns a structured diff with summary + entry list (added/removed/modified items).
    For types.xml, modified entries include per-field (from, to) pairs.
    """
    try:
        from dayzstack_config.diff import diff_types_xml  # noqa: PLC0415
        from dayzstack_config.persistence import get_by_label  # noqa: PLC0415
    except ImportError:
        return {"error": "config_mod package not installed"}

    if config_type != "types_xml":
        return {"error": f"compare_configs currently supports only types_xml (got {config_type!r})"}

    a = await get_by_label(label_a, config_type)
    b = await get_by_label(label_b, config_type)
    if a is None:
        return {"error": f"label not found: {label_a}"}
    if b is None:
        return {"error": f"label not found: {label_b}"}

    diff = diff_types_xml(a, b)
    # Cap modified entries for response size
    diff["entries"] = diff["entries"][: 50 + diff["summary"]["added"] + diff["summary"]["removed"]]
    diff["entries"] = diff["entries"][:max_modified + diff["summary"]["added"] + diff["summary"]["removed"]]
    return diff


@mcp.tool()
async def get_source(url: str) -> dict[str, Any] | None:
    """Fetch the full cleaned text of a source by URL."""
    from sqlalchemy import select

    from dayzstack_shared.db import session_scope

    from ..models import Source

    async with session_scope() as session:
        src = await session.scalar(select(Source).where(Source.url == url).limit(1))
        if src is None:
            return None
        return {
            "url": src.url,
            "source_type": src.source_type,
            "title": src.title,
            "cleaned_text": src.cleaned_text,
            "metadata": src.metadata_,
            "fetched_at": src.fetched_at.isoformat(),
        }


def run_stdio() -> None:
    mcp.run()


def run_sse(host: str = "127.0.0.1", port: int = 8765) -> None:
    mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--sse":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
        run_sse(port=port)
    else:
        run_stdio()
