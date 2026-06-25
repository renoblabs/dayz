# Known Limitations - dayz-stack

Tracks deliberate deferrals and open issues identified during the build. Each entry should resolve eventually; not all are equally urgent.

## L1 KB

### Cloudflare anti-bot blocks `community.bistudio.com`
**Severity:** Medium (canonical reference)
**Symptom:** Every request returns HTTP 403 with the Cloudflare Turnstile challenge page.
**Approaches evaluated (all returned 403 under respectful rate-limiting):**
1. `cloudscraper` library -> 403, CF Turnstile challenge
2. `curl_cffi` with `chrome120` impersonation -> 403, same Turnstile
3. Probe for XML dump (Bohemia infra, archive.org, GitHub mirrors) -> none exists; confirmed by an old forum thread asking for exactly this
4. Try alternate API paths (`/wikidata/api.php`, `/w/api.php`, Special:Export) -> all 403 (CF blocks the entire domain uniformly)
**Partial substitute deployed:** Added `BohemiaInteractive/{DayZ-Samples,DayZ-Misc,DayZ-Central-Economy}` to the github_mods curated list. Official Bohemia GitHub repos, no CF. `DayZ-Central-Economy` is *highly* relevant to the server-modder pivot (types.xml, mission templates, central economy configs). 205 new sources, 441 new chunks ingested.
**Remaining fix candidate:** Headless browser via Playwright. ~3-4hr. Defer until KB queries demonstrably miss wiki-grade engine API content.
**File:** `kb/src/dayzstack_kb/scrapers/bistudio_wiki.py` shipped but inactive; rewrite to drive Playwright when ready.

### `dayz-scripts.yadz.app` Doxygen requires JS-rendered nav
**Severity:** Medium (good Enforce reference)
**Symptom:** Page index lives in `navtreeindex0.js`; static HTML pages exist but can't be discovered without parsing the JS or executing it.
**Workaround now:** Skipped for 2026-04-25 session.
**Fix candidate:** (a) Parse `navtreeindex0.js` with a JS-aware tokenizer to extract URL list (cleanest, ~2hr); or (b) playwright-render the index page, then static-fetch each listed page (heavier).
**Priority signal:** if KB queries miss class signatures the BI wiki would have answered, do this.

### `wobo.tools/dayz/` not yet scraped
**Severity:** Low (specialty: weapon/loot/survival mechanics, not API)
**Workaround now:** Skipped for time.
**Fix:** ~1-2hr. Good candidate for "I have an extra hour" session.

### Legacy `_cf_unpacked/` local-repo seed is empty
**Severity:** Low (worked around via `workshop_local` scraper which reads from Steam workshop install)
**Note:** the `local_repo` scraper has a glob for `_cf_unpacked/**/*.c` that hits zero matches in the legacy seed path. That's fine because `workshop_local` ingests CF source from `C:\Program Files (x86)\Steam\steamapps\workshop\content\221100\1559212036\` directly. If `_cf_unpacked/` ever gets populated, we'll get duplicate sources unless we add a dedup pass.

### `lookup_class` MCP tool returns None (placeholder)
**Severity:** Medium (one of the four advertised MCP tools)
**Fix:** Symbol extraction pass. Walk all `github_mod_file` and `bistudio_wiki` sources, regex out `class Foo : Bar { ... }` declarations, populate `symbols` table. ~3-4hr.

