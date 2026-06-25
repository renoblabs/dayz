# 01 - Repo Inventory: `dayzAPI`

_Cloned from the predecessor dayzAPI repo into `./research/dayz/_repo/` for audit. Analysis only - no code changes._

## Tree

```
dayzAPI/
|-- .github/workflows/ci.yml              # GitHub Actions CI
|-- .gitignore
|-- Makefile                              # `make start`, `make demo`, `make test`, `make ui`, `make all`
|-- README.md                             # Marketing-heavy overview (badges, emojis)
|-- PROJECT_OVERVIEW.md                   # Architecture summary
|-- QUICK_START.md                        # Local setup
|-- DEMO_GUIDE.md                         # Walkthrough
|-- DEPLOYMENT_GUIDE.md                   # VPS/cloud deploy
|-- INTEGRATION_EXAMPLES.md               # C++, Python, Discord bot examples
|-- RESOURCES.md                          # DayZ modding tools pointers
|-- ROADMAP.md                            # Docker-first backlog; references DaemonForge
|-- render.yaml                           # Render.com deploy manifest
|
|-- hiveapi/                              # -- BACKEND (Python / FastAPI)
|   |-- alembic.ini
|   |-- pytest.ini
|   |-- requirements.txt
|   |-- app/
|   |   |-- main.py                       # FastAPI app, CORS=*, Prometheus mw, Origin-Secret mw
|   |   |-- config.py                     # Pydantic Settings: DB_URL, JWT, TTLs, ORIGIN_SECRET
|   |   |-- deps.py                       # get_db()
|   |   |-- db/models.py                  # SQLAlchemy: Tenant, Cluster, Server, Player, Character,
|   |   |                                 #   Event, IdempotencyKey, MoveTicket
|   |   |-- routers/
|   |   |   |-- auth.py                   # POST /v1/auth/server-login
|   |   |   |-- characters.py             # POST /v1/characters/{claim,heartbeat}
|   |   |   |-- inventory.py              # POST /v1/inventory/{set,apply}
|   |   |   |-- admin.py                  # overview, events, SSE stream
|   |   |   `-- server_stub.py            # ping, bootstrap test data
|   |   |-- services/
|   |   |   |-- events.py                 # record_*_event helpers
|   |   |   `-- inventory.py              # compute_inventory_checksum, apply_ops, detect_conflicts
|   |   `-- utils/
|   |       |-- checksums.py
|   |       `-- idempotency.py
|   |-- migrations/
|   |   |-- env.py
|   |   `-- versions/0001_initial.py
|   |-- ops/
|   |   |-- docker-compose.yml            # api + postgres16 + redis7 + prometheus + grafana + cloudflared
|   |   |-- Dockerfile
|   |   |-- entrypoint.sh                 # alembic upgrade head && seed && uvicorn
|   |   |-- prometheus.yml
|   |   |-- grafana-provisioning/datasources/datasource.yml
|   |   `-- cloudflared/config.yml.sample
|   |-- scripts/
|   |   |-- demo_seed.py
|   |   |-- seed.py
|   |   `-- dev_reset.sh
|   `-- tests/                            # pytest, in-memory SQLite
|       |-- conftest.py
|       |-- test_auth.py
|       |-- test_characters.py
|       |-- test_inventory.py
|       `-- test_admin.py
|
|-- sdk-enforce/                          # -- "ENFORCE SCRIPT" SDK (two incompatible attempts)
|   |-- HiveApi.c                         # v1: single-class RestApi helper (RestContext, RestRequest)
|   |                                     #     - uses ERestMethod.PUT/POST/GET
|   |                                     #     - manual JSON string concat
|   |                                     #     - `func`-typed lambda callbacks
|   |                                     #     - static ref map caches
|   `-- HiveApiMod/                       # v2: drop-in mod folder scaffold
|       |-- config.cpp                    # CfgPatches + CfgMods with 3_game/4_world/5_mission
|       |-- QUICK_START.md
|       |-- README.md
|       `-- scripts/4_world/
|           |-- HiveApiConfig.c           # Static class: API_URL, CLUSTER_ID, SERVER_ID, toggles
|           |-- HiveApiClient.c           # REST wrapper: ServerLogin, ClaimCharacter,
|           |                             #   SaveInventory, SendHeartbeat + substring JSON parsing
|           `-- HiveApiCharacterSync.c    # modded MissionServer + modded PlayerBase:
|                                         #   InvokeOnConnect -> ClaimCharacter
|                                         #   InvokeOnDisconnect -> SaveInventory + Heartbeat
|                                         #   Timer-based auto-save every SAVE_INTERVAL_SECONDS
|
|-- sdk-reference/README.md               # Placeholder (near-empty)
|
`-- web-ui/                               # -- FRONTEND (React 18 + TS + Vite + Tailwind)
    |-- index.html, package.json, vite.config.ts, tsconfig*.json
    |-- tailwind.config.js, postcss.config.js
    `-- src/
        |-- main.tsx, App.tsx, App.css, index.css
        |-- api/client.ts                 # Axios wrapper
        |-- hooks/useApi.ts               # SWR-style Custom hook for fetch
        |-- types/index.ts
        |-- components/{Layout,LoadingSpinner,StatCard}.tsx
        `-- pages/{Dashboard,Events,Characters}.tsx
