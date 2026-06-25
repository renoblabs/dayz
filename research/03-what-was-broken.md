# 03 - What Was Broken

Blunt. Analysis of `dayzAPI` against reality. No code changes, just the diagnosis.

## Short version

The backend is fine. The mod half doesn't run. The positioning gets you put under a microscope for nothing. You duplicated DaemonForge UniversalAPI without a reason the scene would care about, named it "Hive" (which means something specific and politically charged in the DayZ world), and shipped a marketing-heavy README with "production-ready" all over it while the PBO can't actually load.

## 1. The Enforce SDK isn't one SDK, it's two partial ones that disagree

Files:
- `sdk-enforce/HiveApi.c` - "v1" attempt
- `sdk-enforce/HiveApiMod/scripts/4_world/HiveApiClient.c` - "v2" attempt

They model the REST API differently and both of them only partly match the real thing:

### v1 (`HiveApi.c`)
```c
RestContext ctx = GetRestContext();
RestRequest req = new RestRequest(url, ERestMethod.PUT);
req.SetHeader("X-API-Key", HIVE_KEY);
req.SetTimeout(HIVE_TIMEOUT_MS);
ctx.Send(req, callback);
```
- Uses an imagined `RestRequest` class, `ERestMethod.PUT` enum, `ctx.Send(req, cb)` pattern.
- Callbacks are `RestCallback` with `OnSuccess(RestResponse)` / `OnError(RestResponse)` and `response.GetBody()` / `response.GetCode()`.
- Uses `JsonReader`/`JsonValue`/`JsonWriter` for structured parsing.
- Stores callbacks as `func m_onSuccess` member fields.

### v2 (`HiveApiClient.c`)
```c
RestContext ctx = GetRestApi().GetRestContext(url);
ctx.SetHeader("Authorization: Bearer " + token);
ctx.POST(cb, "", requestBody);
```
- Uses `ctx.POST(cb, str, body)` / `ctx.PUT` / `ctx.GET`, which is closer to how some community wrappers document it.
- Callbacks are `RestCallback` with `OnSuccess(string data, int dataSize)` / `OnError(int errorCode)` / `OnTimeout()`.
- JSON parsed by hand with `IndexOf("\"access_token\":\"") + 16`.
- Stores callbacks as `func m_successCb` too, but with different invocation contract.

**Neither is fully the real API.** The actual DayZ REST API surface is thin, quirky, and its documentation is scattered across Bohemia community wiki + DayZ-Expansion source + community forum posts. The real public surface uses `CallRestApi()`-style entries and `RestCallback` with the `string,int` shape - but various custom wrappers exist. You combined fragments of all of them into two mutually incompatible attempts.

**Consequence:** Neither file will compile against a real DayZ server build without edits. This is dead code until someone puts hands on it with Workbench open and the actual engine API in front of them.

## 2. Manual JSON string concatenation + substring-based parsing

From `HiveApiClient.c`:
```c
string requestBody = string.Format(
    "{\"platform_uid\":\"steam:%1\",\"cluster_id\":\"%2\",...",
    steamID, clusterID, ...
);
```
And:
```c
int tokenStart = data.IndexOf("\"access_token\":\"") + 16;
int tokenEnd = data.IndexOf("\"", tokenStart);
string token = data.Substring(tokenStart, tokenEnd - tokenStart);
```

