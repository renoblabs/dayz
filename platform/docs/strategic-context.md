# Strategic Context - Server Modder, Not Mod Author

The orienting question for `dayz-stack`: *if we build a personal DayZ platform, what should it be optimized for* This document captures the answer that's emerged over the build, and the priority shifts that follow from it.

## The positioning

**This platform is built for a server modder/operator, not a Workshop mod author.**

The DayZ modding scene has two adjacent but different lanes:

- **Mod-author lane** - publish to Steam Workshop. Compete on 3D assets, weapon packs, vehicle reskins. Success = sub count, asset polish, content cadence.
- **Server-modder lane** - operate a server (or several). Compose existing mods into a coherent stack. Tune the loot economy, the mission, the server.cfg. Success = engaged playerbase, retention, server-side coherence.

Original Workshop assets are not the goal. **Building, tuning, and operating servers - and making the surrounding workflow legible - is.**

## What this means for what we build

| If the goal were mod authorship | Because the goal is server operation |
|---|---|
| Mods are the product | Mods are tools; **the server stack is the product** |
| Compete on 3D assets / weapon packs | Compete on **server design + ops discipline + cohesion** |
| KB optimized for Enforce script API | KB optimized for **Enforce + types.xml + cfgspawnabletypes + mission files + Expansion/TraderPlus configs + server.cfg** |
| Workshop intel = the only market signal | Workshop intel + **server intel** (who runs what, where players actually play) are equally important |
| Layer 3 (Authoring) is the central lane | **Layer 4 (Ops) is the central lane.** Server-stack-as-code is the central artifact. |

## What carries through regardless

- Personal platform first - dogfood at depth before any productization. The temptation to build for an imagined audience distorts what's worth building. Server operators are a smaller niche than mod authors, and getting that wrong early would compound.
- All five layers of the platform still matter - this positioning shifts emphasis between them, not which exist.

## Priority shifts that follow

1. **Server intelligence sits next to Workshop intelligence** - both are first-class. Battlemetrics for top-populated server snapshots (in scope, shipped). DZSA Launcher and broader server-browser sources are next-priority. The point isn't to build a leaderboard; it's to know what real operators are deploying so the platform is grounded in deployment reality, not Workshop trending.

2. **Configuration management is a real module, not an afterthought.** types.xml, cfgspawnabletypes.xml, mission init.c, server.cfg, Expansion/TraderPlus JSON configs - these need parsers, validators, diff tools, and eventually agent-suggested edits. The leverage play is *agent reads natural-language operator intent -> produces structured config diff -> operator approves -> write back to disk -> deploy.*

3. **Operational telemetry inherits patterns from adjacent BossSignal work.** Player counts, retention, session length, death heatmaps - these aren't built here yet, but the design language is settled and reusable.

4. **Reproducible PBO CI is the central infrastructure deliverable.** A pure-Python build pipeline that wraps FileBank + DSSignFile, dockerizable, headless, GitHub-Actions-runnable. The pro-modder community hasn't solved this because Windows-only AddonBuilder + the P:\ drive mount are the de-facto path. Driving the standalone DayZ Tools binaries directly is proven workable. This is the platform's first defensible technical edge.

## Out of scope

- Building or operating any specific named server (downstream product decision)
- Monetization, donation systems, admin Discord bots (premature)
- Touching adjacent projects (strict separation between this platform and any other work)

## How this shows up in the existing architecture

- `intel/sources/battlemetrics.py` - server intel scraper
- `intel/sources/` package - namespace for source-specific scrapers (vs. the workshop-specific `intel/snapshotter.py`)
- `intel.server_snapshots` + `intel.server_mods` - Postgres schema for daily server captures
- `infra/setup-snapshotter.ps1` - schedules nightly Workshop and Server captures
- `kb/scrapers/github_mods.py` - pulls `BohemiaInteractive/DayZ-Central-Economy` (types.xml + mission templates, central to the server-modder pivot)
- `tools/dayzstack_tools/cli.py` - operator-shaped CLI (`dayz-stack health`, `dayz-stack compare`)

## Forward signals to watch

Once Battlemetrics data has 1-2 weeks of evening-only captures, four questions become tractable:

- Which mods are gaining server-share fastest (rising velocity in `server_mods` deployment count)
- Which mods are losing server-share (falling velocity is a signal of changing operator preferences worth understanding)
- Which servers are growing fastest in player-share (study their config + mod stack - they're solving for something)
- Cross-reference with Workshop intel: is a mod high-Workshop-subs but low-server-deployment That's "popular but doesn't cohere with real ops" - likely interesting.

These queries belong in a future session once 2-4 weeks of snapshots are banked. Don't build them yet.
