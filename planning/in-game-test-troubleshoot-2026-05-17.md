# In-Game Test Troubleshoot - 2026-05-17

**This doc is the model for every future troubleshoot doc: comprehensive, log-sourced, lessons-extracted. No "what I saw on screen" - every claim cites a log on disk.**

## Symptom

DayZ client fails to join local Server A (`127.0.0.1:2302`, `server_01`). Two attempts (21:35, 21:55), both kicked at mod-load before reaching gameplay. Boss-kill end-to-end test blocked.

## Investigation - sources read (all on disk, none transcribed)

| Source | Path | Result |
|---|---|---|
| Client RPT | `%LOCALAPPDATA%\DayZ\DayZ_x64_2026-05-17_21-35-08.RPT` | **Primary evidence** - see below |
| Server A RPT | `...\DayZServer\profiles\DayZServer_x64_2026-05-17_19-33-57.RPT` | Zero kick/reject/signature lines -> rejection never reached server |
| BattlEye | `...\DayZServer\profiles\BattlEye\` and `...\DayZServer\battleye\` | No `*.log` files -> BE never engaged -> rejection is pre-BattlEye |
| Launcher preset | `%LOCALAPPDATA%\DayZ Launcher\Presets\dayz.defaultpreset2` | **Root cause** - see below |
| Client mod trees | `...\DayZ\!Workshop\@*` + `meta.cpp` publishedids | Used to derive the correct fix |
| Server modlist | `...\DayZServer\launch_modded.bat` | Authoritative: `@CommunityFramework;@VPPAdminTools;@BossContentMod;@BossSignal;@HiveApiMod;@TrophyHunter;@MarksContent` |

## Exact error (client RPT, lines 251-266, repeated at 304-306)

```
Function: 'LoadMods'
nst/namalsk/scripts/5_Mission/namalskterrain\gui\mainmenu.c:5  Function LoadMods
21:35:48.298 [ErrorModuleHandler] :: Error thrown: 0x00040074 (BossContentMod; @TrophyHunter; @HiveApiMod; @BossSignal)
(C:\Program Files (x86)\Steam\steamapps\common\DayZ\!Workshop\@BossContentMod\addons\BossContentMod.pbo))
```

`0x00040074` = `VE_UNEXPECTED_MOD_PBO`. The `BossContentMod.pbo` in the parenthetical is a **boundary marker, not the culprit** - the `nst/namalsk/...mainmenu.c` reference proves Namalsk is loaded client-side. Server runs no Namalsk.

## Root cause - compound failure (two distinct causes stacked)

The active launcher preset `dayz.defaultpreset2` had **12 mods**, wrong on two axes:

**Cause 1 - path separation (client mods under the server tree):**
```
local:C:\PROGRAM FILES (X86)\STEAM\STEAMAPPS\COMMON\DAYZSERVER\@BOSSSIGNAL\
local:C:\PROGRAM FILES (X86)\STEAM\STEAMAPPS\COMMON\DAYZSERVER\@TROPHYHUNTER\
```
`@BossSignal` and `@TrophyHunter` resolved into the **server's** `DAYZSERVER\` install tree. DayZ's modlist handshake registers the mount path as part of module identity; client mounting from the server's tree ≠ server's own mount -> kick even with byte-identical PBOs.

**Cause 2 - modset composition (extra mods the server doesn't run):**
Preset also carried `steam:3702684028` (MMG Base Storage), `1646187754` (Code Lock), `3429753035` (NMP), `1623711988` (VanillaPlusPlusMap), `3679809459` (LibBSH), `2289461232` (Namalsk Survival), `2289456201` (Namalsk Island) - none on the server. Also **`@BossContentMod` (steam:YOUR_BOSS_MOD_ID) was missing entirely** from the preset, though the server runs it.

Server RPT silent + no BattlEye log corroborate a **client-side, pre-BattlEye modset rejection** - exactly the `VE_UNEXPECTED_MOD_PBO` signature.

## The three bugs (each with the log line that revealed it)

Grep targets for "next time something like this happens" are in **bold**.

**Bug 1 - client mods mounted under the server tree (path separation).**
Revealed by `%LOCALAPPDATA%\DayZ Launcher\Presets\dayz.defaultpreset2`:
```
local:C:\PROGRAM FILES (X86)\STEAM\STEAMAPPS\COMMON\DAYZSERVER\@BOSSSIGNAL\
local:C:\PROGRAM FILES (X86)\STEAM\STEAMAPPS\COMMON\DAYZSERVER\@TROPHYHUNTER\
```
**Grep:** `grep -i 'DAYZSERVER' "$LOCALAPPDATA\DayZ Launcher\Presets\*.preset*"` - any client preset entry containing `DAYZSERVER\` is this bug.

**Bug 2 - extra mods + Namalsk the server doesn't run (composition).**
Revealed by the client RPT, an *unrelated* string proving Namalsk was loaded:
```
%LOCALAPPDATA%\DayZ\DayZ_x64_2026-05-17_21-35-08.RPT : line 253
nst/namalsk/scripts/5_Mission/namalskterrain\gui\mainmenu.c:5  Function LoadMods
21:35:48.298 [ErrorModuleHandler] :: Error thrown: 0x00040074 ...
```
**Grep:** `grep -nE '0x00040074|LoadMods|nst/namalsk' <newest client RPT>` - a non-server mod's source path next to a `0x000` throw = composition bug.

**Bug 3 - BossContentMod missing from the client preset entirely.**
The 12-entry preset had no `steam:YOUR_BOSS_MOD_ID`, yet `launch_modded.bat` requires `@BossContentMod`. The error parenthetical even named `@BossContentMod\addons\BossContentMod.pbo` as the boundary.
**Grep:** diff the preset's ids against `grep -oE '@\w+' launch_modded.bat` - any server mod with no matching preset id is this bug.

## Corrected preset XML (drafted, NOT applied - kept for reference)

```xml
<xml version="1.0" encoding="utf-8">
<addons-presets>
  <published-ids>
    <id>steam:1559212036</id>   <!-- @CommunityFramework -->
    <id>steam:1828439124</id>   <!-- @VPPAdminTools -->
    <id>steam:YOUR_BOSS_MOD_ID</id>   <!-- @BossContentMod (was missing) -->
    <id>local:C:\PROGRAM FILES (X86)\STEAM\STEAMAPPS\COMMON\DAYZ\!WORKSHOP\@BOSSSIGNAL\</id>
    <id>local:C:\PROGRAM FILES (X86)\STEAM\STEAMAPPS\COMMON\DAYZ\!WORKSHOP\@HIVEAPIMOD\</id>
    <id>local:C:\PROGRAM FILES (X86)\STEAM\STEAMAPPS\COMMON\DAYZ\!WORKSHOP\@TROPHYHUNTER\</id>
    <id>local:C:\PROGRAM FILES (X86)\STEAM\STEAMAPPS\COMMON\DAYZ\!WORKSHOP\@MARKSCONTENT\</id>
  </published-ids>
