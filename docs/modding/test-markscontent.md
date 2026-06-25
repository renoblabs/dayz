# Test Recipe: MarksContent Mod

## Server Launch
1. From the repo root, build + deploy MarksContent through the standard modctl pipeline:
   ```powershell
   Push-Location tools-extra/modctl
   python -m modctl -c mods.yaml ship markscontent
   Pop-Location
   ```
2. Launch the local server through the recovery launcher:
   ```powershell
   .\launch_with_recovery.ps1 -Mods bosssignal,markscontent
   ```

## Client Setup
No separate setup script is required. `modctl ship markscontent` deploys the signed PBO to the DayZ Server install and refreshes the local DayZ client launcher entry at `!Workshop\@MarksContent`.

After shipping the mod, restart DayZ Launcher, enable `MarksContent`, and join the local test server launched by `launch_with_recovery.ps1`.

## Expected RPT Log Lines
Check `profiles\DayZServer_x64.RPT`:
- Look for `MarksContent` in the list of loaded mods.
- No `[ERROR]` or `Can't load ...` related to this mod.

## In-Game Validation (Validation step)
1. Join server.
2. Use admin tools (like VPPAdminTools) to spawn:
   - `ZmbM_MarksTester` (Zombie)
   - `Mark_BetaTester_Shirt` (T-Shirt)
   - `Mark_DebugRifle` (Weapon)
3. Verify they appear correctly and have the expected names/descriptions.
