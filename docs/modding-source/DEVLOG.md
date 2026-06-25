# BossSignal - Dev Log & First-Play Validation Checklist

Every assumption made while writing code before owning the game. This is a validation checklist, not a guarantee that each assumption is already proven in live gameplay. Treat participant damage, kill hook edge cases, and external boss-mod compatibility as untrusted until confirmed on a local DayZ server.
Ordered by priority. Resolve in sequence on Day 1 of playing.

---

## How to use this log

Each entry has:
- **What we assumed** - what the code currently does
- **How to validate** - exact test to run on first play
- **Risk level** - how badly wrong this assumption breaks things
- **Fix if wrong** - what to change in which file

---

## DEVLOG-001 | Config file loading API
**File:** `3_game/BossSignalConfig.c`
**Assumed:** Config is hardcoded in static class. v0.2 will read from JSON.
**Validate:** On first play, search Bohemia wiki for `JsonFileLoader` - confirms API exists and path format for server profile directory.
**Risk:** Low (hardcoded config works for v0.1 - this is just a v0.2 upgrade path)
**Fix if wrong:** No fix needed for v0.1. Keep config hardcoded.

---

## DEVLOG-002 | GetHealth() API for MaxHealth
**File:** `3_game/BossSignalTypes.c` -> `BossEncounter` constructor
**Assumed:** `entity.GetHealth("GlobalHealth", "Health")` returns the entity's max health.
**How to validate:**
  1. Spawn a test entity on local server
  2. Print `entity.GetHealth("GlobalHealth", "Health")` in RPT log
  3. Compare to what you'd expect for a normal zombie (should be ~100-200)
  4. Compare to a boss entity (should be much higher - 10,000+)
**Risk:** Medium - if wrong, `m_MaxHealth` is wrong and health-% calculations in heartbeats/dashboard are garbage.
**Fix if wrong:** Try `entity.GetMaxHealth("GlobalHealth")` or `entity.GetHealth("GlobalHealth")` - check Bohemia wiki for the correct two-argument vs one-argument form.

---

## DEVLOG-003 | String.Replace() method
**File:** `4_world/BossSignalJSON.c` -> `BossSignalJSON.Str()`
**Assumed:** `s.Replace(find, replace)` works as an in-place string method on Enforce strings.
**How to validate:**
  1. In a test mod, run: `string s = "hello\"world"; s.Replace("\"", "\\\""); Print(s);`
  2. RPT should show: `hello\"world` (the quote escaped with a backslash)
**Risk:** HIGH - if Replace() doesn't exist or has a different signature, every JSON payload with player names containing quotes or backslashes will be malformed. This would silently corrupt events in the backend.
**Fix if wrong:**
  - Option A: Replace with char-by-char iteration: `for (int i = 0; i < s.Length(); i++) { ... }`
  - Option B: If DayZ has `string.Replace(from, to, ref string out)`, use the out-param form
  - File to edit: `4_world/BossSignalJSON.c`, the `Str()` method

---

## DEVLOG-004 | float.ToString() decimal separator
**File:** `4_world/BossSignalJSON.c` -> `BossSignalJSON.Num()`
**Assumed:** `float.ToString()` produces a dot as the decimal separator (e.g. `"3.14"`).
**How to validate:** `Print(3.14.ToString());` - check RPT output for dot vs comma.
**Risk:** Medium - if the server OS locale uses comma, JSON numbers become invalid (`3,14` breaks parsers).
**Fix if wrong:** Use integer math: `string i = ((int)val).ToString(); string f = ((int)((val - (int)val) * 100)).ToString(); return i + "." + f;`

---

## DEVLOG-005 | GetRestApi() server-side availability
**File:** `4_world/BossSignalClient.c`
**Assumed:** `GetRestApi()` is available in `4_world` scripts running server-side.
**How to validate:** Compile the mod and load it. If RPT shows `[BossSignal] HTTP client ready -> ...`, confirmed. If it crashes or shows a null pointer error, check if `GetRestApi()` needs to be called from `5_mission` instead.
**Risk:** HIGH - if wrong, the HTTP client won't initialize and all events are silently dropped.
**Fix if wrong:** Move `BossSignalClient` instantiation into `BossSignalEmitter.Init()` in `5_mission` by making it a lazy-init - only create the `RestContext` on first `.Post()` call from within `5_mission` context.

---

