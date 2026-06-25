# First Play Checklist - DayZ Day 1

Your first 2-hour session. Every minute is research.
Have the DEVLOG open in a second monitor. Have the backend running locally.

---

## Before you launch the game

- [ ] Backend running via `docs/operations/runbook-local-stack.md` or direct dev server under `backends/bosssignal-backend`
- [ ] Dashboard open in browser: http://localhost:6700
- [ ] Run test harness to confirm dashboard works from `build-pipeline/test-harness`
- [ ] You should see fake boss events flowing into the dashboard
- [ ] DayZ Tools installed and P:\ drive mounted (needed for building the mod later)
- [ ] DEVLOG.md open - you're going to answer questions from it

---

## Session 1 - Vanilla official server (60 min)

**Goal:** Feel the game. Not mod research. Not rushing. Just live in it.

### First 20 minutes
- Spawn. Open inventory (Tab). Look at your UI - understand what everything is.
- Walk. Feel the movement. First person by default (right-click or scroll wheel).
- Find a building. Enter it. Open a door. Search a shelf.
- Get cold. Get hungry. Get thirsty. These are the primary survival drivers.

### 20-45 minutes
- Find a zombie. Watch it aggro. Kill it or avoid it.
- **Watch the zombie animation.** Note: does it have health stages (stumble/limp) Note the AI rhythm.
- Die. It's fine. This is research. Note how you felt when you died.
- Respawn. Repeat.

### 45-60 minutes
- Find another player. Watch what happens. Do nothing hostile. Just observe.
- Feel the tension of another human in the world. That tension is the whole game.
- Log off on the beach. Close game.

### Research notes to write down
- What's the death-to-PvP ratio you personally experienced (most deaths are environment on first play)
- What made you feel tense vs. safe
- What felt like it would benefit from a boss raid event (hint: the "nothing happening" stretches)

---

## Session 2 - Enforce mod compile test (30 min, same day or next day)

**Goal:** Get one event flowing from mod -> backend. Answer DEVLOG-005/006/008 first.

### Setup
1. SteamCMD - install a local DayZ server: https://community.bistudio.com/wiki/DayZ:Server_Installation
2. Start the local server with `@CommunityFramework;@BossSignal` in `-mod=`
3. Watch the RPT log file (usually `C:\DayZServer\DayZServer_x64.RPT`)

### What to look for in RPT on startup
```
[BossSignal] ═══════════════════════════════════════
[BossSignal]  BossSignal v0.1.0 active
[BossSignal]  Server  : server_01
[BossSignal]  Backend : http://localhost:6700
[BossSignal] ═══════════════════════════════════════
```
If you see this: the mod compiled and loaded. ok DEVLOG-014/015/016 safe.

```
[BossSignal] HTTP client ready -> http://localhost:6700
```
If you see this: GetRestApi() worked. ok DEVLOG-005 safe.

```
[BossSignal] OK  server.started -> /api/v1/events (Nb back, Xms)
```
If you see this: POST() works and backend accepted the event. ok DEVLOG-006/008 safe.

### If the mod doesn't load
- Check RPT for `Error` lines near `[BossSignal]`
- Most likely cause: config.cpp syntax error or wrong `requiredAddons` name
- Run `modctl diagnose` or DayZ Tools against `mods/BossSignal` to get syntax/runtime errors

### If events don't arrive at backend
- Check that `BACKEND_URL` in `mods/BossSignal/scripts/3_game/BossSignalConfig.c` is `http://localhost:6700` for the current local stack
- Check that `SHARED_SECRET` matches between mod and backend `.env`
- Check RPT for `ERROR POST` or `TIMEOUT POST` lines

### If `OnEntityKilled` never fires
- Kill a zombie on the test server (connect as a client with `-connect=127.0.0.1`)
- Nothing should appear in RPT yet for kills until we register a boss class
- To test the hook raw: add `Print("[BossSignal] entity killed: " + victim.GetType());` in OnEntityKilled before the boss check - should fire on any kill

---

## Session 3 - First modded server (60 min)

**Goal:** Feel what the scene is actually selling. Compare to vanilla.

- Join a top-50 server from Battlemetrics (filter: modded, high pop, Chernarus)
- Look at what mods they use - check the Steam Workshop load list
- Notice: the trader. The safe zones. The extra weapons. The missions.
- **Find a boss or mission event.** Watch how it plays.
- Note: what's clunky What works What would BossSignal add to this server

### The question to answer during this session
> "If the server operator had a live dashboard showing that 40 players are alive
> and no boss has spawned in 90 minutes - what would they DO with that information"

Write down your answer. It will inform the BossDirector spec (v0.3).

---

## After all three sessions

Mark each DEVLOG item as ok CONFIRMED or ✗ WRONG + fix applied.
Then open a fresh private commit and push the corrected code.

That's the end of Day 1.
