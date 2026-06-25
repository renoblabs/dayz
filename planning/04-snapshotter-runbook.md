# Snapshotter runbook

The Layer 2 nightly snapshotter that bank-rolls Steam Workshop data into `intel.workshop_snapshots`.

## What it does

Runs four Steam Web API queries (`trend`, `recent`, `votes`, `updated`) against DayZ (appid 221100), each up to 10 pages × 100 items = 1000 ranked workshop entries. Stores one row per (snapshot_date × query_type × workshop_id). Result: ~3000-4000 new rows per night.

Idempotent - re-running on the same calendar day skips already-captured rows.

## One-time setup

### 1. Steam API key in env

Get a free key at https://steamcommunity.com/dev/apikey (sign in with the Steam account you want attributed to API requests; "domain" can be `localhost`).

Two ways to make it available to the snapshotter:

**Option A: System env var** (simplest, what the Task Scheduler task expects):
```powershell
[Environment]::SetEnvironmentVariable("STEAM_API_KEY", "PASTE_KEY_HERE", "User")
```
Restart any open shells / IDEs after setting. Verify: `echo $env:STEAM_API_KEY` (PowerShell) or `echo %STEAM_API_KEY%` (cmd).

**Option B: Doppler** (preferred long-term, if you stand up a `dayz-stack` Doppler project). Wrap the python command with `doppler run --project dayz-stack --config dev -- python -m dayzstack_intel.cli snapshot --all`. Currently no `dayz-stack` project exists in your Doppler workspace - create one if you want this path.

### 2. Apply the intel schema (one time per machine)

```powershell
cd C:\Users\<user>\Dayz\dayz-stack\intel
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Confirms with: `Running upgrade  -> 0001, workshop_snapshots in intel schema.`

### 3. Manual smoke test (do this first to verify the key works)

```powershell
cd C:\Users\<user>\Dayz\dayz-stack
.\.venv\Scripts\python.exe -m dayzstack_intel.cli snapshot --query trend --max-pages 1
```

Expected: JSON output `{"trend": ~100}`. Check with:
```powershell
.\.venv\Scripts\python.exe -m dayzstack_intel.cli stats
```

### 4. Register the nightly Task Scheduler jobs

```powershell
cd C:\Users\<user>\Dayz\dayz-stack
PowerShell -ExecutionPolicy Bypass -File .\infra\setup-snapshotter.ps1
```

This creates **two** sibling tasks (session 4 added the server snapshot):

| Task | Time | What it does | Auth |
|---|---|---|---|
| `DayZStackWorkshopSnapshotter` | 03:00 nightly | `dayzstack_intel.cli snapshot --all` - 4 query types × top 1000 mods from Steam Workshop | Needs `STEAM_API_KEY` env var |
| `DayZStackServerSnapshotter` | 03:30 nightly | `dayzstack_intel.cli snapshot-servers --source battlemetrics --max-servers 200` - top DayZ servers + their mod fingerprints from Battlemetrics | None (Battlemetrics public API) |

Both run as your interactive user, both retry once on failure, both inherit `STEAM_API_KEY` from your env config.

The task will:
- Start when the machine wakes if it was sleeping at 03:00
- Restart once on failure
- Time out after 30 minutes (snapshots usually take 1-2 minutes)
- Run as your interactive user (so it inherits your `STEAM_API_KEY` env var)

### 5. Verify both tasks are registered

```powershell
Get-ScheduledTask -TaskName DayZStackWorkshopSnapshotter,DayZStackServerSnapshotter |
    Select-Object TaskName,State,@{n='NextRun';e={(Get-ScheduledTaskInfo $_).NextRunTime}} |
    Format-Table -AutoSize
```

## Daily operations

### Check yesterday's run worked

```powershell
.\.venv\Scripts\python.exe -m dayzstack_intel.cli stats
```

Expected output today + yesterday:
```
date         query        count
2026-04-26   recent          ~1000
2026-04-26   trend           ~1000
2026-04-26   updated         ~1000
2026-04-26   votes           ~1000
2026-04-25   recent          ~1000
...
```

### See task history

```powershell
Get-ScheduledTaskInfo -TaskName DayZStackSnapshotter
```

### Manual run anytime

```powershell
Start-ScheduledTask -TaskName DayZStackSnapshotter
```

Or directly:
```powershell
cd C:\Users\<user>\Dayz\dayz-stack
.\.venv\Scripts\python.exe -m dayzstack_intel.cli snapshot --all
```

### Delete the task (if you want to stop it)

```powershell
Unregister-ScheduledTask -TaskName DayZStackSnapshotter -Confirm:$false
```

## Why this matters now

Workshop velocity, staleness, and trend computations require accumulated daily snapshots. Lost calendar days are *permanent* - there's no API to backfill yesterday's "what was trending" data. Every day the snapshotter doesn't run is a day of analysis we can never do.

By the time you sit down to actually USE this data (Layer 2 query/report tooling, future session), you want 2-4 weeks already banked. That's why this gets installed BEFORE corpus expansion or anything else flashier.

## Recovery if the box gets rebuilt

1. Re-clone repo, `uv sync`, `pip install -e ./shared -e ./kb -e ./intel`
2. Restore the env var (`STEAM_API_KEY`)
3. Apply migrations (`alembic upgrade head`)
4. Re-run `setup-snapshotter.ps1`
5. Restore Postgres data from your backup of the docker volume `dayz-stack_postgres-data`. If no backup, you've lost all historical snapshots - start fresh and accept that compounding restarts.