</addons-presets>
```
Verified launcher identities from `!Workshop\@*\meta.cpp` publishedids. Original preset backed up to `dayz.defaultpreset2.bak-2026-05-17` (backup made; **preset was NOT overwritten**).

## Resolution decision - SETUP DLCS AND MODS AND JOIN (not the preset rewrite)

Chose the launcher's built-in **SETUP DLCS AND MODS AND JOIN** over hand-writing the preset. Rationale: (a) safer - DayZ matches the modset against the live server, no hand-edited XML; (b) verifiable - if it still fails it's provably server-side, not a client preset error; (c) reproducible - this is the exact path an end user will use, so testing it now validates that path too.

## Server-side checks (all clean - no server fix needed)

| Check | Result |
|---|---|
| Server in launcher browser | [done] In **Favourites** as `Server-A-Test`, `ConnectionEndPoint=192.168.56.1:2302` (server binds 0.0.0.0 - reachable). Server B not favourited (only A needed). |
| `keys/` .bikey files | Present: BossSignal, HiveApiMod, MarksContent, TrophyHunter, VPP(=VPPAdminTools), soulfly(=BossContentMod), Jacob_Mango_V3(=CF), dayz. |
| `-mod=` chain (`launch_modded.bat`) | [done] `@CommunityFramework;@VPPAdminTools;@BossContentMod;@BossSignal;@HiveApiMod;@TrophyHunter;@MarksContent` - BossContentMod present, pos 3. |
| **`verifySignatures` (`serverDZ.cfg`)** | **`= 0`** - server does NOT verify signatures. Permanently rules out every key/signature theory for `0x00040074`; keys are not a gate for SETUP DLCS. |

The 4 non-test Favourites are external *Namalsk/Vanilla++* community servers - the origin of the Namalsk/VanillaPlusPlus/extra Workshop subscriptions that polluted the preset (Bug 2). Expected, not a defect.

## Bug 4 - VPP menu unresponsive for a confirmed Super Admin (client-side, NOT auth)

**Symptom:** Connected to modded server_01 fine (RPT `Player "Survivor" (steamID=<your-steam64-id>) is connected`; backend `player_count=1`), but no VPP key (Insert/F1/Home/Shift+Insert/F4) or chat command (`/vpp` `#vpp`) opens the admin menu.

