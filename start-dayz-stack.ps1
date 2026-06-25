# start-dayz-stack.ps1 - One script to launch the entire DayZ dev stack
# Usage: .\start-dayz-stack.ps1 [-Stop]

param([switch]$Stop)

$root = $PSScriptRoot
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$services = @(
    @{ Name="BossSignal"; Port=6700; Dir="backends\bosssignal-backend"; Cmd="python -m uvicorn app.main:app --host 0.0.0.0 --port 6700" },
    @{ Name="HiveAPI";    Port=6701; Dir="backends\hiveapi";            Cmd="python -m uvicorn app.main:app --host 0.0.0.0 --port 6701" },
    @{ Name="Dashboard";  Port=6702; Dir="frontends\web-ui";            Cmd="npm run dev -- --port 6702" }
)

if ($Stop) {
    Write-Host "Stopping all DayZ services..." -ForegroundColor Yellow
    Get-Process DayZServer_x64 -ErrorAction SilentlyContinue | Stop-Process -Force
    # Kill processes on our ports
    foreach ($svc in $services) {
        $conn = Get-NetTCPConnection -LocalPort $svc.Port -ErrorAction SilentlyContinue
        if ($conn) { Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue }
    }
    Write-Host "All stopped." -ForegroundColor Green
    return
}

Write-Host "=== DayZ Dev Stack ===" -ForegroundColor Cyan
Write-Host ""

# Start backends as hidden background jobs
foreach ($svc in $services) {
    $fullDir = Join-Path $root $svc.Dir
    $logFile = Join-Path $logDir "$($svc.Name.ToLower()).log"
    Write-Host "Starting $($svc.Name) on port $($svc.Port)..." -ForegroundColor Gray
    Start-Process powershell -ArgumentList "-WindowStyle Hidden -Command `"cd '$fullDir'; $($svc.Cmd) *> '$logFile'`"" -WindowStyle Hidden
}

# Start DayZ Server (visible - it's the main thing)
# BOSSSIGNAL_SECRET must match the SHARED_SECRET in your Enforce mod and backend.
# Set a real value in your environment before running; "CHANGE_ME" is an insecure
# local-dev placeholder and MUST be overridden for any shared/public deployment.
Write-Host "Starting DayZ Server on port 2302..." -ForegroundColor Gray
if (-not $env:BOSSSIGNAL_SECRET) { $env:BOSSSIGNAL_SECRET = "CHANGE_ME" }
$bossSignalSecret = $env:BOSSSIGNAL_SECRET
$modctlDir = Join-Path $root "tools-extra\modctl"
Start-Process powershell -ArgumentList "-WindowStyle Hidden -Command `"cd '$modctlDir'; `$env:BOSSSIGNAL_SECRET='$bossSignalSecret'; python -m modctl -c mods.yaml serve *> '$logDir\dayz-server.log'`"" -WindowStyle Hidden

# Wait and health check
Write-Host ""
Write-Host "Waiting for services..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "=== Health Check ===" -ForegroundColor Cyan
$allGood = $true
foreach ($svc in $services) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:$($svc.Port)" -TimeoutSec 3 -ErrorAction SilentlyContinue
        Write-Host "  $($svc.Name) :$($svc.Port)  OK" -ForegroundColor Green
    } catch {
        Write-Host "  $($svc.Name) :$($svc.Port)  starting..." -ForegroundColor Yellow
        $allGood = $false
    }
}
$dayz = Get-Process DayZServer_x64 -ErrorAction SilentlyContinue
if ($dayz) { Write-Host "  DayZ Server :2302  OK (PID $($dayz.Id))" -ForegroundColor Green }
else { Write-Host "  DayZ Server :2302  starting..." -ForegroundColor Yellow }

Write-Host ""
Write-Host "=== Port Map ===" -ForegroundColor Cyan
Write-Host "  BossSignal   http://localhost:6700"
Write-Host "  HiveAPI      http://localhost:6701"
Write-Host "  Dashboard    http://localhost:6702"
Write-Host "  Neo4j        bolt://localhost:6703  (browser: http://localhost:6704)"
Write-Host "  DayZ Server  localhost:2302"
Write-Host ""
Write-Host "Logs in: $logDir" -ForegroundColor Gray
Write-Host "Stop all: .\start-dayz-stack.ps1 -Stop" -ForegroundColor Gray
