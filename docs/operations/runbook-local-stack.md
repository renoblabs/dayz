# Runbook - Local DayZ Dev Stack

The cold-start playbook for the full local dev environment: BossSignal backend +
dashboard, both DayZ servers, and the in-game test loop. If any step here
surprises you, the runbook is wrong - fix the runbook, don't memorize the
exception.

## Layout

| Component | Where it lives | URL / Port |
|-----------|----------------|------------|
| BossSignal backend (FastAPI + Postgres, Docker compose) | `backends/bosssignal-backend/` | `http://localhost:6700` |
| Ops dashboard (React, served by backend container) | `frontends/web-ui/` (build output mounted into backend) | `http://localhost:6700/ops` |
| DayZ Server A (`Server-A`) | `C:\Program Files (x86)\Steam\steamapps\common\DayZServer\launch_modded.bat` | UDP `2302` |
| DayZ Server B (`Server-B`) | same install, `launch_modded_B.bat` | UDP `2402` |
| modctl CLI (build/sign/ship mods) | `tools-extra/modctl/` | n/a |

## Mod taxonomy (read first)

Two of the loaded mods sound similar but are **not the same thing** - running the
wrong build of either is the most common cause of confusing kicks and "nothing's
happening" demos.

| Mod | Source | What it is |
|-----|--------|------------|
| `@BossSignal` | **Repo** (`mods/BossSignal/`, built by modctl) | Telemetry-only mod. Registers boss classes from other mods, emits startup/heartbeat and kill events, and supports API-driven spawn/despawn/custom events. Has zero gameplay content of its own. |
| `@BossContentMod` | **Steam Workshop** (publishedid `YOUR_BOSS_MOD_ID`) | Third-party boss-content mod used by this demo stack. Provides actual boss zombie classes. Not part of this repo. |
| `@HiveApiMod` | **Repo** (`mods/HiveApiMod/`) | DayZ-side client/lib that talks to the HiveAPI backend (`ops-api`, port 6701). |
| `@TrophyHunter` | **Repo** (`mods/TrophyHunter/`) | Boss-kill -> trophy-drop loop. Uses `mods/TrophyHunter/config/bosses.json` as the registry. |
| `@MarksContent` | **Repo** (`mods/MarksContent/`) | custom content. Includes `ZmbM_MarksTester` (the dev test zombie used in the smoke test below). |
| `@CommunityFramework`, `@VPPAdminTools` | Workshop | Third-party dependencies. CF must load **first**. VPPAdminTools is for dev/test spawning. |

If you're chasing "client has a PBO not part of the server" or "data verification
error" - almost always one of these is built from a different source than the
server expects. See **Known Gotchas -> Data verification kick**.

### Server modlist - truth source

The exact modlists are defined by the server's launch batch files. **These are
authoritative**, not this runbook:

- A: `C:\Program Files (x86)\Steam\steamapps\common\DayZServer\launch_modded.bat`
- B: `C:\Program Files (x86)\Steam\steamapps\common\DayZServer\launch_modded_B.bat`
- light (subset, single server): `launch_light.bat`

Current full set, in order: `@CommunityFramework;@VPPAdminTools;@BossContentMod;@BossSignal;@HiveApiMod;@TrophyHunter;@MarksContent`

## Cold-start sequence

Run from the repo root.

### 1. Start the backend + dashboard

```powershell
cd backends/bosssignal-backend
docker compose up -d
```

Confirm:

```powershell
curl.exe --max-time 5 -s http://localhost:6700/health
```

Expect `{"status":"ok","version":"0.1.0"}`.

### 2. (If you changed mod source) ship mods

If any of `mods/*` changed since the last run, rebuild + sign + deploy + sync to
the client `!Workshop` folder in one shot. Servers must be **stopped** first -
running servers hold PBO file locks and `modctl ship` will fail with a
`PermissionError`.

