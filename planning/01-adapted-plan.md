# dayz-stack - Adapted Plan (audit + research deltas)

This document layers on top of the master plan you pasted. It captures the deltas after auditing what's actually in `dayzAPI` and researching how the most-respected DayZ modders structure their repos.

---

## What's already in dayzAPI we should leverage (without merging)

| Asset | What it is | How dayz-stack uses it |
|---|---|---|
| `tools/modctl/` | CLI with rule-based diagnose/fix orchestration; rule library | Seed Layer 3's agent loop (reference, not lift). Modctl rules -> KB seed. |
| `docs/dayz-modding-patterns.md` | 10+ Enforce gotchas catalog (GetId, PBO prefix, SetHeader, etc.) | **Day-1 KB ingest.** Manual source type. High signal. |
| `docs/SESSION-2026-04-22.md` + sibling logs | Real debug session notes | KB ingest as `community_doc`. Anti-hallucination context. |
| `_cf_unpacked/` | CommunityFramework decompiled source | KB ingest as `github_mod_file`. Skip scraping CF - we already have it. |
| `build-pipeline/keys/` | Generated `.bikey/.biprivatekey` pairs (BossSignal, TrophyHunter, MarksContent, HiveApiMod) | Reusable as test fixtures for Layer 4's signing tests. Don't commit privates. |
| `build-pipeline/build.bat` | The Windows reference for what worked | Layer 4 reverse-engineers from this into pure Python. |
| `research/` | Already-curated DayZ research | KB seed. |

`dayzAPI` itself stays at its current scope. Two repos. Two missions. Patterns flow one direction (dayzAPI -> dayz-stack) at boundary points.

---

## Pro-modder consensus shape (audit findings)

Researched: `Arkensor/DayZ-CommunityFramework`, `salutesh/DayZ-Expansion-Scripts`, `InclementDab/DayZ-Mod-Template`, `Jacob-Mango/DayZ-SampleMod` + `DayZ-CommunityOnlineTools`.

**Universal patterns:**
- Vendor/author folder at root -> mod folder -> `Scripts/{1_Core,3_Game,4_World,5_Mission}/<ModName>/`
- `Workbench/dayz.gproj` + `project.cfg` per mod
- `SetupWorkdrive.bat` mklinks repo to P:\
- `Workbench/Batchfiles/` ~10-20 `.bat` wrappers (BinarizePBO, Deploy, LaunchClient/Server/LocalMP, UpdateVersion)
- `Missions/{Dev,Global,<map>.ChernarusPlus}/` sibling for server-side mission template
- Default branch = `production` or `experimental`, never `main`

**Variance:**
- Prefix delivery: `$PBOPREFIX$.txt` (CF Legacy) vs gproj-only (InclementDab/Jacob-Mango) vs `BUNDLEIGNORE` (Expansion)
- Mono-PBO vs many-`0_*_Preload`-PBOs (Expansion only - pays off for hookable framework features)

**The opening:**
- **GitHub Actions / reproducible CI is essentially absent** because P:\ mounting and AddonBuilder are Windows-only. Nobody has solved this.
- We already proved today that `FileBank.exe -property prefix=<Name>` + `DSSignFile.exe` work without P:\ - i.e., the Workbench dependency is *artificial*. A pure-Python pipeline wrapping those two binaries gives reproducible builds, dockerizable CI, headless servers. **This is real.**

---

## Three deltas to the master plan

### Delta 1 - Layer 1 cold-start via dayzAPI ingestion

The original plan's Layer 1 starts with web scrapers. Add a "manual ingest" pre-step that reads `../dayzAPI/docs/dayz-modding-patterns.md`, `../dayzAPI/docs/*.md`, `../dayzAPI/_cf_unpacked/`, and `../dayzAPI/research/` *before* any web scraper runs.

**Why:** day 1 you have a working KB instead of waiting for scrapers. the developer's own debug notes are higher-signal than wiki pages for the agent's first 100 queries. CF source is the most-cited example corpus in the scene; it's already on disk.

