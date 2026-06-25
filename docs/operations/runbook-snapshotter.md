# Runbook - Snapshotter

Operational guide for the nightly Workshop and Server snapshot tasks. (Adapted from the pre-consolidation runbook in `platform/docs/operations/runbook-snapshotter.md`; this top-level doc points at the consolidated paths.)

## What runs

Two scheduled tasks (Windows Task Scheduler):
- `DayZStackWorkshopSnapshotter` - 03:00 daily, calls `dayz-stack-intel snapshot --all`
- `DayZStackServerSnapshotter` - 03:30 daily, calls `dayz-stack-intel snapshot-servers --max-servers 200`

Both registered by `platform/infra/setup-snapshotter.ps1`.

## Re-register tasks after consolidation

The old tasks point at the pre-consolidation `~/Dayz/dayz-stack/` paths. After consolidation:

```powershell
cd C:\Users\<user>\Dayz\dayz\platform
PowerShell -ExecutionPolicy Bypass -File .\infra\setup-snapshotter.ps1
```

The script now uses the new paths (`~/Dayz/dayz/platform/`) - verify by inspecting the registered task actions:

```powershell
Get-ScheduledTask -TaskName "DayZStack*" | Select-Object TaskName, Actions | Format-List
```

Expected output: `Execute = C:\Users\<user>\Dayz\dayz\platform\.venv\Scripts\python.exe`, `WorkingDirectory = C:\Users\<user>\Dayz\dayz\platform`.

## Verify snapshots are being captured

```bash
# Per-day row counts
docker exec dayz-stack-postgres psql -U dayzstack -d dayzstack -c "
  SELECT 'workshop' AS kind, snapshot_date, COUNT(*) AS rows
  FROM intel.workshop_snapshots GROUP BY snapshot_date
  UNION ALL
  SELECT 'servers', snapshot_date, COUNT(*)
  FROM intel.server_snapshots GROUP BY snapshot_date
  ORDER BY 1 DESC, 2 DESC;
"
```

Healthy output: ~4000 workshop rows per snapshot_date (4 queries × 1000 each), ~200 server rows.

## Common failures

### Workshop task exits with `STEAM_API_KEY not in env`

Known issue - User-scope env var doesn't always propagate to scheduled task scope. See `platform/docs/reference/known-debt.md`.

### Both tasks "registered" but never fire

PowerShell `$Args` is a reserved automatic variable; the setup script uses `$ArgList` instead. Don't rename it back.

### Embed-fill stalled

Not a snapshotter issue, but quick check:
```bash
cd platform
.venv/Scripts/dayz-stack-kb.exe status
```
If `unembedded_chunks` keeps growing, restart with `embed-fill --concurrency 1`.

## Disabling for absences

```powershell
Disable-ScheduledTask -TaskName "DayZStackWorkshopSnapshotter"
Disable-ScheduledTask -TaskName "DayZStackServerSnapshotter"
```
