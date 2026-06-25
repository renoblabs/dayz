# DayZ modding patterns library

Reference for DayZ 1.29 + Community Framework modding gotchas, distilled from real debugging sessions. The principle: **every gotcha solved once goes here so it's never solved twice.**

This doc pairs with:
- `tools/modctl/modctl/rules/enforce.yaml` - rule-based diagnose patterns
- `memory/project_agent_self_improvement.md` - the RL/rule-promotion loop strategy

Add to this file any time you burn time on a DayZ modding issue that future-you shouldn't have to rediscover.

---

## Toolchain

### Build a PBO (script-only mod, no P: drive)

Use `FileBank.exe` + `DSSignFile.exe`, **not** AddonBuilder.exe (AddonBuilder requires P: drive mount via WorkDrive and hangs silently without one).

```bash
# Pack (absolute paths required - relative paths silently fail with exit 0)
FileBank.exe -property prefix=MyMod -dst <abs_output_dir> <abs_source_dir>
# Produces: <output_dir>/<source_basename>.pbo  (rename to <prefix>.pbo if different)

# Sign
DSSignFile.exe <abs_private_key> <abs_pbo_path>
# Produces: <pbo_path>.<keyname>.bisign next to the PBO
```

Exit codes: FileBank 0 = success. DSSignFile 0 = success, 1 = silent fail (usually wrong key file - see next section).

### Generate signing keys correctly

`DSCreateKey.exe` must be invoked from INSIDE the destination directory, with just the bare mod name as arg. Passing a path prefix (e.g. `keys\MyMod`) makes DSCreateKey write the path STRING into the .biprivatekey file as content. DSSignFile then silently fails with exit 1.

```bash
cd build-pipeline/keys
"C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\DsUtils\DSCreateKey.exe" MyMod
# Correct output: MyMod.biprivatekey (binary RSA key, ~611 bytes starting with "MyMod\0T\2\0\0\7\2\0\0\0...")
# Wrong output:   MyMod.biprivatekey (text containing the path you passed)
```

### Unpack a working mod to read its source

```bash
# BankRev outputs to a folder next to the .pbo (same name without .pbo)
"C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\PboUtils\BankRev.exe" <path_to.pbo>
```

Useful for reading how CF / Expansion / working mods handle specific patterns.

### Workshop mod -> local server

Symlink (Windows junction), don't copy. Stays in sync if the Workshop mod auto-updates.

```cmd
mklink /J "<DayZServer>\@ModName" "<steamapps>\workshop\content\221100\<WORKSHOP_ID>"
```

Then copy the mod's `.bikey` (from `<steamapps>\workshop\content\221100\<id>\keys\`) to `<DayZServer>\keys\`.

---

## Enforce compiler gotchas (DayZ 1.29)

### 1. ASCII-only source files

Enforce 1.29 drifts on multi-byte UTF-8 chars even inside comments. The line counter in error messages goes wrong, and you get reports of syntax errors on wrong lines. Common offenders:

| Char | Replace with |
|---|---|
| em-dash - | `-` |
| en-dash - | `-` |
| smart quotes `'` `'` `"` `"` | plain `'` `"` |
| section sign § | `sec` |
| ellipsis ... | `...` |
| arrow -> | `->` |
| checkmark ok | `OK` |
| bullet • | `*` |
| box-drawing - ═ etc | `-` or `=` |

Run `grep -rP '[^\x00-\x7F]' ./**/*.c` to find non-ASCII. Fix before first compile.

### 2. Single-line string concatenation only

Multi-line `+` concat across newlines is **rejected**:

```c
// FAILS in 1.29
Print("foo" + VAR
    + "bar");

// OK
Print("foo" + VAR + "bar");
```

If the concat is too long, split into smaller statements building up a local string variable.

### 3. "Formula too complex" - split big concats

Enforce has a parser complexity limit. For JSON-event-body style code:

