# Roadmap

What's built, what's next, what's deliberately not. Reread when starting a session and asking "what should I work on"

## Near-term (next 2-4 sessions)

These are sized for one-or-two-session bites and have clear triggers.

### Friday intel report generator
**Why:** Once 7+ days of evening-only Battlemetrics captures are banked, day-over-day rank velocity becomes meaningful. A weekly markdown report - top movers, new entrants, falling mods, freshly-stale mods - is the artifact that makes the data legible.
**Trigger:** ≥7 days of clean evening captures in the database. (Likely first near-term item to hit its trigger - ~4-5 days out at current state.)

### Embed-fill supervisor
**Why:** Background `embed-fill` keeps dying when shells exit. A long-running supervised process (NSSM-wrapped Windows service or systemd unit on Linux) would close this gap. Until then, vector retrieval is degraded - BM25 carries.
**Trigger:** When you notice vector hits staying near zero across many KB queries.

### Workshop snapshotter env-scope fix
**Why:** Scheduled task fails because `STEAM_API_KEY` env var doesn't propagate to Windows Task Scheduler scope. Two fixes possible: (a) load `.env` on snapshotter entry, (b) explicit env override in the `setup-snapshotter.ps1` task definition. Either is ~30 minutes.
**Trigger:** Anytime, low-priority but blocks Workshop daily velocity.

### Server archetype clustering
**Why:** Group servers by mod-set similarity (Jaccard over `intel.server_mods`). The top-200 likely clusters into ~5 archetypes - vanilla-plus, expansion-bundle, hardcore-PvE-quest, RP-roleplay, PvP-arena. Once clustered, "find servers like X" becomes a tool.
**Trigger:** When the `compare` CLI starts feeling limiting because you keep wanting to compare to "this kind of server."

## Mid-term (next 5-10 sessions)

Bigger bites. Each is a real architectural addition, not a tweak.

### Agent-assisted config editing
**Why:** The leverage play. Operator says "rebalance loot for hardcore feel" -> agent reads current types.xml via MCP -> identifies category-level item groups -> proposes diffs with rationale -> operator approves -> write back to disk. Layer 3 has the parser/diff scaffolding; this is the agent prompt + a `config edit` tool.
**Trigger:** When agent-assisted authoring is concretely needed for actual operator work, not as a demo.

### YAML server-stack-as-code manifest format
**Why:** Encode the whole server stack - chosen mods (with versions), config files, mission template, server.cfg overrides, environment variables - in one declarative YAML. Tooling can then diff stacks, validate consistency, and (eventually) provision servers from manifest.
**Trigger:** When juggling multiple servers requires this, OR when a useful "publish my stack" capability emerges.

### YouTube transcripts pipeline
**Why:** A lot of operational DayZ knowledge lives in YouTube - server admin tutorials, mod walkthroughs, gotcha rundowns. `yt-dlp` + `faster-whisper` extracts transcripts; chunking + ingesting brings them into the KB. Bonus content but high quality.
**Trigger:** Focused session at the desk to verify the GPU is being used (faster-whisper falls back to CPU silently if torch is wrong).

### DZSA Launcher integration
**Why:** Closes the TraderPlus / community-PvE blind spot in the current intel sample. Battlemetrics top-200 over-weights heavy-PvE/Expansion bundle servers; DZSA Launcher's server browser surfaces a different cut.
**Trigger:** When intel queries demonstrably miss the community-PvE servers we'd want included.

### Canonical mod identity resolution (`mod_name_aliases` table)
**Why:** Mods get re-uploaded under slightly different names (TraderPlus variants, framework forks, vehicle pack rebrands) and Battlemetrics' raw mod strings don't always map cleanly to a single canonical workshop_id. A `mod_name_aliases` table - mapping known display strings, variant spellings, and re-upload IDs to a canonical mod identity - unblocks better intel quality across dozens of mods, not just TraderPlus.
**Trigger:** When working with intel data and noticing the same logical mod appearing under multiple identities skews top-N rankings.

