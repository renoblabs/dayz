# Test Recipe: BossSignal Mod

BossSignal is telemetry-only. It records events for registered boss classes; it does not ship third-party boss content or spawn/despawn bosses by itself.

## Pre-flight: Backend
1. Start the BossSignal backend:
   ```cmd
   cd C:\Users\<user>\Dayz\dayz\backends\bosssignal-backend
   docker compose up -d
   ```
2. Verify health check:
   ```cmd
   curl http://127.0.0.1:6700/health
   ```
   Expect: `{"status":"ok"}` (or similar JSON)

## Server Launch
1. Launch DayZ Server with BossSignal:
   ```cmd
   cd "C:\Program Files (x86)\Steam\steamapps\common\DayZServer"
   DayZServer_x64.exe -config=serverDZ.cfg -port=2302 -mod=@CommunityFramework;@BossSignal -profiles=profiles
   ```

## Expected RPT Log Lines
Check `profiles\DayZServer_x64.RPT`:
- `[BossSignal] MissionServer constructor fired`
- `[BossSignal] OnInit enter`
- `[BossSignal] BossSignal v0.1.0 active on server_01`
- `[BossSignal] OnMissionStart fired`
- `[BossSignal] OnMissionLoaded fired`

## Failure Indicators
- `[BossSignal][ERROR]`
- `Bad type`
- `Broken expression`
- `Formula too complex`

## In-Game Validation (Validation step)
1. Join server.
2. Spawn a registered boss class from a properly attributed content mod, or use the synthetic event path for a smoke test.
3. Kill the boss.
4. Check dashboard at http://localhost:6700/ (or the configured dashboard URL) to see the encounter.

## Backend Verification
```cmd
curl http://127.0.0.1:6700/api/v1/bosses
```
Expect JSON containing the recent encounter.
