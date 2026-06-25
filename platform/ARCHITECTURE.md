# Architecture

`dayz-stack` is a five-layer personal platform. Each layer has a clear responsibility and its own Postgres schema. The layers compose, but each is independently usable.

## The five layers

### Layer 1 - Knowledge Base (`dayzstack_kb`)

**What:** Searchable corpus of DayZ modding reference material. Hybrid BM25 + vector retrieval over chunked text content, with metadata on origin (which scraper, which source, what kind of file).

**Why:** Modding DayZ requires fluency in Enforce script, the engine API, the modded-CF API, types.xml schema, mission templates, and all the gotchas that don't make it into official docs. A grounded knowledge base is the difference between an agent that hallucinates `out` keyword behavior and one that quotes the actual parser limit.

**Storage:** `public.sources`, `public.chunks`, `public.scrape_runs`, `public.symbols` (Postgres + pgvector).

**Surface:** CLI (`dayz-stack-kb` - ingest, search, embed-fill, status). MCP server (`dayzstack_kb.mcp.server`) exposing tools that any MCP-aware agent can consume.

See [docs/architecture/kb-layer.md](docs/architecture/kb-layer.md).

### Layer 2 - Intel (`dayzstack_intel`)

**What:** Daily snapshots of two market signals - what's hot on Steam Workshop and what's deployed on top-populated DayZ servers. Two snapshotters, one schema.

**Why:** Workshop subscriptions tell you what *players* are clicking. Server deployments tell you what *operators* are choosing. They diverge meaningfully - only ~30% of mods deployed on top servers appear in any of the four 1000-row Workshop sample lists. For server-modder positioning, deployment is the truer signal.

**Storage:** `intel.workshop_snapshots`, `intel.server_snapshots`, `intel.server_mods`.

**Surface:** CLI (`dayz-stack-intel` - snapshot, snapshot-servers, stats). Two scheduled tasks via `infra/setup-snapshotter.ps1` for nightly captures.

See [docs/architecture/intel-layer.md](docs/architecture/intel-layer.md).

### Layer 3 - Configuration Management (`dayzstack_config`)

**What:** Parse, diff, validate, and persist the major DayZ server config formats. Permissive parsers that preserve unknown elements via passthrough so modded dialects (Expansion, CF mods) don't lose data on round-trip.

**Why:** Treating DayZ servers as configurable products requires structured access to their configs. Parser -> diff -> validate -> write back is the foundation for agent-assisted config editing - the leverage play where natural-language operator intent maps to a structured config diff.

**Storage:** `config.parsed_configs`.

**Surface:** CLI (`dayz-stack-config` - parse, diff, validate, ingest-defaults). Three MCP tools (`lookup_config_item`, `list_known_configs`, `compare_configs`).

See [docs/architecture/config-layer.md](docs/architecture/config-layer.md).

### Layer 4 - Operator Tools (`dayzstack_tools`)

**What:** Read-only CLI utilities that join data across the lower layers. Not feature-rich, just sharp.

**Why:** When you're poking at the data and want a fast answer (*how does this server's stack compare to similar ones what's stale on it*), the SQL is the same shape every time. Tools wrap the join.

**Storage:** None - read-only consumer of `intel.*` and `config.*`.

**Surface:** Single CLI (`dayz-stack`) with subcommands (`health`, `compare`).

See [docs/architecture/tools-layer.md](docs/architecture/tools-layer.md).

### Layer 5 - Reproducible PBO CI (planned, not built)

**What:** Pure-Python build pipeline that wraps `FileBank.exe` + `DSSignFile.exe`, bypassing Windows-only AddonBuilder + the P:\ drive mount. Dockerizable, headless, GitHub-Actions-runnable.

**Why:** The pro-modder community hasn't solved reproducible PBO CI because the canonical path requires Windows + a mounted P:\ drive. Standalone DayZ Tools binaries can build PBOs without the mount. Wrapping them in a clean orchestration layer is a real contribution to the modder ecosystem and a defensible technical edge for the platform.

**Surface:** TBD. Will live under a `dayzstack_build` package with its own CLI.

## Data flow

```
                   Workshop                      Battlemetrics
                      |                              |
                      v                              v
                  +--------+                    +--------+
                  | steam  |                    |  bm    |
                  +--------+                    +--------+
                      |                              |
            +---------+--------+              +------+-------+
            v                  v              v              v
     workshop_snapshots  server_snapshots  server_mods    (mod blobs)
     (intel schema)      (intel schema)    (intel schema)
                      |                              |
                      +---------+    +---------------+
                                v    v
                         +-----------------+
                         |  dayz-stack     |
                         |  health/compare |     <-- Layer 4 reads here
                         +-----------------+
                                ^
                                |
   docs (BI/Workshop/CF/...)   readonly joins
       |                       |
       v                       v
   +-------+    +----------------------+
   | kb    |--->| chunks/sources       |
   +-------+    | (public schema)      |
       |        +----------------------+
       v                ^
   +---------+          |
   | MCP svr |----------+ exposes tools
   +---------+

   types.xml,             +-------------+
   cfgspawnabletypes,     | config_mod  |---> parsed_configs
   cfgeventspawns,        | (parsers,   |     (config schema)
   expansion JSON         |  diff,      |
                          |  validate)  |
                          +-------------+
                                ^
                                |
                          MCP svr exposes 3 config tools
```

