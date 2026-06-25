# Test Recipe: TrophyHunter Mod

TrophyHunter depends on BossSignal encounter data and configured boss-class mappings. Use attributed external boss classes or explicit test placeholders, and verify BossSignal has a top-damager record before expecting a trophy award.

## Pre-flight: Backend
1. Start the BossSignal backend (it handles trophies too):
   ```cmd
   cd C:\Users\<user>\Dayz\dayz\backends\bosssignal-backend
   docker compose up -d
   ```

## Server Launch
1. Launch DayZ Server with TrophyHunter (and dependencies):
   ```cmd
   cd "C:\Program Files (x86)\Steam\steamapps\common\DayZServer"
   DayZServer_x64.exe -config=serverDZ.cfg -port=2302 -mod=@CommunityFramework;@BossSignal;@TrophyHunter -profiles=profiles
   ```

## Expected RPT Log Lines
Check `profiles\DayZServer_x64.RPT`:
- `[TrophyHunter] Ready. Watching <N> boss classes.`

## Failure Indicators
- `[TrophyHunter][ERROR]`
- `[TrophyHunter] REST client not ready - trophies disabled.`
- `[TrophyHunter] Failed to load .../bosses.json`
- `Bad type`
- `Broken expression`

## In-Game Validation (Validation step)
1. Join server.
2. Spawn a boss class listed in the current TrophyHunter boss mapping.
3. Kill the boss.
4. Check your inventory for the trophy item.
5. Check dashboard at http://localhost:6700/ to see the trophy award.

## Backend Verification
```cmd
curl http://127.0.0.1:6700/api/v1/trophies
```
Expect JSON containing the trophies list, including the one just awarded.