### `serverDZ.cfg` parser
**Why:** Currently the config layer parses XML and JSON formats but not the cfg-syntax server config. Adding it lets us diff server.cfg the same way we diff types.xml.
**Trigger:** When config-editing work starts touching server.cfg.

### Mission `init.c` parser
**Why:** Mission init.c controls spawn locations, weather, custom logic. A semi-permissive parser (parse what we recognize, preserve passthrough for the rest) extends config-as-code coverage. Risky because Enforce script is real code, not config - but read-only inspection is tractable.
**Trigger:** When someone (you) wants to diff init.c across maps.

### Mod dependency graph
**Why:** Some mods require others (Expansion-Quests needs Expansion-Core). Some mods conflict. Surface this from raw_mod_string + workshop metadata + community knowledge. Output: dependency-aware stack validation.
**Trigger:** When recommending stacks becomes a real workflow, not a one-off.

## Long-term (when timing demands)

Larger or contingent.

### BI wiki Playwright
**Why:** Cloudflare returns 403 to direct requests against `community.bistudio.com`. Four access approaches evaluated under respectful rate-limiting all returned 403; the Wayback Machine archive covers most needs today, with a headless-browser path as a future option. Playwright + login automation could work but it's ~3-4hr.
**Trigger:** When KB queries demonstrably miss wiki-grade engine API content. Currently masked by official Bohemia GitHub repos (`DayZ-Samples`, `DayZ-Misc`, `DayZ-Central-Economy`).

### Backup and recovery automation
**Why:** Single Postgres instance on a personal machine = real fragility. A cron'd `pg_dump` to local + cloud is 30 minutes. A documented restore procedure is another 30. Easy to defer, hard to rebuild from nothing if it breaks.
**Trigger:** Before any sharing, before any extended absence (>2 weeks).

### Test suite scaffolding
**Why:** Currently zero tests across all packages except a placeholder dir in `config_mod`. Fine for personal use, a prerequisite for any sharing or CI. The right move is layered: contract tests for parsers, integration tests for snapshotters (against recorded fixtures), smoke tests for CLIs.
**Trigger:** Before any sharing, OR when a regression bites that tests would have caught.

### Performance / cost telemetry
**Why:** How long does each scraper take What's the embedding cost trajectory Which queries are slow Single dashboard would tell us when to optimize. Premature today.
**Trigger:** When a layer starts feeling slow OR when running on hosted infrastructure (vs. local) makes cost matter.

### Public release / open source
**Why:** Some pieces of the platform (KB scrapers, intel snapshotters, config parsers) might be useful to other DayZ operators if generalized. Other pieces are too operator-specific.
**Decision criteria - what would have to be true:**
- Platform has been dogfooded long enough (~6 months) to know which parts are generic vs which are personal-shape
- At least one external operator has expressed concrete interest in using a piece
- Maintenance cost of supporting public users is bounded - i.e. the relevant component is stable, not actively churning
- License decided: MIT (see LICENSE at the repository root)

**Trigger:** Not before 6 months of personal use; not without an external interested party.

## Explicitly out-of-scope

These are tempting but not the lane.

- **3D asset pipeline.** This is the mod-author lane, not the server-modder lane. Different skills, different tools, different community.
- **Custom map creation.** Same reason. Terra-builder workflow is its own world.
- **Original Workshop mod publishing.** The platform exists to make stack composition legible, not to publish original mods.
- **Productization as SaaS.** The whole platform is dogfood-first. Shipping it as a product would change every design choice in distorting ways.
- **Discord bot *development*.** Discord as a delivery surface for reports is acceptable if/when relevant - what's out of scope is building bot features, not pushing intel digests there.
- **Monetization features.** Donor systems, premium server perks, pay-to-win unlocks - not what this is for.

## How priorities shift

The roadmap reflects current understanding. It will be wrong about specifics. The signal that says "promote a long-term item to mid-term" or "demote something" is when actual work hits a wall the missing thing would have unblocked.

When in doubt: build the smallest thing that closes the loop on a real workflow you actually care about. Defer everything else.