## Storage model

A single Postgres 16 instance with `pgvector`, three schemas:

- **`public`** - Layer 1 (KB) tables: `sources`, `chunks`, `scrape_runs`, `symbols`
- **`intel`** - Layer 2 tables: `workshop_snapshots`, `server_snapshots`, `server_mods`
- **`config`** - Layer 3 tables: `parsed_configs`

Each layer has its own alembic migration history (separate `alembic.ini` per workspace package). This keeps schema ownership obvious and makes it easy to roll back one layer's schema without touching others. The trade-off is that there's no unified migration tool - `alembic upgrade head` has to be run inside each layer's directory.

The instance runs locally via `docker-compose up -d` on port 5436 (chosen to avoid collisions with other Postgres instances on the dev box). This is fine for personal use; it's also the platform's biggest fragility today (single instance, no automated backup - see [docs/reference/known-debt.md](docs/reference/known-debt.md)).

## MCP integration

The KB package hosts a single FastMCP server (`dayzstack_kb.mcp.server`) that exposes all current tools, regardless of which layer they belong to logically. This keeps agents from juggling multiple MCP endpoints.

Current tool surface:

**Knowledge Base (4):**
- `search_enforce_docs(query, limit)` - hybrid retrieval over the corpus
- `lookup_class(class_name)` - symbol lookup (currently a placeholder)
- `find_examples(pattern)` - code-pattern search across ingested mods
- `get_source(source_id)` - full content of one source row

**Configuration (3):**
- `lookup_config_item(config_type, item_name, source_label)` - cross-config item lookup (e.g. AKM across all known types.xml variants)
- `list_known_configs(config_type)` - what's in the DB
- `compare_configs(label_a, label_b, config_type)` - types.xml diff via tool call

The next 1-2 tool additions should consider grouping under a meta-router to avoid MCP tool overload in agent contexts.

## Architectural decisions worth recording

### Postgres + pgvector over Qdrant or a dedicated vector DB
- **Why:** Single deployment story (one container, one DB, one set of credentials). Hybrid BM25 + vector lives in one place because Postgres has both. Operational simplicity outweighs marginal vector-perf benefits at this scale (~10k chunks).
- **When this should change:** If the corpus crosses ~1M chunks and pgvector HNSW recall+latency degrade meaningfully.

### FastMCP for the MCP server
- **Why:** Decorator-based tool definition stays close to the Python signature. The library handles MCP protocol details so we focus on tool logic.
- **When this should change:** If the protocol evolves in ways FastMCP lags on, or if performance under multi-agent load becomes an issue.

### Per-package alembic, not unified
- **Why:** Schema ownership is obvious. Rolling back one layer's schema doesn't risk the others. Each package can be developed and migrated independently.
- **Trade-off:** No single command runs all migrations. Documented in GETTING-STARTED.md.

### uv workspace, not single-package
- **Why:** Each layer has its own dependencies. `kb` needs scraping libs that `tools` doesn't. Workspace lets each member declare what it actually depends on, with `dayzstack-shared` as the cross-layer floor.
- **Trade-off:** More pyproject files to maintain. Acceptable.

### Local Ollama for embeddings, with a documented escape hatch
- **Why:** Free, no API key dependency, runs on the dev box. The escape hatch is: if Ollama becomes too flaky, swap to `voyage-code-2` or `sentence-transformers`. Embedding interface is small enough that the swap is mechanical.
- **When this should change:** If embed-fill stays unreliable enough that vector search degrades the platform's usefulness - currently mitigated by BM25 doing most of the work.

### Battlemetrics public API for server intel (no API key)
- **Why:** Free, generous rate limits, the data we need is in the public endpoints. Pay tier (`api.battlemetrics.com` with token) gives faceted filtering we'd want eventually.
- **Trade-off:** Public endpoint returns minimal facets - no map-name field, no faceted slicing. Documented in [docs/reference/known-debt.md](docs/reference/known-debt.md).

## Known limitations

- **Battlemetrics scope** - only top-200 by current pop. Skews heavy-PvE/quest. No facet for vanilla / 1pp purist / small community. Pay-tier API would resolve.
- **BI wiki Cloudflare** - `community.bistudio.com` returns 403 to four access approaches we evaluated under respectful rate-limiting; we read instead from the public Wayback Machine archive, with headless browser via Playwright as a future option. Deferred until KB queries demonstrably miss wiki-grade engine API content. Partial substitute via `BohemiaInteractive/{DayZ-Samples,DayZ-Misc,DayZ-Central-Economy}` GitHub repos.
- **Embed-fill fragility** - local Ollama under any concurrency stalls; current workaround is single-threaded with 300s timeout. BM25 fallback covers most retrieval needs.
- **Single Postgres instance** - no automated backup, no replication. Fine for personal use, fragility risk for anything more.
- **Workshop snapshotter scheduled task fails** - `STEAM_API_KEY` env var doesn't propagate to scheduled task scope. Needs either `.env` file load on the snapshotter side or scheduled-task env override.

See [docs/reference/known-debt.md](docs/reference/known-debt.md) for the full debt ledger.