### `source_type` enum missed retrofit on early `local_repo` ingestion
**Severity:** Low (cosmetic - early seed corpus has correct `source_type='local_repo'`, but the metadata.kind field wasn't applied)
**Fix:** Migration that adds `kind = 'session_doc' | 'research' | 'gotcha_catalog'` derived from URL pattern. Optional.

## L2 Intel

### Embedding throughput slow + flaky on local Ollama
**Severity:** Medium (vector search degraded until embeds catch up)
**Symptom:** `embed-fill` stalled at 160/7041 between sessions 2 and 3 - Ollama timeouts under any concurrency. Reduced to concurrency=1 + 300s timeout in session 4. Now grinding 7322 unembedded chunks at ~1-2/sec; will take hours.
**Why it matters:** BM25 fallback works (and is the dominant ranker for code), so search is operational. But hybrid quality is degraded until vector retrieval catches up.
**Fix candidates:** (a) Switch to `voyage-code-2` API (paid, fast, no local resource pressure); (b) Use `sentence-transformers` directly instead of Ollama; (c) Pin Ollama to the discrete GPU explicitly (verify GPU is being used, not falling back to CPU); (d) Bigger box.
**Priority signal:** if vector hits stay near zero on hybrid_search results across many queries, escalate.

### XML round-trip fidelity for config editing (session 5)
**Severity:** Medium - blocks future agent-assisted config editing if we want to write changes back without reformatting the whole file
**Symptom:** lxml's `tostring` normalizes attribute order/quoting/whitespace. parse -> serialize is semantically equivalent but not byte-identical to the original `types.xml`.
**Fix candidates:** (a) implement "patch mode" that edits raw_content via regex/line-targeting instead of full serialize; (b) switch to a comment-preserving XML library. Either is ~2-3hr.
**When it bites:** when we get to agent-assisted config editing (session 6+) and want minimal-noise diffs.

### `cfgspawnabletypes` / `cfgeventspawns` / `expansion_json` lack targeted diff
**Severity:** Low - diff exists for `types_xml` only. Other types fall through.
**Fix:** ~30-60 min each. Wait for actual demand.

### MCP `lookup_config_item` only handles `types_xml`
**Severity:** Low
**Fix:** Extend to cfgspawnabletypes (find item across spawnable groups), expansion_json (key path lookup). 30 min.

### YouTube transcripts pipeline NOT built (deferred from session 4)
**Severity:** Low (deferred deliberately, video docs are bonus content)
**Reason:** Heavy install (faster-whisper + CUDA torch ~3GB) with a real failure mode: if pip resolves CPU-only torch, the GPU won't engage and transcription will be unusably slow. Wants a focused session at the desk to verify GPU is actually being used.
**Plan:** Separate cleanly-scoped session. ~2hr including initial transcription run.

### `STEAM_API_KEY` not set anywhere yet
**Severity:** **HIGH - blocks the Workshop snapshotter from running.**
**Symptom:** Snapshotter command exits with `STEAM_API_KEY not in env. Add it to Doppler under the dayz-stack project, OR export STEAM_API_KEY=<your key> before running.`
**Fix:**
1. Get a free API key at https://steamcommunity.com/dev/apikey
2. Add it via either:
   - System env var: `[Environment]::SetEnvironmentVariable("STEAM_API_KEY", "...", "User")` (PowerShell)
   - Doppler: create a `dayz-stack` project, add `STEAM_API_KEY` secret, wrap snapshotter calls with `doppler run --project dayz-stack --config dev -- ...`
3. Re-run `infra\setup-snapshotter.ps1` (or it's already set, just env-restart needed)
**Once unblocked:** Verify with `python -m dayzstack_intel.cli snapshot --query trend --max-pages 1` then `python -m dayzstack_intel.cli stats`.

### Snapshotter idempotency uses per-row `SELECT count(*)` (slow)
**Severity:** Low (works for 4k rows/night; would matter at 100x)
**Fix:** Add a real UNIQUE constraint on `(snapshot_date, query_type, workshop_id)` and use `INSERT ON CONFLICT DO NOTHING` for atomicity.

## L3 Authoring

### Layer 3 not built (intentional - separate session)

### Vendor-prefix scaffolder convention not enforced
**Severity:** N/A until L3 starts
**Note:** The plan calls for `<org>/<ModName>/Scripts/` shape per pro-modder consensus. Today's consolidated mods under `mods/{BossSignal,TrophyHunter,MarksContent}` still use the current repo layout. dayz-stack's L3 scaffolder enforces vendor-prefix for new scaffolds; existing mods stay as-is.

## L4 Ops

### Layer 4 not built (intentional - separate session)

### Reproducible PBO CI is the deliverable, not just deploy automation
**Note from research:** No DayZ modder community has solved reproducible PBO CI because P:\\ + AddonBuilder are Windows-only. We've already proved FileBank.exe + DSSignFile.exe work without P:\\. The L4 build pipeline should be promoted to "the thing the platform is known for" - wraps both binaries via pure Python orchestrator, dockerizable, GH Actions-runnable. Current build/deploy references live under the consolidated repo's mod tooling paths.

## Generic

### MCP server not yet wired into Claude Code or Antigravity
**Severity:** Medium (it's built but no agent uses it)
**Fix:** Add `~/.claude.json` (Claude Code) and equivalent (Antigravity) config blocks pointing at the kb/src/dayzstack_kb/mcp/server.py stdio entry. ~10min.

### Repo default branch is `main`
**Severity:** Cosmetic
**Note:** Pro-modder convention is `production` or `experimental`. dayz-stack uses `main` because it's a platform repo, not a mod repo. Decision: stay `main`. Update if/when this becomes the umbrella for shop deliverables.

### CRLF/LF normalization warnings on every commit
**Fix:** Add `.gitattributes` with `* text=auto eol=lf`. ~2min.

## Hygiene gaps (added session 7)

These were identified as risks during the session-7 reorg. None are blocking current work; all should be addressed before any sharing or extended absence.

### Postgres single instance, no automated backup
**Severity:** High (everything depends on this DB; loss = total rebuild from scratch)
**Symptom:** Single `dayz-stack-postgres` container on the dev box. No `pg_dump` cron, no off-machine copy.
**Fix candidates:** (a) Cron'd `pg_dump` to a local backup dir + cloud sync (~30min); (b) WAL-archiving to S3-compatible storage (heavier, ~2hr).
**When to address:** Before any extended absence (>2 weeks), before any sharing.

### Recovery runbook not documented
**Severity:** High (couples with above - a backup without a tested restore is not a real safety net)
**Symptom:** No documented procedure for "Postgres container lost, restore from backup."
**Fix:** Write `docs/operations/runbook-recovery.md` with: backup location convention, restore command, post-restore verification queries. ~30min once backups exist.
**When to address:** Same trigger as the backup itself.

### Zero test coverage
**Severity:** Medium (fine for personal use; a prerequisite for sharing or CI)
**Symptom:** No test suite across any package except an empty placeholder dir in `config_mod/tests`.
**Fix:** Layered approach per CONTRIBUTING.md - parser contract tests, snapshotter integration tests against recorded fixtures, CLI smoke tests. Estimate ~6-8hr to scaffold meaningfully.
**When to address:** Before any sharing, OR when a regression bites that tests would have caught.

### No dependency security scanning
**Severity:** Low (private repo, personal use)
**Symptom:** No `pip-audit`, no Dependabot, no Snyk.
**Fix:** Add `pip-audit` to a `make check` target. ~10min. Or wire Dependabot once the repo is public.
**When to address:** Before public release.

### Most workers use stderr/print rather than structured logging
**Severity:** Low (workable for single-process; gets ugly with multi-worker concurrency)
**Symptom:** `dayzstack_shared.logging` exists with structlog config, but most snapshotter / scraper code uses `print(..., file=sys.stderr)` directly.
**Fix:** Sweep through worker code, replace prints with `logger.info()` etc. ~1-2hr.
**When to address:** Before running multiple workers concurrently in production-equivalent mode.

### "Cold pickup" doc not written
**Severity:** Medium (noticeable friction after a 6-week absence)
**Symptom:** Returning to the project after a long break, no single doc says "here's how to remember what's happening." GETTING-STARTED is for fresh installs; ROADMAP is for picking work; neither restores context.
**Fix:** Add `docs/operations/cold-pickup.md` covering: what state should the DB be in, what to verify before resuming, how to read the planning docs in `~/Dayz/dayz-stack-planning/`, common stale-state recovery (re-run snapshotter, restart embed-fill, etc.). ~1hr.
**When to address:** After the next long absence, while the friction is fresh.

### `src/` package layout migration
**What's missing:** Python community convention is to put packages under `src/` to force editable installs and prevent accidental in-tree imports. Current layout has packages at the repo root.
**Why it matters:** Insurance against future import-order bugs. Bigger value when adding tests or onboarding contributors.
**When to address:** Before adding meaningful test coverage, or before opening repo to external contributors. Pure refactor session, ~1-2 hours, touches imports and `pyproject.toml`.

### Split `dayzstack_intel` into `dayzstack_intel` (Workshop) + `dayzstack_servers` (Battlemetrics)
**What's missing:** Workshop intel and server intel are conceptually different domains but currently share a package. Schemas are already separated (`intel.workshop_snapshots` vs `intel.server_snapshots`).
**Why it matters:** As either grows (server archetype clustering, Workshop velocity reports, etc.) the package will feel cramped. Clean separation now would prevent later mess.
**When to address:** When one of the two intel domains grows enough to feel cramped, or when adding the Friday intel report generator if it touches both heavily.

### Alembic consolidation
**What's missing:** Alembic migrations exist as multiple configs across schemas (kb / intel / config) rather than a single unified migration history.
**Why it matters:** Multiple migration histories complicate "rebuild from scratch" runbooks and deployment to fresh databases.
**When to address:** Before writing the recovery runbook (separate near-term hygiene item) or before any deployment to a non-development environment.