**Schema impact:** `sources.source_type` adds `'local_repo'` variant. `sources.metadata` carries `{repo_path, file_path, repo_commit_sha}`.

**Day-1 deliverable shifts to:** "ask the KB how I solved Formula-too-complex" -> it returns the actual fix from `dayz-modding-patterns.md`.

### Delta 2 - Layer 3 scaffolder uses vendor-prefix convention

Original plan: scaffolder generates a flat mod tree.

Adapted: scaffolder generates `<org>/<ModName>/Scripts/{1_Core,3_Game,4_World,5_Mission}/<ModName>/` matching CF/Jacob-Mango/InclementDab convention.

**Why:** consensus shape, no namespace collisions when running multiple the developer's mods on the same server, future-proofs publishing to Workshop.

**dayzAPI's existing mods stay flat** - they're scoped to ship, not generalize. The new convention is for everything created via `dayz-stack create`.

### Delta 3 - Layer 4 promoted: reproducible CI is the deliverable

Original plan: ops = "deploy from PBO output to running test server."

Adapted: ops = "*reproducible* PBO build + sign + deploy via pure Python, runnable in Docker / GitHub Actions / headless." Take the Windows-`.bat` lock-in off the table.

**Why:**
- Solves a real gap nobody else has filled
- Powers Layer 3's agent iteration loop (build is fast and headless)
- Makes mod-shop deliverables reproducible by clients (huge product win later)
- We already proved the pieces today (FileBank + DSSignFile + `-property prefix=`)

**Layer 4 file additions:**
- `ops/src/dayzstack_ops/build/{filebank.py,dssign.py,pipeline.py}` - pure-Python wrappers
- `ops/Dockerfile` - DayZ Tools binaries copied in (legal-gray for distribution but fine for personal use)
- `.github/workflows/build-mod.yml` - eventual GH Actions

---

## Build order - adapted for mobile remote work

Phase A (in scratch, no Git push, while the developer is away):

1. Scaffold `~/Dayz/dayz-stack/` (uv workspace, docker-compose, shared/, kb/ skeletons)
2. Initial migration - schema applied to local Postgres
3. `kb/scrapers/local_repo.py` - the cold-start ingester. Reads `dayz-modding-patterns.md`, all dayzAPI/docs/*.md, _cf_unpacked/, research/.
4. Chunking + embeddings (Ollama nomic-embed-text)
5. Hybrid search (BM25 + vector + RRF) on the ingested content
6. CLI: `dayz-stack-kb search <query>` - proves Layer 1 works against real dayzAPI content
7. MCP server skeleton - exposes `search_enforce_docs` and `lookup_class`

Phase B (review when back):

8. Web scrapers (BI wiki, yadz docs) - runs in background once approved
9. Move dayz-stack to GitHub (the developer's call: private vs public, default branch)
10. Continue Layer 2 + Layer 3 + Layer 4 incrementally

---

## Scope of autonomous work (while the developer is away)

[done] Create `~/Dayz/dayz-stack/` directory and scaffold layer 1 in it
[done] Run local Postgres + Ollama
[done] Ingest content from `~/Dayz/dayzAPI/docs/`, `_cf_unpacked/`, `research/` (READ ONLY - no modifications to dayzAPI)
[done] Build first scraper, chunking, embedding, search end-to-end
[done] Commit locally to a fresh `dayz-stack` git init (no remote push)
[done] Write progress notes to memory + `dayz-stack-planning/`

FAIL Create or push to a GitHub remote
FAIL Modify `dayzAPI` in any way
FAIL Touch the running BossSignal server / DayZ client / dashboard
FAIL Run web scrapers without review (rate limits + reputation)
FAIL Make scope-creep additions beyond Layer 1

---

## Handoff doc - when work resumes

A separate `02-handoff.md` will document exactly what was built, what works, what's next. So work can resume without reading code.
