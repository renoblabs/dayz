# TrophyHunter - Design Spec

Date: 2026-04-19
Status: Draft, user-approved for implementation planning
Scope: First-class DayZ mod that pairs with BossSignal and an external boss-content mod to reward top-damage players with rare, visible, losable trophy items across a DayZ server network.

> Current implementation note: this is a design spec. Backend trophy routes and mod-side award helpers exist, but the full in-game award loop, participant damage reliability, transfer/grace behavior, and persistence edge cases still need first-play validation before this can be treated as production-ready.

---

## 1. Purpose

BossSignal alone is a dashboard. TrophyHunter is the second half of the stack: a functional in-game mod that makes every boss kill on a network mint a visible status item for one player. It turns external boss-mod gameplay into a scarcity-driven legend engine, and it turns BossSignal's dashboard into a live trophy map.

The north star: BossSignal *and* TrophyHunter running together on a server network. TrophyHunter exists to make existing boss content matter more.

## 2. Player experience

Five trophy items, one per boss type. Each is a reskin of an existing DayZ item for MVP (no custom 3D art) so the first build can ship fast.

> The boss names below are **illustrative placeholders**. TrophyHunter is boss-mod-agnostic: the boss class allowlist is configured in `bosses.json`. Substitute the actual class names of whatever boss-content mod you license/run.

| Boss class (illustrative) | Trophy item | Slot | Visual cue |
|---|---|---|---|
| Warlord | Warlord's Crown | Head | Bloody iron crown |
| Abomination | Abomination's Jaw | Armband | Oversized jawbone |
| Tank | Heavy Tank Plate | Chest | Dull metal plate |
| Necromancer | Necromancer's Skull | Head | Green-glow skull |
| Hunter Elite | Hunter's Fang | Neck | Subtle pendant |

**Award rule:** on boss death, the top-damage player in the encounter gets the trophy spawned into their inventory.

**Rules:**
- One holder per player per trophy type (second-place gets the award if top-damage already holds it).
- Carryable and wearable - visible on the player character to other players in-world.
- Tradeable - can be given, dropped, or looted from a corpse.
- Droppable on death - killer loots the trophy from the body. PvP meta.
- 10-minute grace period after award during which the trophy is immune to being dropped or looted. If the holder dies inside the grace window, the trophy is removed from the body and restored to the holder's inventory on respawn/next login (it does not appear on the corpse at all). This prevents insta-camp grief without the hand-wavy "killer picks it up but it teleports back" semantics.
- Persistent provenance - the trophy item remembers original holder name, original server, and original claim timestamp. Later holders do not overwrite this. On inspect, the trophy reads: *"Warlord's Crown - claimed by DarkHunter99 on server_03, 2026-04-19 14:32."*
- Network-roaming - trophy follows the player across servers *if* the network runs a shared character hive. If each server has isolated characters, trophies are server-local. This is confirmed per-network during pre-deployment, not a design decision we need to make now.

**Public announcement:** on award, the mod emits a global chat line: *"DarkHunter99 has claimed the Warlord's Crown on server_03."*

## 3. Architecture

Three components, one-way data flow.

```
   ┌-----------------┐      ┌------------------┐      ┌------------------┐
   | External        |      | TrophyHunter     |      | BossSignal       |
   | boss mod        |      | mod (NEW)        |      | backend          |
   | (existing)      |-----▶|                  |-----▶|                  |
   | Spawns bosses   |      | - OnEntityKilled |      | - POST trophy    |
   | Players damage  |      |   allowlist hook |      |   event          |
   | Boss dies       |      | - Top-damage     |      | - Leaderboard    |
   `-----------------┘      |   lookup (via    |      | - Provenance log |
                            |   BossSignal     |      | - SSE broadcast  |
                            |   damage map)    |      |                  |
                            | - Spawn trophy   |      | Dashboard Trophy |
                            | - Announce       |      | Hall panel       |
                            `------------------┘      `------------------┘
