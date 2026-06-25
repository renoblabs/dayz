# Intel Layer (`dayzstack_intel`)

Daily snapshots of DayZ market signals - Steam Workshop trending and Battlemetrics top-populated server deployments.

## Responsibility

- Capture point-in-time state of the DayZ ecosystem from public APIs
- Keep enough history to enable velocity analysis (rising/falling mods, server rank churn)
- Stay polite - rate-limited, no API-key-gated endpoints unless free, no scraping behind auth

## Two snapshotters, one schema

The intel layer hosts both Workshop (Steam Web API) and Server (Battlemetrics) snapshotters. They're separate code paths but share the `intel` Postgres schema. A future split into `dayzstack_intel` + `dayzstack_servers` was considered (and deferred - see `~/Dayz/dayz-stack-planning/07-repo-audit.md`).

### Workshop snapshotter (`snapshotter.py`)

- Calls `IPublishedFileService/QueryFiles` against Steam Web API
- Four query types per night: `trend`, `recent`, `votes`, `updated`
- Captures top 1000 per type at `numperpage=100` × 10 pages
- Persists to `intel.workshop_snapshots`

### Server snapshotter (`server_snapshotter.py`)

- Public Battlemetrics API: `https://api.battlemetrics.com/serversfilter[game]=dayz&sort=-players`
- Captures top 200 by current player count
- Per-server `details.modIds` and `details.modNames` blobs are parsed into `intel.server_mods`
- Some servers return mod blobs as binary with embedded null bytes (Postgres TEXT/JSONB rejects); a recursive `_sanitize_text`/`_sanitize_json` strips them

## Storage

- `intel.workshop_snapshots` - one row per (snapshot_date, query_type, workshop_id). Holds title, subscriptions, favorites, file_size, tags, created_at, updated_at, full raw_response.
- `intel.server_snapshots` - one row per (snapshot_date, source, server_id). Holds server_name, player_count, max_players, version, third_person flag, raw_response.
- `intel.server_mods` - one row per (snapshot_date, server_id, mod). Holds mod_name, workshop_id, raw_mod_string. Joined to `server_snapshots` by `(snapshot_date, server_id)`.

## Surface

### CLI (`dayz-stack-intel`)
- `snapshot --query <trend|recent|votes|updated>` - single-query Workshop snapshot
- `snapshot --all` - all four query types in sequence
- `snapshot-servers --max-servers <N>` - Battlemetrics server snapshot
- `stats` - row counts per snapshot date / query type

### Scheduled tasks (Windows)
`infra/setup-snapshotter.ps1` registers two tasks:
- `dayz-stack: Workshop snapshot` - 03:00 daily
- `dayz-stack: Server snapshot` - 03:30 daily

The Workshop task currently fails on `STEAM_API_KEY` env-scope (env var doesn't propagate to scheduled task context). Documented in `docs/reference/known-debt.md`.

## Known limitations

- **Battlemetrics public-tier scope** - only top-populated by current pop. No facets for vanilla / 1pp purist / small community. Pay-tier API has these.
- **No map field** in the public list endpoint - `attributes.details.map` returns blank for DayZ. Deep-fetch (`/servers/{id}`) may have it; not pulled yet.
- **Workshop sample bias** - only 4 query types × 1000 = 4000 distinct workshop_ids per night. Long-tail mods on the workshop don't appear unless trending.
- **One snapshot ≠ a trend** - single-day data is a point-in-time observation. Velocity analysis needs a clean week minimum.

## Useful join shape

```sql
-- Top deployed mods, with latest workshop metadata
SELECT
  sm.mod_name,
  sm.workshop_id,
  COUNT(DISTINCT sm.server_id) AS deployed_on_servers,
  ws.subscriptions,
  ws.created_at::date AS published,
  ws.updated_at::date AS last_updated
FROM intel.server_mods sm
LEFT JOIN LATERAL (
  SELECT subscriptions, created_at, updated_at
  FROM intel.workshop_snapshots ws
  WHERE ws.workshop_id = sm.workshop_id
  ORDER BY ws.snapshot_date DESC LIMIT 1
) ws ON TRUE
WHERE sm.snapshot_date = (SELECT MAX(snapshot_date) FROM intel.server_mods)
  AND sm.workshop_id IS NOT NULL
GROUP BY sm.mod_name, sm.workshop_id, ws.subscriptions, ws.created_at, ws.updated_at
ORDER BY deployed_on_servers DESC LIMIT 30;
```