Problems:
- If a steam ID or server ID ever contains a quote, a brace, or a backslash (they usually don't, but payloads absolutely will once you start serializing inventory), the output is invalid JSON.
- Substring parsing breaks the moment the API changes field order or adds nested fields.
- Enforce has `JsonFileLoader`, `JsonSerializer`, `JsonReader`/`JsonWriter` available. v1 uses them; v2 throws them away. Pick one.
- No escaping of user-controlled strings = a future server that lets users name something with a `"` in it sends broken JSON silently.

## 3. Mod packaging is incomplete

`config.cpp` declares:
```
class HiveApiMod {
    dir = "HiveApiMod";
    requiredAddons[] = { "DZ_Data", "DZ_Scripts" };
    class gameScriptModule    { files[] = {"HiveApiMod/scripts/3_game"}; };
    class worldScriptModule   { files[] = {"HiveApiMod/scripts/4_world"}; };
    class missionScriptModule { files[] = {"HiveApiMod/scripts/5_mission"}; };
};
```
What's missing:
- **No `3_game` or `5_mission` folders exist.** Only `4_world` is populated. The `config.cpp` declarations point at directories that don't exist.
- **No `.bikey` / `.biprivatekey` / `.bisign`.** The mod is unsigned. It will not load on any server that has `verifySignatures = 2;` set (which is the only correct production value).
- **No PBO output.** There's no build step that packs `HiveApiMod/` into a PBO via Addon Builder or Mikero's pboProject. Nothing in `Makefile` or CI even references DayZ Tools.
- **No `meta.cpp`** (Workshop metadata).
- **No `requiredAddons` for Community Framework.** If this ever ends up doing anything non-trivial it will need CF in the stack, and the load order matters (CF must be first).
- **The `modded class MissionServer`** exists, but there's no guarantee `MissionServer` is the right class to hook in your deployment target - and more importantly, `InvokeOnConnect` / `InvokeOnDisconnect` are not the only places a PlayerBase lifecycle fires. Character creation happens in a more nuanced dance involving `CreateCharacter`, `OnClientNewEvent`, etc. You hooked the simplified lifecycle and you'll miss events.

## 4. The name "Hive" is politically loaded

"Hive" in DayZ specifically refers to the central character persistence database. The current state of the world:
- **Only Bohemia operates the public hive.** It's limited to their official servers. Third parties cannot rent into it.
- **All community/modded servers use local per-server persistence** (`mpmissions/<mission>/storage_1/players.db` SQLite + `*.bin` files).
- Cross-server character sharing **is not natively supported** and exists only via modded systems like **MapLink Hive** (on Daemonforge's UniversalAPI webservice).

So a project calling itself "HiveAPI" claiming "cross-server character and inventory synchronization" reads to anyone in the scene as one of three things:
1. A clone of MapLink Hive / UniversalAPI.
2. Someone trying to resurrect the ARMA 2 / DayZ Mod central hive model (which nobody wants and Bohemia has moved away from).
3. Something cheat-adjacent, because anything that _writes_ to character state from outside the game is the exact attack surface used for item dupes and teleports.

Bohemia's enforcement history is a mix of (a) removing mods that bundle malicious DRM / anti-reverse-engineering obfuscation, (b) responding to DMCA claims (legitimate or abusive), and (c) reining in monetization that gates gameplay. A repo named "HiveAPI - production-ready cross-server character and inventory synchronization system" with `REQUEST_SIGNATURE_REQUIRED: false` defaulted on, `CORS: allow_origins=["*"]`, and an `/v1/admin/` endpoint that lets you rewrite any character's inventory, is _exactly_ the shape of thing that gets screenshotted into a server-admin Discord with a "look at this dupe tool" caption. Even if you'd never use it that way.

## 5. Security posture vs. claims

The README says "Security First - JWT authentication, idempotency keys, and full audit logging."

The code says:
- `CORSMiddleware` is `allow_origins=["*"]` + `allow_credentials=True` + `allow_methods=["*"]` + `allow_headers=["*"]`. This combination is actually rejected by modern browsers (credentials + wildcard origin), but more importantly it's the opposite of "security first."
- Every inventory and character mutation checks `character.owned_by_server != request.server_id`, logs a warning, then **proceeds anyway** if `REQUEST_SIGNATURE_REQUIRED` is false:
  ```python
  if not settings.REQUEST_SIGNATURE_REQUIRED:
      logger.info(f"Allowing inventory apply due to REQUEST_SIGNATURE_REQUIRED=False")
  ```
  And `REQUEST_SIGNATURE_REQUIRED` is set to `True` _in the Settings class default_, but `.env` templates and quick-start paths all set it false. In practice, as deployed by a new user following `QUICK_START.md`, any server in the cluster can rewrite any other server's characters.
- `ORIGIN_SECRET` is defaulted to empty string. If you don't set it, the "origin verification middleware" simply becomes a no-op:
  ```python
  if settings.ORIGIN_SECRET:
      ...
  ```
- `ADMIN_PASSWORD` defaults to empty. Comment in code says "empty disables auth." The dashboard exposes full event history by default.
- JWT is configured for RS256 but there's no key-rotation story, no key storage story, no signature verification in the `server-login` path that's actually enforced in tests (tests just call the endpoint directly in dev mode).
- SQL schema uses `String` primary keys storing UUID strings instead of native `UUID` columns (PostgreSQL has native UUID type that's faster and smaller). Not a security issue, but signals the schema was written generically and wasn't tuned.

None of this is unfixable. Most of it is the normal "dev defaults too permissive for prod" trap. The problem is the _gap between the README's claims and the actual defaults_.

## 6. The checksum / "CRDT-like" inventory is oversold and underimplemented

`services/inventory.py` has `compute_inventory_checksum(inventory)`, `apply_ops(inv, ops)`, `detect_conflicts(...)` (I didn't read the file but it's clearly there from the router imports).

The router's `apply` endpoint:
- Takes `base_checksum` from the client.
- Compares to `character.inventory_checksum`.
- If mismatch -> returns conflict.
- Otherwise applies ops and recomputes checksum.

This is not a CRDT. It's an **optimistic concurrency / compare-and-swap** (CAS). A real CRDT would let two concurrent modifications merge without a conflict. Calling it "CRDT-like" is marketing. Nothing wrong with CAS - it's the right primitive for inventory - but you've put a trendy label on a boring, correct pattern and it reads as a tell that you were producing this by prompting an LLM rather than from first principles.

## 7. You didn't integrate with actual DayZ persistence

In `HiveApiCharacterSync.c`:
```c
override void InvokeOnConnect(PlayerBase player, PlayerIdentity identity) {
    ...
    HiveApiClient.ClaimCharacter(steamID, CLUSTER_ID, SERVER_ID, spawnPos);
}
```

Problems:
- DayZ's vanilla character persistence (the `players.db` SQLite + `dynamic_*.bin` files in `mpmissions/<mission>/storage_1/`) is **still running**. The engine spawns the player from _its_ storage, then your mod tries to overlay state from the API. What happens when they disagree Unaddressed.
- Inventory "gathering" via `player.GetInventory().EnumerateInventory(InventoryTraversalType.PREORDER, cargoItems)` gets you item _references_, but you're only capturing `GetType()` + `quantity=1`. You lose:
  - Item health / damage state
  - Attachments / cargo (nested inventory)
  - Liquid/quantity for stackables (`quantmin`/`quantmax` from types.xml)
  - Ammo loaded in weapons
  - Wetness, temperature, food spoilage state
  - Paint state, scope zero, attached suppressor, everything that matters in DayZ
- Inventory "restoration" is completely missing. There is no code to `ClaimCharacter` -> receive inventory -> spawn items on the player. You write state to the API, but never read it back and apply it.
- No handling of "server A says player has gear, server B has different gear, player logs into server B" race. The `MoveTicket` shape in the schema suggests you meant to build it; you didn't.

So the Enforce mod as-written would: (a) not compile; (b) if it did, it would just mirror partial type-name data to a remote database and never read it back. It's a one-way telemetry firehose, not a persistence system.

## 8. The "modded class PlayerBase" extension is dead code
```c
modded class PlayerBase {
    private string m_hiveCharacterID = "";
    void SetHiveCharacterID(string id) { m_hiveCharacterID = id; }
    string GetHiveCharacterID() { return m_hiveCharacterID; }
};
```
Nothing in the file calls `SetHiveCharacterID`. The `HiveApiClient.OnClaimCharacterSuccess` parses a character ID out of the response but has a `// TODO: Store character_id on player object` comment next to where it would call `SetHiveCharacterID`. `MissionServer.SavePlayerCharacter` calls `GetCharacterID(steamID)` which reads from a separate `m_playerCharacterMap` on the mission server that is never populated. So: the SteamID -> characterID mapping table is empty forever, every call to `SavePlayerCharacter` bails out at the `if (characterID == "")` early return.

As shipped, even if the REST API contract were correct, the mod would never save anything.

## 9. Things that would get the server owner's attention (bad kind)

Running this on a real server would light up:
- **BattlEye / anti-cheat.** The pattern "script makes outbound HTTP request every N seconds containing character state" is fine if it's from a known mod like UniversalAPI. From an unsigned one-off PBO it's a yellow flag. Nothing here is actually malicious, but it's the exact traffic shape _malicious_ mods use.
- **RCON / admin log spam.** `Print("[HiveAPI] ...")` on every connect / disconnect / heartbeat / save pollutes the server RPT log in a way that makes debugging unrelated issues harder.
- **Performance.** The auto-save timer is `300s` = 5 minutes, gathering full inventory via `EnumerateInventory(PREORDER)` on every tick for every player. On a 60-slot server that's a nontrivial amount of script-side iteration. DayZ server FPS is already a known pain point (see `04-stack-architecture.md`), and every script mod that touches PlayerBase regularly is one more thing taking tick budget.
- **Ban-list flags.** CFTools Cloud / Battlemetrics monitors what mods are loaded on a server. An unsigned, unpublished, internal-only mod named "HiveApiMod" making HTTP calls out would draw questions from any large community running CFTools.

## 10. The external server ticket angle

There were external server issues recently and an API/hive prototype may have been part of the loaded stack. Based on this repo, three plausible ways this could have caused trouble:

1. **Persistence corruption suspicion.** Anything that writes outside the engine's own storage can look like the cause when the server's `.bin` files get wedged. If an admin was running a variant of this code and vanilla persistence got corrupt around the same time, the first thing to get blamed would be the non-standard mod - even if this mod wasn't the cause. Ticket to Bohemia support would likely include "what mods are loaded" as step one.
2. **Infinite retry loop on network failure.** `HiveApi.c` retries with `Math.RandomInt(50, 150)` jitter if `HIVE_RETRY > 0`, scheduling through `CallLater`. If `HIVE_URL` is unreachable, this will queue retries indefinitely against every operation. Could show up as "server freezing up" or "lag spikes" at random intervals.
3. **BattlEye / RestApi misuse.** If the mod was loaded on a server without the `-doLogs` / allowed-hosts configuration that DayZ requires for RestApi outbound calls, the engine logs errors every attempt. Not a crash, but a lot of RPT noise that support tickets hate.

I don't have visibility into what the actual ticket was about. But "old prototype mod making outbound HTTP calls in a retry loop with no circuit breaker" is a reasonable suspect. If any external live server is still running a variant of this code, pull it immediately.

## 11. Business / positioning problems

Separate from the code:

- **"HiveAPI" is a recognizable brand.** The name collides with the connotation of Bohemia's official hive and with the existing MapLink **Hive** mod. If you ship this publicly under the name, you're either claiming a term with ambiguous ownership, or you're inviting confusion with Bohemia's own infrastructure. Neither is good for a quiet launch.
- **DaemonForge's UniversalAPI already exists, is adopted, is maintained, and is the de-facto standard for this category.** There's no stated differentiator in your repo that would make a server owner switch. "Mine uses Postgres instead of Mongo" is not a value prop for a DayZ admin.
- **"Multi-tenant" is a SaaS concept.** If you're hosting it for other servers, you're running a commercial service, which in combination with anything that affects gameplay triggers Bohemia's monetization rules. Even if you don't charge, the _shape_ of the business is the thing Bohemia watches.
- **README claims "Free to use for personal and commercial server networks."** That's a license claim. There's no LICENSE file in the repo. Implicit license = all rights reserved = contradicts the README.

## Summary - the damage report

| Category | Status | Fix cost |
|---|---|---|
| Backend API design | Fine. Slightly overbuilt but correct. | - |
| Backend security defaults | Permissive in dev, hardened in prod if you remember to flip every flag. | Low - tighten defaults, require explicit opt-in to open modes. |
| Enforce v1 SDK (`HiveApi.c`) | Doesn't match real engine API. | Delete. |
| Enforce v2 SDK (`HiveApiMod/`) | Doesn't compile as-is, missing folders, missing keys, inventory capture is lossy, save path is dead. | Scrap and rewrite once you actually know Enforce. |
| Branding as "HiveAPI" | Politically loaded, collides with existing mod names. | Rename before any public exposure. |
| Marketing-heavy README | Claims not supported by code. | Rewrite to match reality or delete the repo public-side. |
| Positioning as DaemonForge clone | No differentiator, adopting a saturated category. | Pick a different wedge. |
| License | Missing / contradicted. | Add LICENSE file. Decide terms. |

**The honest call:** The backend is reusable but mis-shaped for the actual problem. The Enforce side is throwaway. The branding is a liability. If this becomes the foundation of your DayZ launch, you're starting on the back foot. If you treat it as educational scar tissue and keep the _architectural_ lessons (multi-tenant data model, idempotency, event log, observability - all good instincts) and throw the rest away, you come out ahead.

See `06-leverage-points.md` for what to actually build instead and `07-plan.md` for the path.
