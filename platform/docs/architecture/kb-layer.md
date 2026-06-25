# KB Layer (`dayzstack_kb`)

Searchable corpus of DayZ modding reference material.

## Responsibility

- Ingest text content from heterogeneous sources (local repos, GitHub repos, Steam Workshop installs, web scrapers)
- Chunk and embed for hybrid retrieval (BM25 + vector cosine via pgvector)
- Surface results via CLI and MCP tools

## Sources currently ingested

| Scraper | Where it reads from |
|---|---|
| `local_repo` | Configured local repo path. Default is legacy `../dayzAPI`; use `--repo ~/Dayz/dayz` or `DAYZSTACK_DAYZAPI_ROOT` for this consolidated repo. |
| `workshop_local` | Steam Workshop install (`steamapps/workshop/content/221100/`) |
| `github_mods` | Curated list of community mod repos + 3 official Bohemia repos (`DayZ-Samples`, `DayZ-Misc`, `DayZ-Central-Economy`) |
| `bistudio_wiki` | Reads the public Wayback Machine archive; the live origin returns 403 behind Cloudflare to the four access approaches evaluated under respectful rate-limiting |

See `docs/reference/corpus-inventory.md` for the per-session ingestion log.

## Storage

- `public.sources` - one row per ingested file/page. Tracks `source_type`, `path`, `title`, `metadata`.
- `public.chunks` - one row per ~1KB chunk. Holds raw text + tsvector + (lazy-filled) `embedding` column.
- `public.scrape_runs` - provenance log. One row per scraper invocation.
- `public.symbols` - placeholder for future `lookup_class` MCP tool. Currently empty.

## Retrieval model

`search.hybrid_search(query)` does:
1. BM25 over `chunks.tsv` (Postgres tsvector)
2. Vector cosine over `chunks.embedding` (pgvector HNSW)
3. Reciprocal Rank Fusion (RRF, k=60) of the two ranked lists

BM25 currently dominates because vector embedding fill is partial (~7300 chunks unembedded). When embed-fill catches up, hybrid quality should improve materially.

## Surface

### CLI (`dayz-stack-kb`)
- `ingest-local` - cold-start from local sources
- `ingest-workshop-local` - pull CF source from Steam install
- `ingest-github` - fetch and chunk curated GitHub repos
- `embed-fill` - backfill missing embeddings (run with `--concurrency 1` due to local Ollama flakiness)
- `search <query>` - hybrid retrieval at the command line
- `status` - total chunks, embedded count, unembedded gap

### MCP server (`dayzstack_kb.mcp.server`)
Single FastMCP server hosting all 7 tools across layers (4 KB + 3 config). Stdio transport.

KB tools:
- `search_enforce_docs(query, limit)` - hybrid retrieval
- `lookup_class(class_name)` - placeholder, returns None pending symbol extraction
- `find_examples(pattern)` - code-pattern search
- `get_source(source_id)` - full source content

## Known limitations

- `bistudio_wiki` scraper exists but is dead behind Cloudflare. Documented in `docs/reference/known-debt.md`.
- `lookup_class` is a placeholder. Symbol extraction pass would walk all `github_mod_file` and (if available) `bistudio_wiki` sources, regex out class declarations, populate `public.symbols`. Tracked in known-debt.
- Embed-fill stalls under any concurrency. Documented in known-debt with three fix candidates (Voyage API, sentence-transformers, GPU pinning).
