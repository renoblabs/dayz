# Data Sources

What flows into the platform, from where, with what authentication and what cadence.

## Knowledge Base (Layer 1)

### `local_repo`
**What:** Local modding notes, gotcha catalog, and research artifacts.
**Where:** Defaults to the legacy sibling path `../dayzAPI`; for the consolidated repo, run with `--repo ~/Dayz/dayz` or set `DAYZSTACK_DAYZAPI_ROOT`.
**Auth:** Filesystem.
**Cadence:** On-demand (`dayz-stack-kb ingest-local`).
**Caveats:** The setting name is still `dayzapi_root` for compatibility, but the source can be any local repo path.

### `workshop_local`
**What:** CommunityFramework source as installed by Steam.
**Where:** `C:\Program Files (x86)\Steam\steamapps\workshop\content\221100\1559212036\`.
**Auth:** Filesystem.
**Cadence:** On-demand (`dayz-stack-kb ingest-workshop-local`).
**Caveats:** Only includes mods you've actually subscribed to via Steam Workshop. Path Windows-specific.

### `github_mods`
**What:** Curated list of community mod repos plus 3 official Bohemia repos (`DayZ-Samples`, `DayZ-Misc`, `DayZ-Central-Economy`).
**Where:** GitHub public repos via `git archive`.
**Auth:** Anonymous (subject to GitHub anonymous rate limits).
**Cadence:** On-demand. Curated list lives in the scraper module.
**Caveats:** Curated list is hardcoded; updating is a code change.

### `bistudio_wiki` (built but inactive)
**What:** Engine API reference, Enforce script reference.
**Where:** `community.bistudio.com/wiki/`.
**Auth:** Live origin currently returns 403 behind Cloudflare (4 access approaches evaluated under respectful rate-limiting). Served instead from the public Wayback Machine archive.
**Cadence:** N/A - disabled.
**Caveats:** Documented in `docs/reference/known-debt.md`. Headless browser via Playwright is the only remaining option.

## Intel - Workshop (Layer 2)

### Steam Web API - `IPublishedFileService/QueryFiles`
**What:** Workshop search results across four query types (trending, recent, votes, updated).
**Where:** `https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/`.
**Auth:** `STEAM_API_KEY` env var. Free key from `steamcommunity.com/dev/apikey` (requires Steam account with $5+ in lifetime purchases).
**Cadence:** Nightly at 03:00 via Windows Task Scheduler.
**Captures:** Top 1000 per query type at `numperpage=100` × 10 pages.
**Caveats:** Subscription counts are lifetime cumulative, not active.

## Intel - Servers (Layer 2)

### Battlemetrics public API
**What:** Top-populated DayZ servers with mod fingerprint per server.
**Where:** `https://api.battlemetrics.com/serversfilter[game]=dayz&sort=-players`.
**Auth:** None (public tier).
**Cadence:** Nightly at 03:30 via Windows Task Scheduler.
**Captures:** Top 200 by current player count, plus `details.modIds` and `details.modNames` per server.
**Caveats:** Top-pop biased toward heavy-PvE/quest niches. No map field returned. Pay-tier API has facets and deeper data.

### DZSA Launcher (planned, not yet integrated)
**What:** DayZ Standalone Launcher's server browser.
**Where:** TBD - likely a public DZSA endpoint or mirror.
**Auth:** TBD.
**Cadence:** TBD - when integrated, expected nightly.
**Captures:** Different cut from Battlemetrics - closer to community-PvE / smaller-pop servers.
**Caveats:** Tracked in `ROADMAP.md` mid-term.

## Configuration Management (Layer 3)

### `BohemiaInteractive/DayZ-Central-Economy`
**What:** Reference vanilla configs (Chernarus, Livonia, Sakhal, Christmas Chernarus).
**Where:** GitHub clone in `scraper-cache/`.
**Auth:** Anonymous.
**Cadence:** Pulled once during `dayz-stack-config ingest-defaults`.
**Captures:** types.xml + cfgspawnabletypes.xml + cfgeventspawns.xml + mission templates.
**Caveats:** Snapshot of whatever Bohemia has committed at clone time. Re-clone to refresh.

### Custom server configs
**What:** Operator-specific types.xml, cfgspawnabletypes, etc.
**Where:** Wherever the operator stores them - typically `<DayZServer>/profiles/<config_dir>/` on the server box.
**Auth:** Filesystem.
**Cadence:** On-demand via `dayz-stack-config parse <file>`.

## Storage destinations

| Source | Postgres schema | Table |
|---|---|---|
| All scrapers | `public` | `sources`, `chunks`, `scrape_runs` |
| Steam Web API | `intel` | `workshop_snapshots` |
| Battlemetrics | `intel` | `server_snapshots`, `server_mods` |
| Config parsers | `config` | `parsed_configs` |

## Authentication summary

| Source | Auth |
|---|---|
| `local_repo`, `workshop_local`, parsed configs | Filesystem |
| `github_mods` | Anonymous GitHub |
| Steam Web API | `STEAM_API_KEY` (free, account-bound) |
| Battlemetrics | None (public endpoints) |
| `bistudio_wiki` | Blocked |
| DZSA Launcher | TBD |

The platform deliberately avoids auth-gated paid APIs in its current shape. All current data sources are either local or free-tier public. This keeps the dependency graph simple and the platform reproducible on any dev box.
