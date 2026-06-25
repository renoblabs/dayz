# dayz-stack

A personal DayZ operations and intelligence platform. Built for someone who runs (or plans to run) DayZ servers and wants the workflow around that to be legible - searchable docs, deployment-grounded mod intel, parsed configs, and a small set of operator-shaped CLI tools.

Started as a workshop scraper to answer "what mods actually matter on populated servers," and grew into a five-layer platform as adjacent gaps surfaced.

This is **not** a mod publishing pipeline, **not** a SaaS, and **not** affiliated with any specific server. Operator tooling for DayZ servers - search, intel, config, and CLI utilities - that complements the existing modder ecosystem rather than competing with it.

## Status

Five layers planned; three substantively built (KB, intel, config). The fourth (operator tools) has its first two CLI utilities. The fifth (reproducible PBO CI) is sketched but not yet built.

| Layer | Status |
|---|---|
| 1 - Knowledge Base | [done] Working - 3,396 sources / 8,201 chunks indexed, hybrid BM25+vector search, 7 MCP tools |
| 2 - Intel (Workshop + Server) | [done] Working - Battlemetrics + Steam Web API; ~2 days banked, scheduler partial |
| 3 - Configuration Management | [done] Working - 4 parsers (types.xml, cfgspawnabletypes, cfgeventspawns, expansion JSON), diff, persistence |
| 4 - Operator Tools | 🟡 Started - `dayz-stack health`, `dayz-stack compare` |
| 5 - Reproducible PBO CI | ⬜ Sketched only |

See [ROADMAP.md](ROADMAP.md) for what's next.

## Key features

- **Hybrid-retrieval knowledge base** over modder docs, official Bohemia GitHub repos, Workshop CF/Expansion/Dabs source, and curated community references
- **Daily intel pipeline** for Steam Workshop trending/recent/voted/updated lists and Battlemetrics top-populated server snapshots (with mod fingerprints per server)
- **Config-aware diff and validation** for the major DayZ server config formats - answers questions like *"what changed between vanilla Chernarus and Christmas Chernarus"* and *"what's the AKM nominal value across known configs"*
- **MCP server** exposing 7 tools that any MCP-aware agent (Claude Code, Antigravity, etc.) can consume
- **Operator CLIs** for stack health checks and cross-server stack diffs

## A taste

Output below uses illustrative example data (synthetic server name, real public mod
names from the deployment sample shown only as ecosystem prior-art):

```
$ dayz-stack health "Example PVE Server"
------------------------------------------------------------------------
  Example PVE Server 1 PVE|MAP WIPE|HORDES|UNIQUE
  pop 54/60  rank #122 in top-populated  snapshot 2026-04-25
------------------------------------------------------------------------
  95 mods total  (95 matched to workshop ids)
  Frameworks: Community Framework, Dabs Framework

  Top deployed mods present (rank by deployment in top-200 sample):
    158 servers  CF
    126 servers  Code Lock
    110 servers  Dabs Framework
    ...

  Stale flag (workshop last-updated > 180 days ago):
    1440d stale  on 11 top-200 servers - ExampleItemPack
     921d stale  on 19 top-200 servers - ExampleMilitaryGear
    ...
```

## Quick links

- **[GETTING-STARTED.md](GETTING-STARTED.md)** - first-time setup on a fresh machine
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - how the layers fit together, why they're separate
- **[ROADMAP.md](ROADMAP.md)** - what's built, what's next, what's deliberately out of scope
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - dev workflow, code style, how to add a layer
- **[docs/strategic-context.md](docs/strategic-context.md)** - why server-modder-not-mod-author shapes everything

## Scope

Built for personal use first, now open-sourced as part of the wider DayZ dev stack. Some layers may still be shaped toward one operator's workflow rather than fully generic — feedback and contributions are welcome.

## License

MIT. See the [LICENSE](../LICENSE) at the repository root.