```c
// FAILS: "Formula too complex"
string body = "{\"a\":\"" + a + "\",\"b\":\"" + b + "\",\"c\":\"" + c + "\",\"d\":\"" + d + "\",\"e\":\"" + e + "\"}";

// OK: build incrementally
string body = "{";
body = body + "\"a\":\"" + a + "\",";
body = body + "\"b\":\"" + b + "\",";
// etc.
body = body + "}";
```

### 4. `ref` on singleton/system objects fails with "private destructor"

`RestContext` (and similar DayZ-owned objects) have private destructors. You cannot hold a `ref` to them - ref count must reach 0, which triggers the destructor, which is private.

```c
// FAILS
protected ref RestContext m_Ctx;

// OK
protected RestContext m_Ctx;  // non-owning pointer
```

### 5. `out` is a reserved keyword

Can't use `out` as a variable name. Rename to `output`, `result`, `o`, etc.

### 6. RestCallback signature (DayZ 1.29)

```c
class MyCallback : RestCallback {
    override void OnSuccess(string data, int dataSize) { /* ... */ }
    override void OnError(int errorCode) { /* ... */ }
    override void OnTimeout() { /* ... */ }
}
```

NOT `OnSuccess(string response, int errorCode)` - that's a stale signature.

### 7. Ternary ` :` rejected in some modded-class contexts

If you see `Broken expression (missing ';')` on a line with `cond  a : b`, replace with if/else:

```c
// FAILS
string status = passed  "PASS" : "FAIL";

// OK
string status;
if (passed) status = "PASS";
else        status = "FAIL";
```

### 8. `MissionServer.OnEntityKilled` - NOT an override target in 1.29

The base `MissionServer.OnEntityKilled(EntityAI, EntityAI, Man)` is NOT exposed as overridable in DayZ 1.29. Use CF's event system instead, or hook `OnEvent(EventType, Param)` with the appropriate EventType.

### 9. JsonFileLoader<T> - verify type parameter syntax

The generic form `JsonFileLoader<MyType>.JsonLoadFile(path, myObject)` has version-specific quirks. If you see "Bad type 'JsonFileLoader'", check whether your DayZ version requires `ref MyType` instead of `MyType` in the type parameter, or whether the class name changed (e.g. `JsonSerializer`).

### 10. Missing `CfgMods.defs.*ScriptModule` = orphaned scripts

CfgPatches enables a mod; **CfgMods > defs > (game|world|mission)ScriptModule.files** is what mounts the PBO's `.c` files into the engine's script modules. Without it:

- PBO loads (mod appears in `-mod=` list and script log `defines`)
- Scripts inside the PBO never get compiled into Game/World/Mission
- Modded classes silently aren't chained - `modded class MissionServer { override void OnInit() }` never fires
- No compile error, no warning - just nothing happens

Required for any script mod:

```cpp
class CfgMods {
    class MyMod {
        dir          = "MyMod";
        type         = "mod";
        dependencies[] = {"Game", "World", "Mission"};
        class defs {
            class gameScriptModule    { files[] = {"MyMod/scripts/3_game"}; };
            class worldScriptModule   { files[] = {"MyMod/scripts/4_world"}; };
            class missionScriptModule { files[] = {"MyMod/scripts/5_mission"}; };
        };
    };
};
```

Symptom that uniquely fingerprints this: mod appears in `-mod=`, script log shows `defines: ...,MyMod,...`, but zero `Print()` output from your code reaches the RPT. If OnInit Prints are missing, check config.cpp defs BEFORE debugging the script.

### 11. Animation XML missing warnings are harmless

```
ANIMATION (E): Can't load @MyMod/Anims/cfg/skeletons.anim.xml
```

Pure script mods (no character/animation data) always log this. Ignore unless you're actually doing animation work.

---

## Mission class hierarchy (DayZ 1.29 + CF)