```powershell
Get-Process DayZServer_x64 -ErrorAction SilentlyContinue | Stop-Process -Force

cd tools-extra/modctl
# Refuse to ship with an unset secret - export BOSSSIGNAL_SECRET first (do NOT hardcode it).
if (-not $env:BOSSSIGNAL_SECRET) { throw "BOSSSIGNAL_SECRET is not set. Export it before shipping mods." }
foreach ($m in @("bosssignal","hiveapi","trophyhunter","markscontent")) {
  python -m modctl -c mods.yaml ship $m
}
```

Skip this step if no mod source changed - re-shipping is harmless but adds ~10s
and forces a server restart.

### 3. Launch both DayZ servers

```powershell
Start-Process "C:\Program Files (x86)\Steam\steamapps\common\DayZServer\launch_modded.bat"
Start-Sleep -Seconds 4
Start-Process "C:\Program Files (x86)\Steam\steamapps\common\DayZServer\launch_modded_B.bat"
```

Wait ~30s for them to finish loading, then verify:

```powershell
Get-Process DayZServer_x64 | Select-Object Id, StartTime
curl.exe --max-time 5 -s http://localhost:6700/api/v1/servers
```

Both `server_01` and `server_02` should appear with `is_online: true` and a
recent `last_seen`. Heartbeats are the real signal - process presence alone
doesn't prove the mods loaded cleanly.

### 4. Connect from the DayZ client

DayZ Launcher's LAN tab is flaky with multiple local servers - see Known Gotchas.
Two reliable paths:

**Easiest (avoids modset drift):** in DayZ Launcher, find your server entry
(Favorites or Recent) -> **"SETUP DLCS AND MODS AND JOIN"**. The launcher applies
the server's exact modlist and order, so you can't forget a mod or load a stray
Workshop mod that breaks parity.

**Direct Connect:** if you've already pinned the right modset:

- Server A: `127.0.0.1:2302`
- Server B: `127.0.0.1:2402`

After joining once, right-click each in **Recent** -> **Add to Favorites**.

Required mods, in this order (CF must be first):

1. `@CommunityFramework`
2. `@VPPAdminTools`
3. `@BossContentMod`
4. `@BossSignal`
5. `@HiveApiMod`
6. `@TrophyHunter`
7. `@MarksContent`

Don't enable random extra Workshop mods (Namalsk maps, etc.) for the dev
preset - the server doesn't run them, you'll get kicked.

## In-game smoke test

1. Join Server A.
2. Press `Insert` for VPP Admin Tools -> Object Spawner.
3. Spawn `ZmbM_MarksTester` (from `@MarksContent` - the dev-test zombie).
4. Kill it. Fists work.
5. Watch `http://localhost:6700/ops` - the kill event should appear in the feed
   within a few seconds.
6. Log out, Direct Connect to Server B (`127.0.0.1:2402`), repeat. Confirms the
   cross-server flow.

For a real boss-kill demo (vs smoke test), use a class from `@BossContentMod`
or another properly attributed third-party/content mod that has been registered
with `BossSignalAPI.RegisterBossClass()`.
instead of `ZmbM_MarksTester`, and check that
`mods/TrophyHunter/config/bosses.json` has a `trophy` mapping for it.

## Cold-stop sequence

```powershell
Get-Process DayZServer_x64 -ErrorAction SilentlyContinue | Stop-Process -Force
cd backends/bosssignal-backend
docker compose down
```

## Health checks

```powershell
# backend up
curl.exe --max-time 5 -s http://localhost:6700/health

# both servers heartbeating
curl.exe --max-time 5 -s http://localhost:6700/api/v1/servers

# stats summary
curl.exe --max-time 5 -s http://localhost:6700/api/v1/stats

# recent events (heartbeats + spawns + kills)
curl.exe --max-time 5 -s "http://localhost:6700/api/v1/eventslimit=10"

# DayZ processes alive (PowerShell - tasklist /FI is broken under git-bash)
Get-Process DayZServer_x64 -ErrorAction SilentlyContinue

# DayZ ports listening (game + steam + query for each server)
netstat -ano -p UDP | findstr "2302 2402 27016 27017"

# HiveAPI (separate backend, ops-api container)
curl.exe --max-time 5 -s http://localhost:6701/health
```

## Known gotchas

