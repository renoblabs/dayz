# Diagnostic Capture Infrastructure - Proposal (2026-05-17)

**Status: SPEC ONLY. Do not build. For a future session.**

Motivation: troubleshooting the 2026-05-17 join kick required manually reading 6 log sources across 3 trees. The knowledge is all on disk; the friction is *aggregation* and *persistence*. Three tiers, independently shippable, increasing automation.

Constraints carried from the 2026-05-17 brainstorm:
- Capture **errors only**; Solution/`SOLVES` linking stays manual/deferred (auto-inference is the explicitly-deferred risky part).
- Target store is the **Neo4j graph only**; the dayz-stack Layer-1 KB stays curated, not a raw-event dump.
- **Pollution/overwhelm is the hard constraint** -> dedup is a first-class requirement, ideally a DB invariant (idempotent `MERGE` on a content fingerprint), not script discipline.

---

## Tier 1 - `dayz-stack diagnose --since=<window>` CLI

**Scope:** One command aggregates, for a time window, the sources that mattered today:
- Server RPT (`profiles/` + `profiles_B/`), filtered: kick/reject/signature/verif/`0x000`/crash
- BattlEye logs (`profiles*/BattlEye/*.log`)
- Client RPT (`%LOCALAPPDATA%\DayZ\DayZ_x64_*.RPT`) - `ErrorModuleHandler`, `LoadMods`, `0x000*`
- Docker logs for `bosssignal-backend-backend-1` (incl. the silent-hang/empty-reply symptom)
- Dashboard event stream (`/api/v1/eventslimit=N`) for the same window
Output: a single chronological, source-tagged digest + a one-line probable-cause heuristic (reuse the `0x00040074` differential).

**Effort:** ~0.5 day. Pure read/aggregate; no new storage, no scheduling. Read-only.

**Unblocks:** "I just hit something - what happened" in one command instead of 6 manual greps. Becomes the standard first step of every troubleshoot doc.

## Tier 2 - Scheduled `auto_capture` -> Neo4j

**Scope:** Harden `dayz-memory/hooks/auto_capture.ps1` (today it watches server logs only, no client RPT, no `0x000` pattern, no dedup - re-creates duplicate nodes every 5s in watch mode) and run it unattended:
- Add client-RPT + backend-docker source adapters; add verification-error (`0x000xxxx`) pattern.
- **Idempotent dedup**: `MERGE (:DayZError {fingerprint})` where fingerprint = hash(normalized message + error_type + mod). Re-scans cannot pollute.
- Track per-source file offset so only new bytes are scanned.
- Both one-shot and daemon modes (single fixed script). Schedule the one-shot every ~5 min via Windows Task Scheduler.

**Effort:** ~1-1.5 days, mostly because doing dedup *correctly* is the whole point and needs tests (pytest harness already exists beside `models.py`/`schema.py`). Recommend porting the extract/write to Python; PowerShell stays a thin launcher.

**Unblocks:** Errors flow into the causal graph with zero human involvement; `find_similar_errors` becomes useful because history actually accumulates. Foundation for the deferred fix-side loop.

## Tier 3 - Dashboard ALERTS tab ← Neo4j

**Scope:** Wire the existing (placeholder) ALERTS/Alerts page to the Neo4j graph: recent `DayZError` nodes, recurrence counts, "seen N times / first seen / last seen", unresolved-vs-resolved. Read-only view over Tier 2's data.

**Effort:** ~1 day (backend read endpoint proxying Neo4j + frontend wiring). Depends on Tier 2 producing clean, deduped data - wiring this to noisy data makes the dashboard worse, not better.

**Unblocks:** Errors and recurring patterns surface visually during a session; recurring-pain becomes obvious without querying. Demo-relevant (shows the stack observing itself).

---

## Recommended order

**Tier 1 -> Tier 2 -> Tier 3.**

- **Tier 1 first**: highest value/effort ratio, zero risk (read-only, no storage/scheduling), immediately useful for the *next* troubleshoot, and validates the source/filter set before automating it.
- **Tier 2 second**: only automate capture after Tier 1 has proven which sources/patterns are signal. Dedup-as-DB-invariant is the gate - don't schedule anything that can pollute.
- **Tier 3 last**: strictly downstream of Tier 2's data quality. Building it on un-deduped data is negative value.

Each tier is independently shippable and leaves the system better than before. None of them touch the deferred fix-side/promotion loop.