**False hypothesis (disproven):** "Steam ID not in VPP SuperAdmins / bad formatting."

**Verification chain (all server-side, all green - DO NOT 'fix' these):**
- File: `profiles/VPPAdminTools/Permissions/SuperAdmins/SuperAdmins.txt`
- `cat -A` -> `<your-steam64-id>$` - ID present, clean LF, no CRLF/BOM/whitespace/quotes. Correct format (a Steam64 ID is 17 digits / 18 bytes with the trailing newline).
- VPP boot log `profiles/VPPAdminTools/Logging/Log_2026-5-17_23-34-20.txt:81` -> `[PermissionManager] Adding Super Admin (<your-steam64-id>)` (confirmed in both boot logs).
- Same log line 104 -> `Player "Survivor" (steamId=<your-steam64-id>) connected to server!`
- **Grep for next time:** `grep -rn 'Adding Super Admin' profiles/VPPAdminTools/Logging/` and `cat -A profiles/VPPAdminTools/Permissions/SuperAdmins/SuperAdmins.txt`. If the "Adding Super Admin" line is present, the auth chain is fine - stop looking server-side.

**Actual root cause:** VPP Admin Tools ships with **no default menu keybind**. The open-menu action must be bound manually client-side in DayZ **Options -> Controls**. Server auth perfect + menu won't open ⇒ unbound key, not authorization.

**Fix applied:** None server-side (correctly - nothing was broken). No file edited, no backup needed, no activation/restart. Resolution is **client-side only**: bind the VPP menu key in DayZ Options -> Controls (no server bounce - the  connection is preserved).

**Lesson:** A "VPP won't open" report for a connected player is auth ~10% of the time; verify the SuperAdmins file *and* the `Adding Super Admin` log line first (2 commands), and if both are green, it's the unbound client keybind - don't edit permission files, don't restart the server.

## Lessons extracted

1. **`0x00040074` is a family, not a bug.** Discriminate by (a) which path the error shows and (b) `md5sum` client vs server PBO. See memory `feedback_dayz_client_mod_path_separation`. This incident was causes **1 AND 2 simultaneously** - fixing only one would still kick.
2. **The PBO named in the error is usually a red herring** (boundary marker). The real tell here was an unrelated string (`nst/namalsk/...`) proving an extra mod was loaded.
3. **Server RPT silent + no BattlEye log = client-side pre-BE rejection.** Don't wait for server-side evidence that will never come.
4. **The launcher preset on disk (`dayz.defaultpreset2`) is the truth**, not the checkboxes from memory. Read it; don't ask the human to describe the mod list.
5. **Logs > screenshots, always.** Every fact here came from disk. Future troubleshoot docs follow this exact structure: Symptom -> Sources table -> Exact error quote -> Root cause -> Fix -> Lessons.
6. **Check `verifySignatures` in `serverDZ.cfg` FIRST.** If it's `0`, every key/signature/.bikey theory is dead on arrival - don't spend a single step there. This setup is `0`; signatures were never the issue and never could have been.
7. **Multiple bugs can wear one error code.** `0x00040074` here was *three* independent defects (path separation + composition + a missing required mod) behind one kick. Don't stop at the first cause found - enumerate against the authoritative server modlist.
8. **Prefer the reproducible user-facing path over a clever fix.** Hand-writing the preset would have worked once; SETUP DLCS AND MODS AND JOIN is what an end user will actually use, so validating it now tests the real path. A fix only the developer can apply isn't a fix for end users.