### Data verification kick on join

Almost always means the client modset doesn't match the server modset exactly -
either a mod is missing, a stray Workshop mod is enabled, or a mod is built from
a different source than the server's PBO. Fixes, in order:

1. Use the launcher's **"SETUP DLCS AND MODS AND JOIN"** from the server entry.
   Eliminates modlist drift entirely.
2. If you just edited a mod's source, run step 2 of cold-start (`modctl ship`)
   then restart both servers - the server scans `addons/` once at boot and
   caches the manifest, so swapping a PBO mid-run leaves clients with phantom
   verify errors.
3. If you're self-hosting on the same machine the server runs on, your
   Launcher's mod-folder pointer must be a **separate tree** from the server's
   `@*` folders. Sharing the server's mod folders triggers
   `VE_UNEXPECTED_MOD_PBO (0x0004074)`.

### `modctl ship` fails with `PermissionError: ... .pbo`

The server is still running and holding the PBO file open. Stop it before
shipping (see step 2 above). modctl can't kill the server for you because it
shouldn't make assumptions about which servers you've launched.

### LAN browser only shows one of the two local servers

Known DayZ Launcher discovery bug. Both servers ARE running - confirm with
`Get-Process DayZServer_x64` and the `/api/v1/servers` curl. Use Direct Connect
for the missing one and add to Favorites.

### `MarksContent` missing from launcher mod list

The DayZ client needs a `!Workshop\@MarksContent` entry pointing at the server
build. `modctl ship markscontent` recreates it via its `sync_client_workshop`
step. If you need to do it by hand:

```powershell
$client = 'C:\Program Files (x86)\Steam\steamapps\common\DayZ\!Workshop\@MarksContent'
$server = 'C:\Program Files (x86)\Steam\steamapps\common\DayZServer\@MarksContent'
New-Item -ItemType Directory -Force -Path $client | Out-Null
foreach ($child in 'addons','keys') {
  $linkPath = Join-Path $client $child
  $target   = Join-Path $server $child
  if (-not (Test-Path $linkPath)) {
    New-Item -ItemType Junction -Path $linkPath -Target $target | Out-Null
  }
}
@'
protocol = 1;
publishedid = 0;
name = "MarksContent";
timestamp = 0;
'@ | Set-Content -Path (Join-Path $client 'meta.cpp') -NoNewline -Encoding ASCII
```

Then close the launcher fully and reopen.

### Ops UI "Loaded mods" shows placeholder

The dashboard's loaded-mods card currently renders a placeholder - the backend
doesn't yet expose the per-server mod manifest. Tracked separately; don't treat
this as a bug.

### Backend logs show `IntegrityError: duplicate key value ... ix_events_idempotency_key`

Should no longer fire - `events.py` wraps the commit in a try/except and returns
a `duplicate` response on the race. If it does, capture the full traceback and
file an issue.

### Dashboard shows old data after restart

Force-refresh the page (`Ctrl+Shift+R`). The React build is cached aggressively.

### Docker Desktop engine not running

```powershell
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Start-Sleep 15
docker ps
```

### Runtime error modal on the DayZ server window

Always click **Abort**. Don't click "Continue" - the server limps along in a
broken state and the next batch of events will be lost or doubled. Claude can't
click native Windows dialogs; if you see one in a remote-control session,
that's a hand-on-keyboard moment.

## Repeatable commands library

If you want a one-shot boot script: see `start-dayz-stack.ps1` at the repo root
(legacy; uses `modctl serve` instead of the batch files). For now, prefer the
two `Start-Process` calls above because they reuse the existing Steam-installed
launch scripts and their bundled mod ordering.

## Where things write to disk

- DayZ server logs: `C:\Program Files (x86)\Steam\steamapps\common\DayZServer\profiles\` and `profiles_B\`
  - Newest `script_*.log` and `DayZServer_x64_*.RPT` are the post-mortem feed.
- Backend events: Postgres in the `bosssignal-backend-db-1` container; query via the API.
- DayZ Launcher data: `C:\Users\<user>\AppData\Local\DayZ Launcher\`.