```

### 3.1 TrophyHunter Enforce mod (`mods/TrophyHunter/`)

Four `.c` files, one `config.cpp`, one JSON config.

- `config.cpp` - defines the five trophy item classes, each deriving from a DayZ base item class. Mission init hook registers TrophyHunter as a server-side mod. Requires CF (Community Framework) as a dependency so we reuse its RPC + config patterns that BossSignal already depends on.
- `config/bosses.json` - allowlist mapping boss class names to trophy item classes. Admin-editable. Loaded at server start. Example:
  ```json
  {
    "bosses": [
      {"class": "ExampleBoss_01", "trophy": "WarlordsCrown"},
      {"class": "ExampleBoss_02", "trophy": "AbominationsJaw"}
    ]
  }
  ```
- `scripts/5_Mission/TrophyHunterConfig.c` - reads `bosses.json`, exposes shared-secret, BossSignal base URL, grace-period seconds. Mirrors `BossSignalConfig` layout in the sibling mod.
- `scripts/5_Mission/TrophyHunterListener.c` - hooks `OnEntityKilled` globally, filters by the allowlist, kicks off award flow. Shares the pattern used in `BossSignalEmitter.c` today.
- `scripts/5_Mission/TrophyAwarder.c` - given a dead-boss event: fetches top-damage player from BossSignal, spawns the trophy into their inventory (or at their feet if inventory is full), stamps provenance attributes, fires the global chat announce, POSTs `trophy.awarded` to BossSignal.
- `scripts/5_Mission/TrophyProvenance.c` - attaches the provenance attributes to a trophy item. Reads them on inspect. Survives the item being looted by a new holder (original holder info stays frozen).

### 3.2 BossSignal backend additions

- New event type `trophy.awarded` accepted at existing `POST /api/v1/events` (same shared-secret auth, same idempotent ingest pattern). Event payload: `encounter_id`, `boss_class`, `trophy_class`, `holder_name`, `holder_player_id`, `server_id`, `timestamp`, `original_holder_name`, `original_server_id`, `original_timestamp`.
- New `GET /api/v1/encounters/{encounter_id}/top-damager` - used by TrophyHunter to look up who gets the trophy. Returns top-damage player ID and name, falls through the damage list if the top player is offline/disconnected.
- New `app/routers/trophies.py`:
  - `GET /api/v1/trophies` -> all currently-held trophies across the network.
  - `GET /api/v1/trophies/leaderboard` -> aggregated by player and by server.
  - `GET /api/v1/trophies/{trophy_id}/history` -> provenance chain.
- New SQLAlchemy model `Trophy` - one row per award, append-only. Current holder is derivable from the latest `trophy.transferred` or `trophy.awarded` event for a given trophy instance.
- New event type `trophy.transferred` for later (when a killer loots a trophy). MVP can ship without it; we add it in v0.2 after first-play validates the basic award flow.

### 3.3 Dashboard (`bosssignal-backend/static/dashboard.html`)

- New **Trophy Hall** panel - always-visible strip at the top-right of the dashboard showing five icons, one per trophy, with current holder name and server.
- Updates live via the existing SSE connection - no new WebSocket, no new polling.
- Clicking a trophy icon opens a small modal showing provenance chain for that trophy instance.

## 4. Data flow

Happy path, ordered:

1. External boss-content mod spawns a boss on `server_03`. BossSignal logs `boss.spawned` only if the external mod calls `BossSignalAPI.EmitBossSpawned(...)` or an equivalent event is sent through the API.
2. Players damage the boss. BossSignal needs a reliable damage feed so the encounter's participant map is populated; this is still a validation item.
3. Boss HP hits 0. The game fires `OnEntityKilled` for the boss entity.
4. `TrophyHunterListener.OnEntityKilled` checks the entity's class against `bosses.json` allowlist. Miss -> ignore. Hit -> continue.
5. `TrophyAwarder` calls `GET /api/v1/encounters/{encounter_id}/top-damager` on BossSignal.
6. Backend returns the top-damage player (with fallback logic for offline players).
7. `TrophyAwarder` checks if that player already holds this trophy type (via a server-side inventory scan or a BossSignal lookup). If yes, fall through to #2 damager, and so on.
8. `TrophyAwarder` spawns the trophy item in the chosen player's inventory. If inventory is full, spawns at their feet with a 2-meter marker.
9. `TrophyProvenance` stamps the item with `OriginalHolder`, `OriginalServer`, `OriginalTimestamp`, `GraceUntil` (now + 10 min).
10. `TrophyAwarder` calls global chat: *"DarkHunter99 has claimed the Warlord's Crown on server_03."*
11. `TrophyAwarder` POSTs `trophy.awarded` to BossSignal.
12. Backend stores the event, writes the `Trophy` row, broadcasts SSE update.
13. Dashboard Trophy Hall updates live in every open browser.

## 5. Edge cases

| Case | Resolution |
|---|---|
| Top damager logged out mid-fight | Fall through damage list until a player is found online. If all offline, log `trophy.skipped` with reason `no_online_damagers` and skip. |
| Tie on damage (within 100 damage) | Award to the player who landed the killing blow. |
| Top damager already holds the same trophy type | Award to the next-highest damager. One holder per player per trophy type. |
| No damage at all (scripted despawn or bug) | Log `trophy.skipped` with reason `no_damagers`. No award. |
| Two bosses killed on different servers in the same second | Both awards fire independently. Per-encounter idempotency key at BossSignal prevents duplicates. |
| Trophy holder's inventory full | Spawn at their feet with a 2m ground marker. Announce adjusts to: *"claimed but dropped - grab it fast."* |
| Trophy holder disconnects before item lands | Game's persistence saves the item in their slot or on the ground near them. Trophy re-appears next login. |
| Holder killed inside grace period | Trophy is removed from the body on death so it never appears on the corpse. Trophy is restored to the holder's inventory when they respawn or next log in. Killer gets nothing. |
| Holder killed after grace period | Trophy remains on the corpse. Killer can loot it normally. Provenance updates with the new holder; `OriginalHolder` stays frozen. |
| Two players claim the final blow bug | Tie-break on damage total; if still tied, first `entity.killed` packet timestamp wins. |
| Server restart mid-fight | Encounter is abandoned (no award). BossSignal already handles this. |
| Allowlist misconfigured (unknown boss class in JSON) | Mod warns at server startup with a readable log line. No crash. |

## 6. Testing plan

Three layers.

**Layer 1 - backend unit/integration (local, no DayZ).**
Extend the existing test harness to fire a synthetic `boss.killed` plus a synthetic `OnEntityKilled` from a fake TrophyHunter client. Assert:
- `GET /api/v1/encounters/{id}/top-damager` returns correct ordering.
- `POST /api/v1/events` accepts `trophy.awarded`.
- `GET /api/v1/trophies` reflects the new holder.
- SSE clients receive the trophy update.
Ship these as Python pytest cases in a new `bosssignal-backend/tests/test_trophies.py`.

**Layer 2 - dashboard visual (local, no DayZ).**
Run the backend, fire synthetic trophy awards, open the dashboard, confirm the Trophy Hall panel renders and updates live. Manual verification is fine for MVP.

**Layer 3 - in-game (real DayZ test server, this rig).**
On the Windows gaming rig, after DayZ Tools is installed and the PBO signed:
1. Start a local DayZ server with BossSignal + TrophyHunter + a placeholder boss mod, or use BossSignal's simulator-generated fake bosses for backend/dashboard validation before live DayZ validation.
2. Spawn a boss, damage it with one player, kill it. Confirm: trophy in inventory, chat announce fires, dashboard updates, provenance attributes set.
3. Spawn a second boss, have a second player damage more. Confirm top-damage award goes to the right player.
4. Have two players both damage a boss. Confirm award goes to the top damager.
5. Drop and re-pick up trophy. Confirm provenance persists.
6. Die with trophy outside the grace window. Confirm killer loots it and the history updates.
7. Die with trophy inside the grace window. Confirm trophy returns to original holder.

## 7. Pre-deployment unknowns

These block real-network deployment, not local development. Capture as a checklist in `docs/TROPHYHUNTER-PREDEPLOY.md`.

1. **Identify the external boss-content mod.** Need an exact Workshop mod name, Workshop ID, or server mod list. Strategies: install DayZ on this rig, join a target server once, inspect the workshop folder auto-downloads, or ask the mod author/server operator directly.
2. **Extract external boss class names.** Once the Workshop page is found, unpack the PBO with DayZ Tools and read `config.cpp` for class names that look like boss variants. Populate `bosses.json`.
3. **Confirm the boss mod emits damage signals BossSignal can read.** BossSignal's current damage tracking relies on `OnEntityKilled` + generic damage hooks. If the external mod bypasses these (custom damage pipeline), fall back to BossSignal's own damage tracking once wired for that path.
4. **Confirm the target network has shared-character hive** (required for network-roaming trophies). If not, ship with server-local trophies for MVP and add hive roaming later.
5. **Sign the PBO with a keypair.** Requires DayZ Tools + `sign-keygen.bat` one-time setup. The public `.bikey` has to be installed on the target server or the server cannot load the mod.
6. **Get mod onto the target server.** Requires coordination with the server operator to install and key-whitelist the mod.

## 8. Explicitly out of scope (YAGNI)

- Custom 3D models - reskin existing DayZ items first.
- Trophy tiers - all trophies are equal for MVP. No gold/silver/bronze.
- Trophy upgrades - killing the same boss multiple times does not upgrade the trophy. Later feature.
- Trader NPC integration - trophies cannot be sold to traders. Later feature.
- Anti-dupe protection beyond what DayZ server-side inventory already provides. If server persistence is tuned well, this is a non-issue.
- Leaderboard points, XP, achievements. The leaderboard is just a list of current holders. No scoring system.
- Steam Workshop publication. Ship server-side only for the first deployment. Publish later if wanted.
- Multi-mod-support for additional boss mods. Eventually the allowlist pattern makes this trivial; not an MVP concern.

## 9. Success criteria

- On the demo, the operator sees a boss die on one target server and watches the trophy appear in the killer's inventory **and** on the dashboard's Trophy Hall at the same time.
- Trophies are visible to other players on the character model.
- Provenance survives trophy transfers.
- No server crashes, no trophy duplication, no repeated awards for the same encounter.

## 10. Known risks

- **External boss mod internals unknown.** Mitigated by configurable allowlist + `docs/TROPHYHUNTER-PREDEPLOY.md`.
- **DEVLOG-NNN validation items in BossSignal are not yet resolved.** TrophyHunter depends on BossSignal's damage tracking being correct. If first-play validation reveals those assumptions are wrong, trophy awarding will misfire. This is the reason first-play is the next milestone for BossSignal itself.
- **CF dependency.** If the target server does not already run CF, the operator needs to install it. Almost every modded DayZ server does, so this is low risk.
- **PBO signing is a one-time process.** Easy to get wrong the first time. First-play will flush this out.
