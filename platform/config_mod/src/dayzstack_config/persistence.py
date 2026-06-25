"""Persist + retrieve ParsedConfig rows."""

from __future__ import annotations

from sqlalchemy import select

from dayzstack_shared.db import session_scope

from .models import ParsedConfigRow
from .types import ParsedConfig


async def upsert_parsed_config(parsed: ParsedConfig) -> tuple[int, bool]:
    """Insert if (file_hash, source_label) is novel, otherwise return existing.

    Returns (row_id, was_inserted).
    """
    async with session_scope() as session:
        existing = await session.scalar(
            select(ParsedConfigRow).where(
                ParsedConfigRow.file_hash == parsed.file_hash,
                ParsedConfigRow.source_label == parsed.source_label,
                ParsedConfigRow.config_type == parsed.config_type,
            )
        )
        if existing is not None:
            return existing.id, False

        row = ParsedConfigRow(
            config_type=parsed.config_type,
            source_label=parsed.source_label,
            source_path=parsed.source_path,
            parsed_data=parsed.data,
            raw_content=parsed.raw_content,
            file_hash=parsed.file_hash,
            metadata_=parsed.metadata,
        )
        session.add(row)
        await session.flush()
        return row.id, True


async def get_by_label(source_label: str, config_type: str | None = None) -> ParsedConfig | None:
    async with session_scope() as session:
        q = select(ParsedConfigRow).where(ParsedConfigRow.source_label == source_label)
        if config_type:
            q = q.where(ParsedConfigRow.config_type == config_type)
        q = q.order_by(ParsedConfigRow.parsed_at.desc()).limit(1)
        row = await session.scalar(q)
        if row is None:
            return None
        return ParsedConfig(
            config_type=row.config_type,
            source_label=row.source_label,
            source_path=row.source_path,
            raw_content=row.raw_content or "",
            data=row.parsed_data,
            metadata=row.metadata_ or {},
        )


async def list_known(config_type: str | None = None) -> list[dict]:
    async with session_scope() as session:
        q = select(ParsedConfigRow.id, ParsedConfigRow.config_type, ParsedConfigRow.source_label,
                   ParsedConfigRow.source_path, ParsedConfigRow.parsed_at)
        if config_type:
            q = q.where(ParsedConfigRow.config_type == config_type)
        q = q.order_by(ParsedConfigRow.config_type, ParsedConfigRow.source_label)
        result = await session.execute(q)
        return [
            {
                "id": r.id,
                "config_type": r.config_type,
                "source_label": r.source_label,
                "source_path": r.source_path,
                "parsed_at": r.parsed_at.isoformat(),
            }
            for r in result.all()
        ]


async def lookup_types_item(item_name: str, source_label: str | None = None) -> list[dict]:
    """Look up a types.xml item across known configs (or one specific config).

    Returns rows of (source_label, item dict).
    """
    async with session_scope() as session:
        q = select(ParsedConfigRow.source_label, ParsedConfigRow.parsed_data).where(
            ParsedConfigRow.config_type == "types_xml"
        )
        if source_label:
            q = q.where(ParsedConfigRow.source_label == source_label)
        result = await session.execute(q)

    out: list[dict] = []
    for label, data in result.all():
        items = (data or {}).get("items") or {}
        if item_name in items:
            out.append({"source_label": label, "item": items[item_name]})
    return out
