# Quick DayZ Server Test - Single attempt with fast failure
# Use this when you just want to see if it crashes immediately

param(
    [switch]$NoBuild,  # Skip build step
    [string[]]$Mods = @("bosssignal", "markscontent")
)

$script = Join-Path $PSScriptRoot "launch_with_recovery.ps1"

Write-Host "=== Quick Test Mode ===" -ForegroundColor Cyan
Write-Host "This will make ONE attempt to start the server" -ForegroundColor Cyan
Write-Host "Monitor timeout: 5 minutes (fail-fast)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$params = @{
    MaxRetries = 1
    MonitorTimeoutSeconds = 300  # 5 minutes - fail fast for debugging
    QuickFail = $true
    Mods = $Mods
}

if ($NoBuild) {
    $params.SkipBuild = $true
}

& $script @params
