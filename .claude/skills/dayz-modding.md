# DayZ Modding - Top 10 Known Issues

> This document tracks recurring issues with PBO conflicts and Enforce syntax quirks.
> Always consult this BEFORE diagnosing script errors.

---

## 1. PlayerBase.GetStamina() Removed in DayZ 1.29

**Error:** `Undefined function 'PlayerBase.GetStamina'`

**Cause:** The `GetStamina()` method was removed from `PlayerBase` in DayZ 1.29. Use `GetStaminaHandler()` instead or remove the call entirely.

**Fix:**
```c
// OLD (broken)
stats.Set("stamina", player.GetStamina());

// NEW (commented out or replaced)
// stats.Set("stamina", player.GetStamina());
// OR use GetStaminaHandler() if you need stamina data
```

---

## 2. Param2/Param3/Param4 Classes Incompatible in DayZ 1.29

**Error:** `Bad type 'Param2'` or `Can't find class Param2`

**Cause:** The `Param*` template classes have changed signatures in DayZ 1.29.

**Fix:**
```c
// OLD (broken)
timer.Run(interval, this, "Callback", new Param2<string, PlayerBase>(id, player), true);

// NEW (workaround)
// Pass data through instance variables instead, or use alternative callback pattern
```

---

## 3. PBO File Conflicts - Multiple Mods Override Same Class

**Error:** `Multiple mods override class 'X'`

**Cause:** Two or more mods contain `modded class X` definitions. Load order matters.

**Fix:**
1. Check mod load order in `-mod=` parameter
2. Ensure dependent mods load AFTER their dependencies
3. Use `depends_on` in mods.yaml to enforce order

---

## 4. $mission: vs $mpmissions: Path Aliases

**Error:** `Failed to load $mpmissions:...` when file exists

**Cause:** `$mpmissions:` does NOT include the mission name. Use `$mission:` instead.

**Fix:**
```c
// WRONG
static string PATH = "$mpmissions:TrophyHunter/bosses.json";

// CORRECT
static string PATH = "$mission:TrophyHunter/bosses.json";
```

---

## 5. RestContext POST Blocks During MissionServer.OnInit()

**Error:** Server hangs during world loading (ponds/entities never finish)

**Cause:** HTTP calls in `OnInit()` block the main thread during map load.

**Fix:**
```c
override void OnInit()
{
    super.OnInit();
    // Defer HTTP calls until AFTER mission load
    GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(DoHttpCall, 10000, false);
}
```

---

## 6. FileBank Caches Old PBO Content

**Error:** Rebuilt PBO still contains old code after edit

**Cause:** FileBank may not overwrite existing PBO files, or server has PBO locked.

**Fix:**
1. Stop the DayZ server
2. Delete the output PBO file
3. Rebuild the mod
4. Restart server

---

## 7. JsonFileLoader Template Syntax

**Error:** JSON file fails to load despite correct format

**Cause:** Enforce template syntax for `JsonFileLoader` is finicky.

**Fix:**
```c
ref MyClass data = new MyClass();
string errMsg;
if (!JsonFileLoader<ref MyClass>.LoadFile(path, data, errMsg)) {
    Print("JSON load failed: " + errMsg);
}
```

---

## 8. DayZ Version Mismatch - Unknown Function

**Error:** `Undefined function 'X'` for standard DayZ functions

**Cause:** Function was added/removed in a specific DayZ version.

**Fix:**
1. Check DayZ server version (currently 1.29)
2. Consult Bohemia DayZ wiki for API changes
3. Use conditional compilation or version checks if supporting multiple versions

---

## 9. EntityAI.GetItemInHands() Return Type Varies

**Error:** Type casting issues with `GetItemInHands()`

**Cause:** Return type changed between DayZ versions.

**Fix:**
```c
// Safe casting pattern
EntityAI inHands = EntityAI.Cast(player.GetItemInHands());
if (inHands) {
    string type = inHands.GetType();
}
```

---

## 10. Map Iteration - GetKey()/GetElement() vs Foreach

**Error:** Map iteration produces unexpected results or crashes

**Cause:** Enforce map iteration patterns differ from other languages.

**Fix:**
```c
// Index-based iteration
for (int i = 0; i < myMap.Count(); i++) {
    string key = myMap.GetKey(i);
    int value = myMap.GetElement(i);
}

// Foreach pattern (for arrays only, not maps)
foreach (string key, int value : myMap) {  // May not work on all versions
    // ...
}
```

---

## Placeholders for Future Issues

### Issue #11
*Add your encountered errors here*

**Error:** `[PLACEHOLDER]`

**Cause:** `[PLACEHOLDER]`

**Fix:** `[PLACEHOLDER]`

---

### Issue #12
*Add your encountered errors here*

**Error:** `[PLACEHOLDER]`

**Cause:** `[PLACEHOLDER]`

**Fix:** `[PLACEHOLDER]`

---

## Quick Reference: Log Error Patterns

| Pattern | Likely Cause |
|---------|--------------|
| `Undefined function` | Function removed/renamed in DayZ version |
| `Can't find class` | Missing class or wrong namespace |
| `Bad type` | Type compatibility (often Param classes) |
| `No need to use 'Cast'` | Warning only, non-blocking |
| `Failed to load $...` | Path alias issue |
| `Script module failed` | Compilation error, check script_*.log |
| `ENTITY (W): Unknown object class 'pond'` | Normal warning, non-blocking |

