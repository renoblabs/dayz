# Hive Audit - Is the old dayzAPI salvageable

Honest technical read on the old `dayzAPI` project sitting on `origin/main`. Written 2026-04-22 after the developer asked if we should circle back and resurrect it.

> Current note: this is a historical audit. Since consolidation, the backend routes and mod client have been aligned, but HiveApiMod is still not production-ready because token use, character-id handoff, restore/autosave/disconnect save, and live DayZ validation remain incomplete. See `docs/integrations/hiveapi-audit-2026-05-07.md` for the newer route-surface audit.

---

## TL;DR

**Not garbage. ~70% complete. Salvageable with in-game validation + edge-case hardening.** But not urgent - a later collaboration project with a server operator, not a near-term priority.

---

## What's actually there

### Backend - `hiveapi/` (substantial)

- **FastAPI app** with routers: `characters.py` (243 lines), `inventory.py`, `auth.py`, `admin.py`, `server_stub.py`
- **PostgreSQL + Alembic migrations** - proper production DB with migration history (`migrations/versions/0001_initial.py`)
- **Services layer** - `services/events.py`, `services/inventory.py` - clean separation from routers
- **Utils** - `checksums.py` (CRDT-like conflict detection), `idempotency.py` (dedup keys)
- **Full pytest suite** - `test_admin.py`, `test_auth.py`, `test_characters.py`, `test_inventory.py`
- **Production ops** - `docker-compose.yml` wraps API + Postgres + Redis + Prometheus + Grafana + Cloudflared tunnel
- **Multi-tenant data model** - `tenants -> clusters -> servers -> players -> characters -> events`
- **JWT server-login auth** with signature verification
- **Idempotency keys** at the API surface to prevent duplicate operations

This is **production-shaped code**. Not a weekend prototype.

### Enforce mod - `sdk-enforce/HiveApiMod/` (exists, coherent)

- **`HiveApiConfig.c`** - settings (`API_URL`, `CLUSTER_ID`, `SERVER_ID`, `ENABLE_AUTO_SAVE`, `SAVE_INTERVAL_SECONDS`)
- **`HiveApiClient.c`** - HTTP client (316 lines), wraps RestContext calls
- **`HiveApiCharacterSync.c`** - `modded class MissionServer` (258 lines) that hooks the right lifecycle points:
  - `OnInit()` - server login
  - `InvokeOnConnect(player, identity)` - claim character from Hive on join
  - `InvokeOnDisconnect(player)` - save state + stop auto-save timer
  - Auto-save timer per player

**This is the half I previously assumed was missing.** It's not missing - it exists and is structured correctly.

### Web UI - `web-ui/` (React + Vite + Tailwind)

- **TypeScript + React Router** - proper SPA, not a one-file vanilla JS like bosssignal-backend
- Pages: Dashboard, Events, Characters
- API client, React hooks, reusable components
- Different architectural choice than BossSignal's dashboard (single-file vanilla JS)

---

## What's broken / missing / concerning

### Not production-validated in-game
At the time of the original audit, the Enforce mod had not been compiled into a PBO, signed, loaded into DayZ Server, and observed against real gameplay events. Since then the route surface has been cleaned up, but `HiveApiCharacterSync.c` still has unverified lifecycle assumptions and missing handoffs. Expect compile/runtime issues on first real boot.

### Concurrent-session edge cases
The nightmare of cross-server hives: player connects to Server A, before Server A's save completes, connects to Server B. Who owns the "canonical" character What happens to gear changes made on A while B claimed

The code has **idempotency keys** and **checksums** (good architectural start), but the ACTUAL failure modes - net partition during sync, server crash mid-write, client lag causing stale-read claims - need more thought than "we wrote atomic operations in the router." Real hive systems fail on these edges 90% of the time. The other 10% fail on clock skew.

### MongoDB -> Postgres migration scars
Git log shows PR #10 cleaned up "old mongodb code." That means the project started on Mongo, migrated to Postgres. Worth checking for leftover cruft - dead imports, half-migrated data models, test fixtures that still reference Mongo patterns.