## DEVLOG-006 | RestContext.POST() signature
**File:** `4_world/BossSignalClient.c` -> `BossSignalClient.Post()`
**Assumed:** `m_Ctx.POST(callback, path, body)` - callback first, path second, body third.
**How to validate:**
  1. Start test server with BossSignal loaded
  2. Watch RPT for `[BossSignal] OK server.started` or an error code
  3. If you see HTTP 202 on the backend, signature is correct
  4. If RPT shows `[BossSignal] ERROR ... code=-1` or a compile error, the signature is wrong
**Risk:** CRITICAL - wrong signature means zero events ever reach the backend.
**Fix if wrong:**
  - Try: `m_Ctx.POST(path, body, callback)` (order swapped)
  - Try: `m_Ctx.POST(callback, body)` (no path - path set separately)
  - Cross-reference: `sdk-enforce/HiveApiMod/scripts/4_world/HiveApiClient.c` in the old repo for the variant the original author used (was ctx.POST(cb, "", body) - note the empty string middle arg)

---

## DEVLOG-007 | RestCallback GC behaviour
**File:** `4_world/BossSignalClient.c` -> `m_PendingCallbacks`
**Assumed:** Engine may GC callbacks before they fire unless we hold strong refs.
**How to validate:** Run test harness (simulate_boss_encounter.py), watch RPT. If callbacks fire cleanly (OnSuccess logs appear), GC is handled. If you see crashes or silent drops, the engine IS GC'ing callbacks.
**Risk:** Low-Medium - worst case is silent event drops after ~32 events, not a crash.
**Fix if wrong:** Increase MAX_PENDING or keep callbacks indefinitely (bounded memory).

---

## DEVLOG-008 | RestContext.SetHeader() format
**File:** `4_world/BossSignalClient.c` -> `BossSignalClient()` constructor
**Assumed:** `m_Ctx.SetHeader("Key: Value")` - colon-separated single string.
**How to validate:** After the first POST attempt, check backend logs. If the request arrives without the `X-BossSignal-Secret` header (401 error), the header format is wrong.
**Risk:** HIGH - if wrong, all requests return 401 Unauthorized and no events are stored.
**Fix if wrong:** Try `m_Ctx.SetHeader("Key", "Value")` (two-argument form). Also check if it's `m_Ctx.AddHeader()` instead.

---

## DEVLOG-009 | entity.GetID() return type
**File:** `4_world/BossSignalAPI.c` -> `GetEntityId()`, `5_mission/BossSignalEmitter.c`
**Assumed:** `entity.GetID()` returns an int or string that's unique per entity per session.
**How to validate:**
  1. Add a `Print("[BossSignal] entity ID: " + myEntity.GetID());` in a test mod
  2. Kill the entity and check the ID is stable up to the kill event
  3. Check if two different entities have different IDs
**Risk:** Medium - if IDs collide, boss encounters get confused with each other (unlikely but possible if ID is e.g. a pointer reused after GC).
**Fix if wrong:** Use `entity.GetPosition().ToString()` + spawn timestamp as composite ID (more fragile but guaranteed unique in practice).

---

## DEVLOG-010 | GetGame().GetPlayers() signature
**File:** `5_mission/BossSignalEmitter.c` -> `GetCurrentPlayerCount()` and `SendBossSpawned()`
**Assumed:** `GetGame().GetPlayers(array<Man> outArray)` fills the array by ref and the count is correct.
**How to validate:**
  1. On local test server with yourself connected, print the count
  2. Should be 1 (just you)
**Risk:** Medium - if wrong, player_count in heartbeats and boss.spawned events is always 0.
**Fix if wrong:**
  - Try: `GetGame().GetWorld().GetPlayers(players)`
  - Try: `array<Man> players = GetGame().GetPlayers()` (returns array directly)
  - Check CF source - CF may have a `EXTC_GetPlayerCount()` helper

---

## DEVLOG-011 | PlayerBase identity API
**File:** `5_mission/BossSignalEmitter.c` -> `ExtractKillerInfo()`
**Assumed:** `pb.GetIdentity().GetPlayerId()` returns Steam64 ID as a string.
**How to validate:**
  1. Kill something (or yourself) on test server
  2. Check RPT for `[BossSignal] Boss killed: ... by <name>`
  3. Your Steam64 ID should appear in the backend's participants list
**Risk:** Medium - if wrong, killer_player_id is empty string, which breaks cross-server aggregation in the dashboard.
**Fix if wrong:**
  - Try: `identity.GetId()` instead of `.GetPlayerId()`
  - Try: `identity.GetUID()` (some DayZ versions use this)
  - Try: `pb.GetIdentity().GetPlainId()` (seen in some community mods)