```
Mission (engine base)
  └- MissionBase (modded by CF - lifecycle events)
      └- MissionServer (modded by CF - server-side hooks)
          └- CustomMission (in mpmissions/dayzOffline.chernarusplus/init.c)
```

`modded class MissionServer { override void OnInit() { ... } }` IS the right pattern - CF uses it. Your OnInit fires via inheritance chain from CustomMission.OnInit -> (inherits MissionServer) -> your modded OnInit.

**Common hooks you can override on MissionServer:**
- `void MissionServer()` - constructor
- `override void OnInit()`
- `override void OnMissionStart()`
- `override void OnMissionLoaded()`
- `override void OnMissionFinish()`
- `override void OnUpdate(float timeslice)`
- `override void OnEvent(EventType eventTypeId, Param params)`

Call `super.Method()` first in every override unless you have a specific reason not to.

---

## Load order

Scripts in a mod load in dir order: `1_core/`, `2_gamelib/`, `3_game/`, `4_world/`, `5_mission/`.

Cross-mod order is determined by `-mod=@A;@B;@C` on the DayZ Server command line, left to right. `@CommunityFramework` should always be first since most mods depend on CF. Our own mods come after.

When mod A depends on mod B's classes, ensure B comes before A in the `-mod=` list AND that B's class is in an earlier subfolder (e.g. B's class in `3_game/` is visible to A's code in `5_mission/`).

---

## Mission initialization timing

Cold-boot of Chernarus mission loads a LOT of entities first (1000s of buildings, vehicles, POIs). **Mission OnInit only fires AFTER world entities finish loading** - this can take 1-3 minutes on first boot.

Wait for `Mission is starting` or `DayZ server is initialised` lines in the RPT before assuming your OnInit should have fired.

---

## RPT buffering - taskkill does NOT flush

DayZ Server buffers RPT writes in memory. A `taskkill /F` (force-kill) loses everything since the last flush. `Print()` output that LOOKED like it should appear won't, even if the code ran.

To validate Prints in RPT, you need **graceful shutdown**:
- Close the console window via its X button (triggers WM_CLOSE -> clean shutdown)
- Use RCON `#shutdown` command if configured
- Send Ctrl+C to the console process

**Rule:** Never force-kill a DayZ server during validation. If your Prints aren't appearing, try a clean shutdown before concluding your code isn't running.

The script log (`script_*.log`) also lags. Entity warnings / `[CE]` / `[Storage]` lines flush more eagerly than user `Print()` calls.

## Log file locations

```
<DayZServer>/profiles/
|-- DayZServer_x64_<date>_<time>.RPT     # main runtime log (entity loads, warnings)
|-- script_<date>_<time>.log              # script compilation messages
|-- crash_<date>_<time>.log               # fatal errors
`-- DataCache/                             # world geometry cache
```

Search order when debugging: crash log first (fatal reason), then script log (compile errors), then RPT (runtime).

Crash log is CREATED even if server subsequently starts cleanly - check the timestamp before assuming the server crashed.

---

## Quick diagnosis cheat sheet

| Symptom | Likely cause | Fix |
|---|---|---|
| `Can't compile X script module` | Enforce compile error | Check script log, find line, apply gotcha #1-9 |
| PBO builds but not loaded | .bikey missing from server keys/ folder | Copy `<mod>.bikey` to `<DayZServer>/keys/` |
| `modctl build` exits 0 but no PBO | Relative paths used with AddonBuilder/FileBank | Use absolute paths |
| DSSignFile silent exit 1 | Wrong key format (path written instead of RSA key) | Regenerate key from inside keys dir |
| `NULL pointer to instance` | Unchecked deref | Null-guard before .Method() call |
| `Expected ',' or ')', not a 'SERVER_ID'` | Multi-line concat OR non-ASCII earlier | See gotchas #1, #2 |
| Mission compiles but OnInit doesn't fire | Still loading world - wait longer | Can take 1-3 min on cold boot |