```

## File purposes (inferred)

### Backend (`hiveapi/`)
A fully modern Python web service. The shape is **Stripe/SaaS-style**, not game-server-style:
- Multi-tenant data model (Tenant -> Cluster -> Server -> Character).
- JWT auth with RS256 configured, idempotency keys, audit events, SSE event stream.
- Observability stack (Prometheus + Grafana) bolted on from day one.
- Ops story: Docker Compose for local, Render.com for prod, Cloudflare Tunnel for exposure.
- CRDT-lite inventory: a `base_checksum` -> `ops` -> `new_checksum` model with conflict detection.
- Move-ticket pattern (one-shot transfer tokens with TTL) for cross-server character moves.

### Enforce "SDK" (`sdk-enforce/`)
Two passes at the same thing that never got reconciled:

1. `HiveApi.c` - a more architecturally clean attempt written against what the author _thought_ the Enforce REST API looked like. Uses `RestContext`, `RestRequest`, `ERestMethod`, `RestResponse.GetBody/GetCode`, and `JsonReader`/`JsonValue`. Registers callbacks by assigning `func`-typed member fields (`m_onSuccess`, `m_onError`) and `.Invoke()`ing them. Caches responses in `static ref map<string,string>`.

2. `sdk-enforce/HiveApiMod/` - a second, fuller attempt that drops the cleaner shape and uses the signature `OnSuccess(string data, int dataSize)` / `OnError(int errorCode)` / `OnTimeout()`. Does the REST call as `ctx.POST(cb, "", body)` with `ctx.SetHeader("Authorization: Bearer ...")`. Parses JSON by hand via `IndexOf("\"access_token\":\"")`. Plugs into the game via `modded class MissionServer` overriding `InvokeOnConnect` / `InvokeOnDisconnect` and a `modded class PlayerBase` extension. `config.cpp` declares a minimal `CfgPatches` + `CfgMods` with standard `3_game` / `4_world` / `5_mission` script module dirs.

The two halves disagree on the REST callback contract, the JSON parsing approach, the class layout, and which side of the wire owns the retry loop. They were not reconciled.

### Web UI (`web-ui/`)
Standard 2024-vintage React/Vite/Tailwind admin panel. Dashboard + Events + Characters pages. Consumes the FastAPI JSON + SSE stream. Looks like a generic internal ops console, not anything DayZ-specific.

### Docs
Heavy on promotional-style README content (badges, emojis, "production-ready", "perfect for..."). The real architecture signal is in `ROADMAP.md`, which admits the project's north star: **DaemonForge Universal API parity** - reimplementing Mongo-style player/object/globals JSON store over Postgres JSONB with `$set/$inc/$push/$pull` semantics.

## Signals about what stack / approach you were aiming at

1. **You reached for your existing toolbox.** FastAPI, PostgreSQL, Redis, Alembic, Pydantic, Prometheus, Grafana, Cloudflare Tunnel, Docker Compose, React+Vite+Tailwind, Render.com. Zero of that is native to the DayZ/Bohemia ecosystem - all of it is standard SaaS web-backend stuff.

2. **You assumed the inside-out architecture is the product.** Multi-tenant (Tenant -> Cluster -> Server) with JWT, idempotency keys, audit events, SSE streaming, checksummed CRDT-lite inventory, signed request verification. That's a Stripe-shaped API, not a DayZ addon. Shipped before a single line of in-game logic was proven.

3. **You modeled on DaemonForge UniversalAPI.** `ROADMAP.md` says it out loud: "Parity with DaemonForge Universal API." UniversalAPI is the _real_ standard in the DayZ scene for exactly this job - external key/value + player + globals store with Mongo-ish ops, already integrated with popular mods (MapLink Hive, CRDTN, etc.). Your repo is effectively a Postgres-flavored rewrite of it.

4. **The Enforce side was done blind.** Two mutually incompatible SDKs coexist. One uses `ctx.Send(req, cb)` + `RestResponse`, the other uses `ctx.POST(cb, "", body)` + `OnSuccess(string,int)`. Only one of those API shapes exists in real Enforce Script (see `03-what-was-broken.md`). Both were generated from docs hallucinations, not from running code against a real server.

5. **Hive is the wrong word.** The project calls itself "HiveAPI," implying it replaces or augments the DayZ hive (persistence layer). In DayZ Standalone the hive is no longer a thing players rent into - it's local, per-server, and Bohemia-only for the public hive. So branding says "we are the persistence layer" but the actual position in the stack is "we are a side-channel cache that sits next to persistence."

6. **Use cases are speculative, not validated.** README lists cross-server transfers, faction wars, Discord rewards, PvP wager escrow, etc. All plausible, none actually built against a running DayZ server. No `.pbo` output, no `@mod` folder, no `.bikey`/`.biprivatekey`, no mission file wiring, no `serverDZ.cfg` snippets, no `types.xml` touchpoint. The in-game half never got out of prototype.

7. **Ops sophistication is disproportionate.** Prometheus + Grafana + Cloudflare Tunnel + Render.yaml + multi-tenant schema + Alembic migrations + SSE + pytest before you've proven a single Enforce Script call reaches the backend on a real server. Classic "architect builds the whole platform before building the thing."

## Summary
A production-grade web-SaaS backend with a React admin console, bolted to two half-written Enforce SDKs that disagree with each other and with the real engine API. It's the right shape for _something_ in the DayZ world - a DaemonForge-style external data service - but it was designed top-down from a generic web-backend template instead of inside-out from what a running DayZ mod can actually do.
