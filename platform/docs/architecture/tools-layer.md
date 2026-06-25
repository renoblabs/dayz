# Tools Layer (`dayzstack_tools`)

Read-only operator-shaped CLI utilities. Joins data across `intel.*` and `config.*` so common questions have a fast answer.

## Responsibility

- Wrap recurring data joins behind sharp single-purpose commands
- Emit explicit caveats inline so output disclaims its own limits
- Stay read-only - never mutate data the lower layers wrote

## Current commands

### `dayz-stack health <server-name-pattern>`

Single-server stack health check. Substring-matches by server name (case-insensitive, ILIKE), picks the most recent snapshot the server appears in, reports:

- **Frameworks present** (CF / Dabs / Expansion-Core)
- **Top deployed mods** on this server, ranked by deployment count in the latest top-200 sample
- **Stale flag** - mods whose Workshop `updated_at` is more than 180 days ago
- **Rare/bespoke flag** - mods deployed on fewer than 5 of top-200
- **Caveat footer** - sample biases, metadata gaps

### `dayz-stack compare <pattern1> <pattern2> [...]`

Cross-server stack comparator. For each pattern, picks the highest-pop matching server. Shows:

- **Mods shared by all servers** - common foundation, ranked by global deployment
- **Mods unique to each server** - differentiators, ranked rarest-first
- **BESPOKE flag** on mods on <5 of top-200

## Design notes

- Both commands span snapshot dates rather than restricting to "latest" - top-200 churns ~50% between peak and off-peak captures, so a strict latest-only filter would frequently miss servers.
- Output is plain ASCII (no Unicode box-drawing) because Windows console default cp1252 fails on `-` and `-`.
- "Caveats" footer is always printed. Tools that pretend to confidence they don't have are worse than tools that disclaim limits.

## Surface

CLI entry point: `dayz-stack` (just the bare entry, not prefixed with `dayz-stack-tools`). Subcommands: `health`, `compare`.

## What's deliberately not here

- **Write operations.** Tools layer is read-only. Anything that mutates data lives in the layer that owns the schema.
- **MCP tools.** Currently this layer doesn't host MCP tools. If/when it does, register them in the centralized `kb/src/dayzstack_kb/mcp/server.py` per the convention in CONTRIBUTING.md.
- **Aggregation reports.** A weekly `dayz-stack report` command for the Friday intel digest is in the roadmap but not built - needs ≥7 days of data first.
