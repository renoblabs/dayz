# Corpus Inventory - dayz-stack KB

Snapshot as of session 4 end (2026-04-26 EOD).

## Headline counts

| | |
|---|---|
| Total sources | **3,396** |
| Total chunks | **8,201** |
| Embedded | varies (background fill running - check `dayz-stack-kb status`) |
| Embedding model | `nomic-embed-text` (768 dim) via local Ollama, concurrency=1 |

## Sources by ingest pass

| pass | added | source_type | scraper |
|---|---|---|---|
| Session 1 (cold-start) | 25 srcs / 473 chunks | `local_repo` | originally read legacy `~/Dayz/dayzAPI/{docs,research}` notes/gotcha catalog; use `--repo` or `DAYZSTACK_DAYZAPI_ROOT` for the consolidated repo |
| Session 2 (Workshop) | 174 srcs / 246 chunks | `github_mod_file` | reads local Steam Workshop install: CommunityFramework + VPPAdminTools |
| Session 2 (curated GH) | 2,992 srcs / 7,041 chunks | `github_mod_file` | git clone --depth 1 of 6 community foundation repos |
| Session 4 (BI repos) | 205 srcs / 441 chunks | `github_mod_file` | added BohemiaInteractive's 3 official repos (DayZ-Samples, DayZ-Misc, DayZ-Central-Economy) |
| **TOTAL** | **3,396 srcs / 8,201 chunks** | | |

## Curated GitHub repo list (`kb/src/dayzstack_kb/scrapers/github_mods.py::CURATED_REPOS`)

| owner | repo | rationale |
|---|---|---|
| `Arkensor` | `DayZ-CommunityFramework` | Foundational mod (4.7M Workshop subs). Most-cited code corpus. |
| `salutesh` | `DayZ-Expansion-Scripts` | Second-largest framework. `0_*_Preload` modular pattern. |
| `InclementDab` | `DayZ-Mod-Template` | De facto starter shape. |
| `InclementDab` | `DayZ-Dabs-Framework` | Production framework conventions (Dabs Framework on 112/200 servers per BM intel). |
| `Jacob-Mango` | `DayZ-CommunityOnlineTools` | High-stars admin/QoL mod. |
| `Jacob-Mango` | `DayZ-SampleMod` | Authoritative vendor-prefix + Workbench plugins reference. |
| `BohemiaInteractive` | `DayZ-Samples` | Official Bohemia sample mods (canonical patterns). |
| `BohemiaInteractive` | `DayZ-Misc` | Official Bohemia misc tools. |
| `BohemiaInteractive` | `DayZ-Central-Economy` | **CRITICAL for server-modder pivot:** types.xml, mission templates, central economy configs. |

## What's NOT in the corpus

| Source | Why excluded | When to add |
|---|---|---|
| `community.bistudio.com` DayZ wiki | **EXHAUSTED 4 approaches in session 4** - Cloudflare Turnstile blocks all HTTP scrapers; no XML dump exists. Needs Playwright. | When KB queries miss wiki-grade engine content. (See KNOWN-DEBT.md.) |
| `dayz-scripts.yadz.app` Doxygen | JS-rendered nav requires Playwright OR JS parsing of navtreeindex0.js | Same as above. |
| `wobo.tools/dayz/` | Time-deferred (specialty: weapon/loot mechanics) | "Extra hour" session. |
| YouTube transcripts | Deferred from session 4 - needs GPU validation (faster-whisper + CUDA torch). Heavy install. | Separate scoped session. |
| Discord exports | Not pursued - low-friction-only target per master plan. | Not planned. |

## Sanity-check queries (corpus-aware)

```bash
# the developer's own notes only
.venv\Scripts\python.exe -m dayzstack_kb.cli search "Formula too complex" --source-type local_repo

# Foundational hooks (BM25 + vector both fire - DEVLOG + CF source)
.venv\Scripts\python.exe -m dayzstack_kb.cli search "modded class MissionServer"
.venv\Scripts\python.exe -m dayzstack_kb.cli search "OnEntityKilled"

# Server-pivot queries (test the new BI ingest)
.venv\Scripts\python.exe -m dayzstack_kb.cli search "types.xml nominal min"
.venv\Scripts\python.exe -m dayzstack_kb.cli search "cfgspawnabletypes weapon attachments"
.venv\Scripts\python.exe -m dayzstack_kb.cli search "central economy event spawn"

# HTTP gotchas
.venv\Scripts\python.exe -m dayzstack_kb.cli search "RestContext SetHeader"
```

## Re-running ingest

```bash
.venv\Scripts\python.exe -m dayzstack_kb.cli ingest-local --repo ..\dayz   # consolidated repo docs/research
.venv\Scripts\python.exe -m dayzstack_kb.cli ingest-workshop        # Steam install of CF/VPP
.venv\Scripts\python.exe -m dayzstack_kb.cli ingest-github-mods     # 9 curated repos (sessions 2+4)
.venv\Scripts\python.exe -m dayzstack_kb.cli embed-fill --batch-size 4   # fill new embeddings
.venv\Scripts\python.exe -m dayzstack_kb.cli status                 # check counts
```
