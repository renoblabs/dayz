# HiveAPI Integration Audit - 2026-05-07

A snapshot audit of the HiveAPI ↔ HiveApiMod surface to make sure the mod
calls match what the backend exposes, and to remove dead code that was
actively misleading.

## TL;DR

- **Route surface matches, lifecycle wiring is still incomplete.** `HiveApiClient.c` calls existing HiveAPI routes on the `ops-api` container (`:6701` host port), but mod-side Bearer token attachment, character-id handoff, restore, autosave timer execution, and reliable disconnect save are not complete.
- **One dead file removed.** `mods/HiveApiMod/scripts/4_world/HiveApi.c` was a 302-line legacy KV-store/transfer client targeting `:8000` and `/v1/state/*`, `/v1/transfer` - endpoints that don't exist in the current backend. Zero external callers. Deleted.
- **Outstanding items** (not blocking this audit, but blocking production use): out-of-date `:8000` examples in older docs (the container port; host maps to `:6701`), per-server `CLUSTER_ID` / `SERVER_ID` values, Bearer token use after login, and character-id propagation from the `ClaimCharacter` callback back into `HiveApiCharacterSync.c`.

## Live backend surface

`ops-api-1` container, host `:6701` -> `8000` in-container. From `/openapi.json`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Service banner |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus |
| POST | `/v1/auth/server-login` | Server obtains auth token |
| POST | `/v1/characters/claim` | Claim character on connect |
| POST | `/v1/characters/heartbeat` | Periodic player heartbeat |
| POST | `/v1/inventory/apply` | Apply diff |
| POST | `/v1/inventory/set` | Replace inventory |
| GET | `/v1/admin/events` | Recent events feed |
| GET | `/v1/admin/events/stream` | SSE event stream |
| GET | `/v1/admin/overview` | Admin overview |
| POST | `/v1/server-stub/bootstrap` | Server-stub bootstrap |
| GET | `/v1/server-stub/ping` | Server-stub ping |

## Mod-side surface

After this audit, the mod calls into the backend from exactly two files:

### `scripts/4_world/HiveApiClient.c`
Static methods, each builds a `RestContext` against `HiveApiConfig.GetEndpoint(...)` (= `API_URL` + path):

| Method | Backend path | Status |
|---|---|---|
| `ServerLogin` | `/v1/auth/server-login` | Route matches; token is parsed but not attached to later calls |
| `ClaimCharacter` | `/v1/characters/claim` | Route matches; returned character ID is logged but not handed back into the sync map |
| `SaveInventory` | `/v1/inventory/set` | Route matches; only works once a valid character ID is available |
| `SendHeartbeat` | `/v1/characters/heartbeat` | Route matches; only works once a valid character ID is available |

### `scripts/5_mission/HiveApiCharacterSync.c`
Modded `MissionServer`. Hooks:

- `OnInit` - calls `HiveApiClient.ServerLogin` (deferred 10s after mission load to avoid boot hang)
- `InvokeOnConnect` - calls `HiveApiClient.ClaimCharacter`
- `InvokeOnDisconnect` - attempts to save inventory if `ENABLE_AUTO_SAVE`, but currently has no character ID unless that handoff is wired
- Auto-save timer map exists, but the `Timer.Run(...)` call is commented out, so periodic autosave is not active

This is the canonical integration point; everything else is helpers/config. Treat it as an integration scaffold until the ID/token/autosave gaps are closed and tested in-game.

## What was removed

### `scripts/4_world/HiveApi.c` (302 lines, deleted)

Legacy KV-store / transfer client. Hardcoded `HIVE_URL = "http://127.0.0.1:8000"` (wrong port for the running backend) and used these endpoints:

| Mod call | Backend route | Reality |
|---|---|---|
| `HiveApi.SaveKV(key, json)` | `POST /v1/state/{key}` | Not exposed |
| `HiveApi.LoadKV(key)` | `GET /v1/state/{key}` | Not exposed |
| `HiveApi.CreateTransfer(...)` | `POST /v1/transfer` | Not exposed |
| `HiveApi.ClaimTransfer(token)` | `POST /v1/transfer/claim/{token}` | Not exposed |

**Caller graph:** zero callers outside its own callback classes. The class would never be invoked at runtime - but its very existence misled anyone reading the mod source about what the integration *should* be doing.

The transfer/KV idea may be valuable later (cross-server item transfer, stored events) but the right place to add it is on top of the current `HiveApiClient.c` plumbing, not a parallel client targeting a stale URL.

## Things to fix later (not in this audit)

1. **`backends/hiveapi/QUICK_START.md` references `:8000` everywhere.** Inside the container that's correct, but the docker-compose host port is `:6701` - readers running through Docker will hit confusion. Either add a `host = 6701, in-container = 8000` note up front or rewrite to use `:6701` consistently.
2. **`HiveApiConfig.c` has concrete demo `CLUSTER_ID` / `SERVER_ID` UUIDs.** `IsConfigured()` only checks for non-empty, so demo values pass. Real deployment needs per-server values, ideally from `$profile:hiveapi_config.json`.
3. **`HIVE_KEY = "dev-local-secret"`** was hardcoded in the deleted file. The live `HiveApiClient` parses a token returned by `ServerLogin`, but follow-up calls do not attach it yet. Any future authenticated mod-side call should use `HiveApiConfig.s_serverToken`, not a hardcoded shared secret.
4. **Character ID handoff is missing.** `HiveClaimCharacterCallback` logs the `character_id`, but `HiveApiCharacterSync.SetCharacterID(...)` is never called from that callback.

## Verification

- `python -m modctl ship hiveapi` - clean build after the delete.
- `curl http://localhost:6701/health` - `{"status":"healthy"}`.
- `curl http://localhost:6701/openapi.json` - paths above.