---

## DEVLOG-012 | GetItemInHands() return type
**File:** `5_mission/BossSignalEmitter.c` -> `ExtractKillerInfo()`
**Assumed:** `pb.GetItemInHands()` returns something castable to EntityAI.
**How to validate:** Kill a boss while holding an AKM. Check that `killer.weapon` in the database shows `"AKM"`.
**Risk:** Low - if wrong, weapon just shows as empty string. Cosmetic issue only.
**Fix if wrong:** Try `EntityAI.Cast(pb.GetItemInHands())` or `ItemBase.Cast(pb.GetItemInHands())`.

---

## DEVLOG-013 | map<K,V> iteration API
**File:** `5_mission/BossSignalEmitter.c` -> `BuildParticipantsArray()`
**Assumed:** `map.GetKey(i)` and `map.GetElement(i)` iterate by index.
**How to validate:** Run a multi-player boss kill on test server. Check that all participants appear in the `participants` array in the database.
**Risk:** Medium - if wrong, participant list is always empty. Kill is tracked but nobody gets credit.
**Fix if wrong:**
  - Try `foreach(string k, float v: m_ParticipantDamage) { ... }` (Enforce foreach syntax)
  - Or: convert to parallel arrays - `ref array<string> keys = new array<string>(); m_ParticipantDamage.GetKeyArray(keys);`

---

## DEVLOG-014 | MissionServer.OnEntityKilled() signature
**File:** `5_mission/BossSignalMission.c`
**Assumed:** `override void OnEntityKilled(EntityAI victim, EntityAI killer, Man killerPlayer)`
**How to validate:** This is the most likely thing to break on first compile. If you get a "function not found" or "override doesn't match" compile error in the RPT, the signature is wrong.
**Risk:** CRITICAL - if wrong, the mod compiles but the hook never fires and no kill events ever emit.
**Fix if wrong (in order of likelihood):**
  1. Remove `Man killerPlayer` param: `OnEntityKilled(EntityAI victim, EntityAI killer)`
  2. Use IEntity: `OnEntityKilled(IEntity victim, IEntity killer)`
  3. Check the DayZ 1.2x MissionServer source or ask in DZMC Discord: "what's the current OnEntityKilled signature"
  4. Fallback: hook into `PlayerBase.EEKilled(EntityAI source)` instead (fire from the victim side)

---

## DEVLOG-015 | MissionServer.OnUpdate() availability
**File:** `5_mission/BossSignalMission.c`
**Assumed:** `override void OnUpdate(float timeslice)` exists on MissionServer.
**How to validate:** Start server, wait 60 seconds. If you see `[BossSignal] OK server.heartbeat` in the RPT, OnUpdate works.
**Risk:** Medium - if OnUpdate doesn't exist, heartbeats never fire. Kill events still work.
**Fix if wrong:** Replace with CallQueue timer. In `OnInit()`:
  ```c
  GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM)
           .CallLater(m_BSigEmitter, "SendHeartbeat",
                      BossSignalConfig.HEARTBEAT_INTERVAL * 1000, true);
  ```
  Note: `CallLater` interval is in milliseconds. `true` = repeat.

---

## DEVLOG-016 | super.OnEntityKilled() call order
**File:** `5_mission/BossSignalMission.c`
**Assumed:** super must be called, and it's safe to call it before our logic.
**How to validate:** Load with another CF-based mod active. Verify neither mod breaks the other.
**Risk:** Low - super call is standard modded class pattern. Unlikely to be wrong.
**Fix if wrong:** Move our logic before super() call. Try both orderings if other mods break.

---

## Summary: highest-risk items to test on Day 1

| # | Item | File | Impact if wrong |
|---|------|------|----------------|
| 1 | RestContext.POST() signature | `BossSignalClient.c` | No events ever sent |
| 2 | SetHeader() format | `BossSignalClient.c` | All requests 401 |
| 3 | OnEntityKilled() signature | `BossSignalMission.c` | No kill events |
| 4 | GetRestApi() location | `BossSignalClient.c` | Client never inits |
| 5 | String.Replace() | `BossSignalJSON.c` | Malformed JSON |
| 6 | GetHealth() for MaxHealth | `BossSignalTypes.c` | Wrong health values |

**First-play order:** Get one kill event to appear in the backend. That validates items 1-4 simultaneously. Then check the dashboard shows the event. Then check participant data (items 11-13). Everything else is cosmetic.
