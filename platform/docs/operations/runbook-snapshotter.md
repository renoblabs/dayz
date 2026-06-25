# Runbook - Snapshotter

Operational guide for the nightly Workshop and Server snapshot tasks.

## What runs

Two scheduled tasks (Windows Task Scheduler):
- `dayz-stack: Workshop snapshot` - 03:00 daily, calls `dayz-stack-intel snapshot --all`
- `dayz-stack: Server snapshot` - 03:30 daily, calls `dayz-stack-intel snapshot-servers --max-servers 200`

Both registered by `infra/setup-snapshotter.ps1`.

## Verify it's working

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

The User-scope env var doesn't always propagate to Windows Task Scheduler context. Two workarounds:

**Quick:** Set as a System env var (requires admin).

```powershell
[Environment]::SetEnvironmentVariable("STEAM_API_KEY", "<key>", "Machine")
```

Then logoff/logon to refresh.

**Cleaner:** Add `.env` file loading on the snapshotter side. Tracked in `docs/reference/known-debt.md`.

### Server task exits with `Cannot connect to host` (Battlemetrics)

Battlemetrics rate-limits aggressive pollers. The snapshotter is conservative (1 req/sec, exponential backoff on 429). If still failing:

1. Check from the dev box: `curl https://api.battlemetrics.com/serversfilter[game]=dayz`
2. If that fails, the issue is upstream (Battlemetrics outage or your IP got temp-blocked)
3. If that works, the issue is in the snapshotter - check the task's last-run output

### Both tasks "registered" but never fire

The setup script uses PowerShell auto-variable shadowing protection - `$ArgList` was renamed from `$Args` (which is reserved). If you hand-edit the script and revert the variable name, the task registers with no Action and silently never fires. Re-run the setup script.

### Embeddings stalled on the KB side

Not a snapshotter issue but worth knowing because `dayz-stack-kb status` is a quick health check:

```bash
uv run dayz-stack-kb status
```

If `unembedded_chunks` keeps growing, the embed-fill background process died. Restart:

```bash
nohup uv run dayz-stack-kb embed-fill --concurrency 1 > /tmp/embedfill.log 2>&1 &
```

## Recovery from a bad snapshot

Snapshots are date-keyed. To purge a bad day:

```sql
DELETE FROM intel.server_mods       WHERE snapshot_date = 'YYYY-MM-DD';
DELETE FROM intel.server_snapshots  WHERE snapshot_date = 'YYYY-MM-DD';
DELETE FROM intel.workshop_snapshots WHERE snapshot_date = 'YYYY-MM-DD';
```

Then re-run the snapshotter manually:

```bash
uv run dayz-stack-intel snapshot --all
uv run dayz-stack-intel snapshot-servers
```

Date will be re-keyed to today.

## Backups (not yet automated)

This is a known debt entry. For manual backup:

```bash
docker exec dayz-stack-postgres pg_dump -U dayzstack dayzstack > backup-$(date +%F).sql
```

Run before any non-trivial schema migration. Tracked in `docs/reference/known-debt.md` as a near-term hygiene gap.

## Logs

Scheduled tasks log to Windows Event Viewer (Microsoft -> Windows -> TaskScheduler -> Operational). For ad-hoc runs, output goes to wherever stdout is redirected.

## Disabling for absences

Long absence from the dev box (>1 week)

```powershell
Disable-ScheduledTask -TaskName "dayz-stack: Workshop snapshot"
Disable-ScheduledTask -TaskName "dayz-stack: Server snapshot"
```

Re-enable on return:

```powershell
Enable-ScheduledTask -TaskName "dayz-stack: Workshop snapshot"
Enable-ScheduledTask -TaskName "dayz-stack: Server snapshot"
```

This avoids accumulating failed-task notifications when the dev box is offline or sleeping.
