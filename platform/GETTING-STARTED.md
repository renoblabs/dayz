# Getting Started

First-time setup on a fresh machine. Roughly 30 minutes if Docker and Python are already installed; longer if you're starting from a clean OS.

## Prerequisites

- **OS:** Windows 10/11 or Linux. macOS should work but the snapshotter scheduling uses Windows Task Scheduler, so the operational layer needs adaptation on macOS/Linux (cron-equivalent).
- **Docker** - for the Postgres+pgvector container.
- **Python 3.11 or newer** - used for all four packages.
- **uv** - workspace-aware Python package manager. Install via [astral.sh/uv](https://astral.sh/uv).
- **A Steam API key** - free, get one at [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey). Requires a Steam account with at least $5 in lifetime purchases.
- **Ollama** (optional but recommended) - for local embeddings. Install via [ollama.com/download](https://ollama.com/download), then `ollama pull nomic-embed-text`. If you skip Ollama, the KB still works on BM25; you lose hybrid retrieval until embeddings are filled.
- **Discrete GPU** (optional, for transcripts later) - RTX-class or equivalent. Not needed for current functionality.

## Step 1: Clone and set up the workspace

```bash
git clone <repo-url> dayz-stack
cd dayz-stack
uv sync
```

`uv sync` installs all five workspace packages (`shared`, `kb`, `intel`, `config_mod`, `tools`) into a single `.venv`. Their CLI entry points (`dayz-stack-kb`, `dayz-stack-intel`, `dayz-stack-config`, `dayz-stack`) become available in `.venv/Scripts/` (Windows) or `.venv/bin/` (Linux/macOS).

## Step 2: Start Postgres

```bash
docker compose up -d
```

Brings up `dayz-stack-postgres` on host port 5436 (chosen to avoid conflicts with default 5432). Healthcheck takes a few seconds; verify with:

```bash
docker compose ps
# Should show dayz-stack-postgres as healthy
```

## Step 3: Configure environment

Set these env vars in your shell profile or a `.env` file alongside the code:

```bash
DAYZSTACK_DB_HOST=localhost
DAYZSTACK_DB_PORT=5436
DAYZSTACK_DB_NAME=dayzstack
DAYZSTACK_DB_USER=dayzstack
DAYZSTACK_DB_PASSWORD=dayzstack
STEAM_API_KEY=<your-steam-api-key>
```

On Windows, set `STEAM_API_KEY` as a User env var so the Workshop snapshotter scheduled task picks it up:

```powershell
[Environment]::SetEnvironmentVariable("STEAM_API_KEY", "<key>", "User")
```

Then restart any open shells. (Alternative: use [Doppler](https://doppler.com) and wrap CLI calls with `doppler run --project dayz-stack --config dev -- ...`.)

## Step 4: Run migrations for each layer

Each layer owns its own schema and its own alembic config.

```bash
cd kb && uv run alembic upgrade head && cd ..
cd intel && uv run alembic upgrade head && cd ..
cd config_mod && uv run alembic upgrade head && cd ..
```

You'll have three Postgres schemas: `public`, `intel`, `config`. Verify:

```bash
docker exec dayz-stack-postgres psql -U dayzstack -d dayzstack -c "
  SELECT table_schema, COUNT(*) AS tables
  FROM information_schema.tables
  WHERE table_schema IN ('public','intel','config')
  GROUP BY table_schema;
"
```

## Step 5: Verify each layer

### Knowledge base

Cold-start ingest from local sources, then run a search:

```bash
uv run dayz-stack-kb ingest-local
uv run dayz-stack-kb search "Formula too complex"
uv run dayz-stack-kb status
```

`status` prints chunk count, embedding count, and how many chunks are still unembedded. If you have Ollama running, fill embeddings:

```bash
uv run dayz-stack-kb embed-fill --concurrency 1
```

(Concurrency 1 is the safe default - local Ollama gets flaky under parallelism. Documented in `docs/reference/known-debt.md`.)

### Intel

One-shot Workshop snapshot to verify Steam API access:

```bash
uv run dayz-stack-intel snapshot --query trend --max-pages 1
uv run dayz-stack-intel stats
```

`stats` shows row counts per snapshot date and query type.

One-shot server snapshot from Battlemetrics:

```bash
uv run dayz-stack-intel snapshot-servers --max-servers 50
```

### Configuration management

Ingest the bundled reference configs (vanilla Chernarus, Livonia, Sakhal, Christmas Chernarus, etc.) - sourced from `BohemiaInteractive/DayZ-Central-Economy`:

```bash
uv run dayz-stack-config ingest-defaults
uv run dayz-stack-config compare vanilla_chernarus_2025 christmas_chernarus_2025 --type types_xml
```

### Operator tools

Smoke-test the CLI:

```bash
dayz-stack health "<part of a server name from your snapshot>"
dayz-stack compare "<server pattern 1>" "<server pattern 2>"
```

If you've only just done a single snapshot, pick a server name out of:

```bash
docker exec dayz-stack-postgres psql -U dayzstack -d dayzstack -c \
  "SELECT server_name FROM intel.server_snapshots ORDER BY player_count DESC LIMIT 5;"
```

## Step 6: Schedule the nightly tasks (Windows)

```powershell
PowerShell -ExecutionPolicy Bypass -File .\infra\setup-snapshotter.ps1
```

Registers two scheduled tasks:
- `dayz-stack: Workshop snapshot` - 03:00 daily
- `dayz-stack: Server snapshot` - 03:30 daily

The Workshop task currently fails on `STEAM_API_KEY` env-scope (see `docs/reference/known-debt.md`). Server task works.

## Step 7: Wire MCP into Claude Code (optional)

Add to your Claude Code config (`~/.claude.json`):

```json
{
  "mcpServers": {
    "dayz-kb": {
      "command": "C:/Users/<you>/Dayz/dayz-stack/.venv/Scripts/python.exe",
      "args": ["-m", "dayzstack_kb.mcp.server"],
      "cwd": "C:/Users/<you>/Dayz/dayz-stack",
      "env": {
        "DAYZSTACK_DB_HOST": "localhost",
        "DAYZSTACK_DB_PORT": "5436",
        "DAYZSTACK_DB_NAME": "dayzstack",
        "DAYZSTACK_DB_USER": "dayzstack",
        "DAYZSTACK_DB_PASSWORD": "dayzstack"
      }
    }
  }
}
```

Restart Claude Code. The 7 MCP tools should appear.

## Common gotchas

- **Windows path escaping in the MCP config** - use forward slashes, not backslashes, in the JSON values. JSON parses backslashes as escape chars.
- **Postgres port collision** - if `5436` is taken, edit `docker-compose.yml` and the `DAYZSTACK_DB_PORT` env var to match.
- **`PYTHONIOENCODING`** - Windows console defaults to cp1252. If you see `UnicodeEncodeError` from a CLI, set `PYTHONIOENCODING=utf-8` in your environment.
- **Embed-fill stalling** - local Ollama under any concurrency hangs. Run with `--concurrency 1`. If it dies between sessions, restart it; it's idempotent.
- **`STEAM_API_KEY` not propagating to scheduled tasks** - the User env var doesn't always reach Windows Task Scheduler scope. Workaround: set it as a System env var, OR add `.env` file loading on the snapshotter side. Tracked in `known-debt.md`.

## First useful queries

Once you have at least one Workshop and one Server snapshot in the DB, these are the canonical "is the data shaped right" queries:

```sql
-- Top deployed mods across the most recent snapshot
SELECT mod_name, workshop_id, COUNT(DISTINCT server_id) AS servers
FROM intel.server_mods
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM intel.server_mods)
  AND mod_name IS NOT NULL
GROUP BY mod_name, workshop_id
ORDER BY servers DESC LIMIT 20;
```

```sql
-- Workshop top by subscriptions, this snapshot
SELECT title, author_name, subscriptions, file_size
FROM intel.workshop_snapshots
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM intel.workshop_snapshots)
  AND query_type = 'votes'
ORDER BY subscriptions DESC LIMIT 20;
```

```sql
-- Knowledge base coverage by source type
SELECT source_type, COUNT(*) FROM public.sources GROUP BY source_type ORDER BY COUNT(*) DESC;
```