### Auth surface not hardened
JWT server-login is fine as a pattern, but:
- Rate limiting Not obvious in the router code.
- Key rotation strategy Unknown.
- Revocation when a server is compromised Unclear.
- Signature verification - good that it's there, but edge cases around clock skew and expired-but-renewable tokens matter.

### Overlap with BossSignal architecture
Both projects ship: FastAPI backend + Enforce mod + SSE stream + event log + audit trail + Docker stack. Different:
- BossSignal -> observability (read-only on gameplay)
- HiveAPI -> state mutation (cross-server character writes)

If we resurrect HiveAPI, **we should decide: merge into one codebase, or keep separate** Probably **keep separate** - hive has 10x the risk surface (data corruption = player rage). Keeping them as distinct services lets us ship BossSignal (low-risk) without being held back by hive-hardening work. But there are real DRY wins in shared infrastructure (auth lib, DB helpers, event log schema, dashboard framework).

---

## What would "fix it" actually look like

### Week 1 - Validation (blocked on DayZ Tools being installed)
- Build the Enforce mod PBO, sign it
- Boot a local DayZ server with `@HiveAPI` mod loaded
- Watch the RPT log for: mission init, auth attempt, player connect -> claim call
- Fix the 5-10 Enforce bugs that surface on first boot
- Confirm the round-trip: player joins -> backend receives claim -> DB has new character row -> server logs success
- This phase exists but is less documented than BossSignal's equivalent phase. Would need a HIVEAPI-DEVLOG parallel to BossSignal's DEVLOG.

### Week 2 - Edge case hardening
- Write tests (or manual scenarios) for: concurrent connect, mid-sync server crash, net partition, clock skew, idempotency-key collision
- Instrument with OpenTelemetry - real hives need trace-level visibility into every mutation
- Add: rate limiting, key rotation, revocation list
- Pen-test the auth surface

### Week 3 - Scale test + polish
- Seed 100K character rows, simulate 50 concurrent servers writing
- Measure Postgres performance under load
- Grafana dashboards for: auth failures, idempotency rejections, sync latency, server heartbeat health
- Documentation pass

### Strategic fork
At some point early in week 1, decide:
- **Merge with BossSignal** - unified codebase, one backend serving both observability and hive
- **Keep separate** - BossSignal is lower risk because it is telemetry-first; HiveAPI has a long validation tail before it is safe to put in production

Gut call: **keep separate.** BossSignal is ready-ish. HiveAPI being risky shouldn't gate it.

---

## Why it was thought it didn't work

Best guess: the feedback loop was never closed. Build -> run -> observe -> fix requires a running DayZ server (which the developer didn't have until today). Without that loop:
- You can't confirm the Enforce mod compiles
- You can't confirm the PBO signing works
- You can't see the HTTP POST hit the backend
- You can't see what the real payload shape looks like
- Every "does this work" question is theoretical

So the feeling that "nothing worked" probably came from **pushing on an untestable system** until it felt like nothing was grounded. The code itself isn't bad. It just never got to try.

---

## Recommendation

1. **Don't resurrect now.** Ship BossSignal + TrophyHunter first. Let that land. One focused thing > spreading across hive work.
2. **File under "later collaboration project."** When a server operator asks "what else should we build," this is the natural pitch - cross-server progression across a real server network, positioned as an easy-to-deploy cross-server hive.
3. **First resurrection move should be validation, not rewrite.** Don't touch the code until you've booted it on a real DayZ server and seen what actually breaks. Then fix from real data.
4. **Keep BossSignal and HiveAPI architecturally separate.** Different risk profiles. Don't entangle them.
5. **Mental frame:** this is 70% done, not 0%. When you come back to it you're not starting from scratch - you're validating a substantial existing codebase.

The old dayzAPI was mis-aimed (framed as "replace Bohemia's hive" which is impossible), but the code itself is solid architecture. It deserves a second life.
