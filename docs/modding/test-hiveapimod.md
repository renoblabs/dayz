# Test Recipe: HiveApiMod

HiveApiMod is currently an integration scaffold. These checks validate backend reachability, server login, claim, and heartbeat paths; full restore, disconnect save, Bearer token reuse, and death/kill-event reporting are not wired yet.

## Pre-flight: Backend
1. Start the HiveAPI backend:
   ```cmd
   cd C:\Users\<user>\Dayz\dayz\backends\hiveapi
   make all
   ```
2. Verify health check:
   ```cmd
   curl http://127.0.0.1:6701/health
   ```
   Expect: `{"status":"healthy", ...}`. If running HiveAPI directly instead of through the local stack port map, use `http://127.0.0.1:8000/health`.

## Server Launch
1. Launch DayZ Server with HiveApiMod:
   ```cmd
   cd "C:\Program Files (x86)\Steam\steamapps\common\DayZServer"
   DayZServer_x64.exe -config=serverDZ.cfg -port=2302 -mod=@CommunityFramework;@HiveApiMod -profiles=profiles
   ```

## Expected RPT Log Lines
Check `profiles\DayZServer_x64.RPT`:
- `[HiveAPI] Mission server initialized`
- `[HiveAPI] Configuration loaded:`
- `[HiveAPI]   API URL: http://127.0.0.1:8000`
- `[HiveAPI] Authenticating server: 660e8400-e29b-41d4-a716-446655440001`
- `[HiveAPI] [OK] Server authenticated successfully` once the configured cluster/server IDs exist in the backend

## Failure Indicators
- `[HiveAPI] [FAIL]`
- `[HiveAPI] [ERROR]`
- `[HiveAPI] WARNING: ... not configured!`

## In-Game Validation (Validation step)
1. Join server.
2. Observe RPT for `[HiveAPI] Player connecting: Steam:<YourID>`.
3. Observe RPT for `[HiveAPI] [OK] Character claimed: <CharacterID>`.
4. Observe RPT for any heartbeat/claim logs. Disconnect save and inventory restore are planned paths, not current expected behavior.

## Backend Verification
```cmd
curl http://127.0.0.1:6701/v1/admin/eventslimit=5
```
Expect JSON containing recent `server_login` and `character_claimed` events if admin endpoints are enabled.
