# Sets up two nightly Task Scheduler tasks for dayz-stack:
#   1. DayZStackWorkshopSnapshotter — Steam Workshop top mods (Layer 2 intel)
#   2. DayZStackServerSnapshotter — Battlemetrics top DayZ servers + mod fingerprints
#
# Both run as the current user so they can read STEAM_API_KEY from your env.
# Idempotent — safe to re-run; replaces any existing tasks with the same names.

$Python     = "C:\Users\<user>\Dayz\dayz\platform\.venv\Scripts\python.exe"
$WorkingDir = "C:\Users\<user>\Dayz\dayz\platform"

function Register-DayZStackTask {
    param(
        [string]$TaskName,
        [string]$Description,
        [string]$ArgList,   # was $Args — that's a reserved automatic var in PS, silently empty
        [datetime]$RunAt
    )

    $Trigger = New-ScheduledTaskTrigger -Daily -At $RunAt

    $Action = New-ScheduledTaskAction `
        -Execute $Python `
        -Argument $ArgList `
        -WorkingDirectory $WorkingDir

    $Settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -DontStopIfGoingOnBatteries `
        -AllowStartIfOnBatteries `
        -RestartCount 1 `
        -RestartInterval (New-TimeSpan -Minutes 30) `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

    $Principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType Interactive

    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Description $Description `
        -Trigger $Trigger `
        -Action $Action `
        -Settings $Settings `
        -Principal $Principal | Out-Null

    Write-Host "Registered task '$TaskName'." -ForegroundColor Green
}

# 03:00 — Workshop snapshot (needs STEAM_API_KEY)
Register-DayZStackTask `
    -TaskName "DayZStackWorkshopSnapshotter" `
    -Description "Nightly Steam Workshop snapshot for dayz-stack intel layer (4 query types x 1000 mods)" `
    -ArgList "-m dayzstack_intel.cli snapshot --all" `
    -RunAt (Get-Date "03:00")

# 03:30 — Server snapshot (no auth needed; staggered to spread load)
Register-DayZStackTask `
    -TaskName "DayZStackServerSnapshotter" `
    -Description "Nightly Battlemetrics top-200 DayZ server snapshot (player counts + mod fingerprints)" `
    -ArgList "-m dayzstack_intel.cli snapshot-servers --source battlemetrics --max-servers 200" `
    -RunAt (Get-Date "03:30")

Write-Host "`n--- Both tasks registered. Next runs:" -ForegroundColor Cyan
Get-ScheduledTask -TaskName DayZStackWorkshopSnapshotter, DayZStackServerSnapshotter | `
    Select-Object TaskName, State, @{n='NextRun'; e={(Get-ScheduledTaskInfo $_).NextRunTime}} | `
    Format-Table -AutoSize
