# Roadmap

What's built, what's next, what's deliberately not. The actual queue lives in [GitHub Issues](https://github.com/renoblabs/dayz/issues). This doc is the strategic frame.

## Active streams

- **Platform** (most mature): KB, intel, config, tools - produces value daily without hands-on
- **BossSignal** (Active): Multi-server support, uptime tracking, and dashboard hydration verified. Broadened CORS for local dev.
- **Hive** (75% done): backend is production-shaped, mod kill-event loop being verified end-to-end.
- **Play** (In Progress): verifying platform against real play (BossSignal telemetry).

## Near-term (next 2-3 sessions)

Tracked in [GitHub Issues](https://github.com/renoblabs/dayz/issues).

| Issue | Title | State |
|-------|-------|-------|
| #1 | Hive loop close - first end-to-end kill telemetry | `state:active` |
| #2 | Weekly intel report generator - first weekly digest | `state:trigger-ripening` |
| #3 | First modded server - playthrough feedback loop | `state:queued` |

## Mid-term (clear trigger, ready when conditions met)

| Issue | Title |
|-------|-------|
| #4 | Embed-fill supervisor - NSSM-wrap as Windows service |
| #5 | Workshop snapshotter env-scope fix |
| #6 | Server archetype clustering |
| #7 | Agent-assisted config editing |
| #8 | YAML server-stack-as-code manifest |
| #18 | BossSignal/TrophyHunter - strategic decision |

## Long-term

All `state:backlog` labeled issues: https://github.com/renoblabs/dayz/issues?q=label%3Astate%3Abacklog

| Issue | Title |
|-------|-------|
| #9 | YouTube transcripts pipeline |
| #10 | DZSA Launcher integration |
| #11 | mod_name_aliases table for canonical mod identity |
| #12 | serverDZ.cfg parser |
| #13 | Mission init.c parser |
| #14 | Mod dependency graph |
| #15 | BI wiki Playwright attempt |
| #16 | Backup automation |
| #17 | Test suite scaffolding |

## Explicitly out-of-scope

These are tempting but not the lane.

- **3D asset pipeline.** This is the mod-author lane, not the server-modder lane. Different skills, different tools, different community.
- **Custom map creation.** Same reason. Terra-builder workflow is its own world.
- **Original Workshop mod publishing.** The platform exists to make stack composition legible, not to publish original mods.
- **Productization as SaaS.** The whole platform is dogfood-first. Shipping it as a product would change every design choice in distorting ways.
- **Discord bot development.** Discord as a delivery surface for reports is acceptable if/when relevant - building bot features is not.
- **Monetization features.** Donor systems, premium server perks, pay-to-win unlocks - not what this is for.

## How priorities shift

The roadmap reflects current understanding. It will be wrong about specifics. The signal that says "promote a long-term item to mid-term" or "demote something" is when actual work hits a wall the missing thing would have unblocked.

When in doubt: build the smallest thing that closes the loop on a real workflow you actually care about. Defer everything else.

---

*Verbose per-item descriptions live in the GitHub Issues themselves and in `platform/ROADMAP.md` (historical).*
