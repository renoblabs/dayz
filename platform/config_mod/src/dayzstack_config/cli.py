"""dayz-stack-config CLI."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click

from dayzstack_shared.logging import setup_logging

from .registry import PARSERS, get_parser


@click.group()
def main() -> None:
    """dayz-stack config-management CLI."""
    setup_logging()


@main.command("parse")
@click.option("--type", "config_type", required=True, type=click.Choice(sorted(PARSERS)))
@click.option("--file", "file_path", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--label", "source_label", required=True)
@click.option("--validate/--no-validate", default=True)
def parse_cmd(config_type: str, file_path: str, source_label: str, validate: bool) -> None:
    """Parse one config file, persist to DB, print summary."""
    from .persistence import upsert_parsed_config

    async def _run() -> None:
        parser = get_parser(config_type)
        parsed = parser.parse_file(Path(file_path), source_label=source_label)
        if validate:
            issues = parser.validate(parsed)
            parsed.issues.extend(issues)
        row_id, was_new = await upsert_parsed_config(parsed)
        click.echo(json.dumps({
            "row_id": row_id,
            "was_new": was_new,
            "config_type": parsed.config_type,
            "source_label": parsed.source_label,
            "metadata": parsed.metadata,
            "issue_count": len(parsed.issues),
            "first_3_issues": [i.model_dump() for i in parsed.issues[:3]],
        }, indent=2))

    asyncio.run(_run())


@main.command("list")
@click.option("--type", "config_type", default=None, type=click.Choice(sorted(PARSERS)))
def list_cmd(config_type: str | None) -> None:
    """List known parsed configs in the DB."""
    from .persistence import list_known

    async def _run() -> None:
        rows = await list_known(config_type)
        for r in rows:
            click.echo(f"  [{r['config_type']:<22}] {r['source_label']:<40} (id {r['id']})")
        if not rows:
            click.echo("(none — run `parse` or `ingest-defaults` first)")

    asyncio.run(_run())


@main.command("show")
@click.option("--label", "source_label", required=True)
@click.option("--type", "config_type", default=None)
@click.option("--limit-items", default=5, help="Max items to print for large configs")
def show_cmd(source_label: str, config_type: str | None, limit_items: int) -> None:
    """Print a parsed config (truncated)."""
    from .persistence import get_by_label

    async def _run() -> None:
        parsed = await get_by_label(source_label, config_type)
        if parsed is None:
            click.echo("(not found)", err=True)
            sys.exit(1)
        # Truncate large item dicts
        data = dict(parsed.data)
        if "items" in data and isinstance(data["items"], dict) and len(data["items"]) > limit_items:
            shown = dict(list(data["items"].items())[:limit_items])
            data["items"] = {**shown, "...": f"({len(parsed.data['items']) - limit_items} more truncated)"}
        click.echo(json.dumps({
            "config_type": parsed.config_type,
            "source_label": parsed.source_label,
            "source_path": parsed.source_path,
            "metadata": parsed.metadata,
            "data_preview": data,
        }, indent=2, default=str))

    asyncio.run(_run())


@main.command("diff")
@click.option("--label-a", required=True)
@click.option("--label-b", required=True)
@click.option("--type", "config_type", required=True, type=click.Choice(sorted(PARSERS)))
@click.option("--format", "out_format", default="markdown", type=click.Choice(["markdown", "json"]))
@click.option("--max-modified", default=50)
def diff_cmd(label_a: str, label_b: str, config_type: str, out_format: str, max_modified: int) -> None:
    """Diff two parsed configs by source_label."""
    from .diff import diff_types_xml, render_types_diff_markdown
    from .persistence import get_by_label

    async def _run() -> None:
        a = await get_by_label(label_a, config_type)
        b = await get_by_label(label_b, config_type)
        if a is None:
            click.echo(f"label not found: {label_a}", err=True); sys.exit(1)
        if b is None:
            click.echo(f"label not found: {label_b}", err=True); sys.exit(1)

        if config_type == "types_xml":
            d = diff_types_xml(a, b)
            if out_format == "json":
                click.echo(json.dumps(d, indent=2, default=str))
            else:
                click.echo(render_types_diff_markdown(d, max_modified=max_modified))
        else:
            click.echo(f"diff for config_type={config_type} not yet implemented (only types_xml)", err=True)
            sys.exit(2)

    asyncio.run(_run())


# Reference configs we know how to ingest from the github_mods scraper-cache
_DEFAULTS = [
    # (config_type, source_label, glob from scraper-cache root)
    ("types_xml", "vanilla_chernarus_2025",
     "github/BohemiaInteractive__DayZ-Central-Economy/dayzOffline.chernarusplus/db/types.xml"),
    ("types_xml", "vanilla_livonia_2025",
     "github/BohemiaInteractive__DayZ-Central-Economy/dayzOffline.enoch/db/types.xml"),
    ("types_xml", "vanilla_sakhal_2025",
     "github/BohemiaInteractive__DayZ-Central-Economy/dayzOffline.sakhal/db/types.xml"),
    ("cfgspawnabletypes_xml", "vanilla_chernarus_2025",
     "github/BohemiaInteractive__DayZ-Central-Economy/dayzOffline.chernarusplus/cfgspawnabletypes.xml"),
    ("cfgspawnabletypes_xml", "vanilla_livonia_2025",
     "github/BohemiaInteractive__DayZ-Central-Economy/dayzOffline.enoch/cfgspawnabletypes.xml"),
    ("cfgeventspawns_xml", "vanilla_chernarus_2025",
     "github/BohemiaInteractive__DayZ-Central-Economy/dayzOffline.chernarusplus/cfgeventspawns.xml"),
    ("cfgeventspawns_xml", "vanilla_livonia_2025",
     "github/BohemiaInteractive__DayZ-Central-Economy/dayzOffline.enoch/cfgeventspawns.xml"),
    # Christmas variants — useful diff target ("vanilla balanced" vs "event-modified")
    ("types_xml", "christmas_chernarus_2025",
     "github/BohemiaInteractive__DayZ-Central-Economy/ChristmasOffline.ChernarusPlus/db/types.xml"),
    # Sample Expansion JSONs (Credits is small but proves the parser)
    ("expansion_json", "expansion_credits",
     "github/salutesh__DayZ-Expansion-Scripts/DayZExpansion/Core/Scripts/Data/Credits.json"),
]


@main.command("ingest-defaults")
@click.option("--cache-root", default="scraper-cache", help="Root dir holding github_mods clones")
def ingest_defaults_cmd(cache_root: str) -> None:
    """Bulk-ingest known reference configs from the scraper cache."""
    from .persistence import upsert_parsed_config

    cache = Path(cache_root).resolve()

    async def _run() -> None:
        success = 0
        skipped = 0
        failed = 0
        for config_type, source_label, rel in _DEFAULTS:
            path = cache / rel
            if not path.exists():
                click.echo(f"  SKIP  {source_label:<30} ({config_type}) — file missing: {rel}")
                skipped += 1
                continue
            try:
                parser = get_parser(config_type)
                parsed = parser.parse_file(path, source_label=source_label)
                row_id, was_new = await upsert_parsed_config(parsed)
                marker = "NEW" if was_new else "DUP"
                click.echo(f"  {marker:<5} {source_label:<30} ({config_type}, {parsed.metadata.get('item_count', parsed.metadata.get('event_count', '?'))} items) row {row_id}")
                success += 1
            except Exception as e:
                click.echo(f"  FAIL  {source_label:<30} ({config_type}) — {e}", err=True)
                failed += 1
        click.echo(f"\nDone: {success} parsed, {skipped} skipped, {failed} failed")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
