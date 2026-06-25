# Config Management Module (`dayzstack_config`)

The foundation for treating DayZ servers as configurable products. Parses, diffs, validates, and persists the major DayZ config formats so we can answer questions like *"what changed between vanilla Chernarus and Christmas Chernarus types.xml"* or *"what's the AKM nominal value across known configs"* - and so future agent-assisted editing has structured representations to work with.

## Architecture

```
config_mod/
|-- src/dayzstack_config/
|   |-- types.py              # ParsedConfig, TypesItem, ValidationIssue (Pydantic)
|   |-- models.py             # SQLAlchemy ORM (config.parsed_configs)
|   |-- persistence.py        # upsert / get_by_label / lookup_types_item
|   |-- diff.py               # diff_types_xml + render_types_diff_markdown
|   |-- registry.py           # config_type -> Parser instance
|   |-- cli.py                # `dayz-stack-config` CLI
|   `-- parsers/
|       |-- base.py           # ConfigParser Protocol
|       |-- types_xml.py
|       |-- cfgspawnabletypes_xml.py
|       |-- cfgeventspawns_xml.py
|       `-- expansion_json.py
`-- migrations/versions/0001_parsed_configs.py
```

Tables live in Postgres schema `config` (separate from `intel` and the kb tables) so the schema ownership boundary is obvious.

## Parser Protocol

Every parser implements:

```python
class ConfigParser(Protocol):
    config_type: str    # e.g. 'types_xml'

    def parse_string(self, content: str, source_label: str, source_path: str | None = None) -> ParsedConfig
    def parse_file(self, path: Path, source_label: str | None = None) -> ParsedConfig
    def serialize(self, parsed: ParsedConfig) -> str
    def validate(self, parsed: ParsedConfig) -> list[ValidationIssue]
```

## Permissive parsing - preserve unknown fields

DayZ has multiple types.xml dialects in the wild:
- Vanilla (Bohemia)
- Expansion-modified (additional Expansion-specific fields)
- CF-modified
- Server-author tweaks

Strategy: parse what's known, capture unknown elements in `extra_elements` passthrough so round-trip serialize doesn't lose data. Modded inputs survive a parse -> store -> serialize cycle without information loss.

## Supported formats (session 5)

| config_type | parser | status |
|---|---|---|
| `types_xml` | `parsers/types_xml.py` | [done] full + diff + validate |
| `cfgspawnabletypes_xml` | `parsers/cfgspawnabletypes_xml.py` | [done] parse + serialize + validate |
| `cfgeventspawns_xml` | `parsers/cfgeventspawns_xml.py` | [done] parse + serialize + validate |
| `expansion_json` | `parsers/expansion_json.py` | [done] parse with flavor detection (heuristic) |
| `traderplus_json` | (not built) | ⬜ punted - JSON parser handles it permissively if needed |
| `mission_init_c` | (not built) | ⬜ Enforce script parsing - separate session |
| `server_cfg` | (not built) | ⬜ key=value with sections - small follow-up |

## Diff (types.xml)

- Computes added / removed / modified by item name
- For modified items, captures per-field (from, to) tuples for `nominal`, `lifetime`, `restock`, `min`, `quantmin`, `quantmax`, `cost`, `category`, `flags`, `usages`, `values`, `tags`
- Sorts modifications by impact (number of changed fields, descending)
- Renders both structured JSON and human-readable markdown

Demonstrated working on `vanilla_chernarus_2025` vs `christmas_chernarus_2025` - surfaces 4 added items, 21 removed items, 37 modified items (with the seasonal LeafCrown / Candycane / Flare nominal-zero -> spawnable transitions visible).

cfgspawnabletypes / Expansion JSON / cfgeventspawns diff: deferred. The generic JSON-deep-diff approach will handle the JSON formats fine; XML formats need targeted diffs to be useful.

## Persistence

`config.parsed_configs` table stores:
- `config_type`, `source_label`, `source_path` - primary identity
- `parsed_data` (JSONB) - normalized structured form
- `raw_content` (TEXT) - original for diff/regen
- `file_hash` (TEXT) - sha256 of raw_content; idempotent upsert key
- `metadata` (JSONB) - format-specific (item_count, event_count, flavor, etc.)

Idempotency: upserting the same `(file_hash, source_label, config_type)` tuple is a no-op.

## MCP integration

Three new tools added to `dayzstack_kb.mcp.server`:
- `lookup_config_item(config_type, item_name, source_label)` - cross-config item lookup (e.g. AKM across all known types.xml variants)
- `list_known_configs(config_type)` - what's in the DB
- `compare_configs(label_a, label_b, config_type)` - types.xml diff via tool call

Total MCP surface is now **7 tools** (4 KB + 3 config). The next 1-2 additions should consider grouping under a meta-router to avoid MCP tool overload in agent contexts.

## Reference configs ingested (session 5)

Via `dayz-stack-config ingest-defaults`:

| source_label | config_type | item count |
|---|---|---|
| `vanilla_chernarus_2025` | types_xml | 1,941 |
| `vanilla_livonia_2025` | types_xml | 1,939 |
| `vanilla_sakhal_2025` | types_xml | 1,955 |
| `christmas_chernarus_2025` | types_xml | 1,924 |
| `vanilla_chernarus_2025` | cfgspawnabletypes_xml | 574 |
| `vanilla_livonia_2025` | cfgspawnabletypes_xml | 575 |
| `vanilla_chernarus_2025` | cfgeventspawns_xml | 34 events |
| `vanilla_livonia_2025` | cfgeventspawns_xml | 32 events |
| `expansion_credits` | expansion_json | (credits sample) |

All sourced from `BohemiaInteractive/DayZ-Central-Economy` GitHub clone in `scraper-cache/`. The Christmas variant is especially useful as a diff target - it's a known reference for "modify-event-pool-only" changes.

## Round-trip fidelity (known limitation)

XML serialization via lxml normalizes attribute quoting, attribute ordering, and whitespace. For diff purposes this is fine. For future agent-assisted editing where we want to *change a few values and write back without reformatting the whole file*, byte-identical round-trip matters. Two paths to resolve later:
1. Implement a "patch" mode that operates on the original raw_content via regex/line-targeting rather than serialize.
2. Use a comment-preserving XML library and configure lxml for attribute order preservation.

Flagged in `KNOWN-DEBT.md` for when it becomes blocking.

## Path to agent-assisted config editing

This module built the scaffolding. Agent-assisted editing is the leverage play - operator says "rebalance loot for hardcore feel" and the agent:
1. Pulls the current types.xml via MCP
2. Identifies items by category/usage tags (military weapons, food, medical, ammo)
3. Proposes nominal/min/restock changes with rationale
4. Generates a new ParsedConfig
5. Diff-previews the change
6. Operator approves; serialize -> write to disk -> deploy

The pieces needed for that: (a) all 7 MCP tools we now have, (b) a "config edit" tool that takes a ParsedConfig + a structured set of changes and returns a new ParsedConfig, (c) the agent prompt scaffolding. Tracked in `ROADMAP.md`.
