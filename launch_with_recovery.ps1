# DayZ Server Crash-Resistant Launcher
# Handles the reality of modding: crashes are expected, hangs happen, just restart and move on.

param(
    [int]$MaxRetries = 10,
    [int]$MonitorTimeoutSeconds = 300,  # 5 minutes - fail-fast for debugging
    [int]$CrashCooldownSeconds = 5,     # Pause between crash and restart
    [switch]$SkipBuild,                  # Skip rebuild on each iteration
    [switch]$QuickFail,                  # Exit on first crash instead of retrying
    [string[]]$Mods = @("bosssignal", "markscontent")
)

$ErrorActionPreference = "Continue"
$serverExe = "C:\Program Files (x86)\Steam\steamapps\common\DayZServer\DayZServer_x64.exe"
$profilesDir = "C:\Program Files (x86)\Steam\steamapps\common\DayZServer\profiles"
$monitorScript = Join-Path $PSScriptRoot "monitor_dayz.ps1"
$modctlPath = Join-Path $PSScriptRoot "tools-extra\modctl"
$modctlConfig = Join-Path $modctlPath "mods.yaml"

# Set required environment variables for modctl.
# BOSSSIGNAL_SECRET must match the SHARED_SECRET in your Enforce mod and backend.
# Set a real value in your environment before running; this placeholder is a
# local-dev fallback only and MUST be overridden for any shared/public deployment.
if (-not $env:BOSSSIGNAL_SECRET) {
    Write-Warning "BOSSSIGNAL_SECRET not set; using insecure local-dev placeholder. Override before any real use."
    $env:BOSSSIGNAL_SECRET = "CHANGE_ME"
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN"  { "Yellow" }
        "SUCCESS" { "Green" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

function Get-ServerProcess {
    return Get-Process -Name "DayZServer_x64" -ErrorAction SilentlyContinue
}

function Stop-DayZServer {
    $procs = Get-ServerProcess
    if ($procs) {
        Write-Log "Stopping existing DayZ server processes..." "WARN"
        $procs | ForEach-Object {
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }
}

function Start-DayZServer {
    Write-Log "Starting DayZ server..." "INFO"
    
    # Use modctl serve if available, otherwise direct launch
    if (Test-Path $modctlConfig) {
        try {
            Push-Location $modctlPath
            & python -m modctl -c mods.yaml serve --detached 2>&1 | Out-Null
            Pop-Location
            Start-Sleep -Seconds 3
            return Get-ServerProcess
        } catch {
            Write-Log "modctl serve failed, falling back to direct launch" "WARN"
        }
    }
    
    # Direct launch fallback
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $serverExe
    $startInfo.WorkingDirectory = Split-Path $serverExe -Parent
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $false
    $startInfo.RedirectStandardError = $false
    
    try {
        $process = [System.Diagnostics.Process]::Start($startInfo)
        Write-Log "Server process started (PID: $($process.Id))" "SUCCESS"
        return $process
    } catch {
        Write-Log "Failed to start server: $_" "ERROR"
        return $null
    }
}

function Invoke-Monitoring {
    param([System.Diagnostics.Process]$ServerProcess)
    
    if (-not (Test-Path $monitorScript)) {
        Write-Log "Monitor script not found, using basic process monitoring" "WARN"
        return "PROCESS_WATCH"
    }
    
    Write-Log "Starting monitoring (timeout: $MonitorTimeoutSeconds seconds)..." "INFO"
    
    $monitorJob = Start-Job -ScriptBlock {
        param($scriptPath)
        & powershell.exe -File $scriptPath
    } -ArgumentList $monitorScript
    
    $timeout = $MonitorTimeoutSeconds
    $elapsed = 0
    $checkInterval = 5
    
    while ($elapsed -lt $timeout) {
        # Check if server process died
        if ($null -ne $ServerProcess -and $ServerProcess.HasExited) {
            Stop-Job -Job $monitorJob -ErrorAction SilentlyContinue
            Remove-Job -Job $monitorJob -Force -ErrorAction SilentlyContinue
            Write-Log "Server process exited (exit code: $($ServerProcess.ExitCode))" "ERROR"
            return "CRASH"
        }
        
        # Check monitor job status
        if ($monitorJob.State -eq "Completed") {
            $result = Receive-Job -Job $monitorJob
            Remove-Job -Job $monitorJob -Force
            
            $exitCode = $monitorJob.ChildJobs[0].JobStateInfo.Reason.ExitCode
            if ($null -eq $exitCode) { $exitCode = 0 }
            
            switch ($exitCode) {
                0 { 
                    Write-Log "Server is READY!" "SUCCESS"
                    return "READY" 
                }
                1 { 
                    Write-Log "HANG detected in logs" "ERROR"
                    return "HANG" 
                }
                2 { 
                    Write-Log "Monitor timeout reached" "ERROR"
                    return "TIMEOUT" 
                }
                default { 
                    Write-Log "Monitor returned unknown code: $exitCode" "WARN"
                    return "UNKNOWN" 
                }
            }
        }
        
        Start-Sleep -Seconds $checkInterval
        $elapsed += $checkInterval
    }
    
    Stop-Job -Job $monitorJob -ErrorAction SilentlyContinue
    Remove-Job -Job $monitorJob -Force -ErrorAction SilentlyContinue
    Write-Log "Monitoring timeout exceeded" "ERROR"
    return "TIMEOUT"
}

function Invoke-Diagnosis {
    if (-not (Test-Path $modctlConfig)) {
        Write-Log "modctl not found, skipping diagnosis" "WARN"
        return
    }
    
    Write-Log "Running crash diagnosis..." "INFO"
    try {
        Push-Location $modctlPath
        $diagOutput = & python -m modctl -c mods.yaml diagnose 2>&1
        Pop-Location
        
        if ($diagOutput) {
            Write-Log "=== DIAGNOSIS ===" "WARN"
            $diagOutput | ForEach-Object { Write-Host $_ }
            Write-Log "=== END DIAGNOSIS ===" "WARN"
        }
    } catch {
        Write-Log "Diagnosis failed: $_" "WARN"
    }
}

function Build-Mods {
    if ($SkipBuild) {
        Write-Log "Skipping build (--SkipBuild flag set)" "INFO"
        return $true
    }
    
    Write-Log "Building mods: $($Mods -join ', ')" "INFO"
    
    # Use modctl if available
    if (Test-Path $modctlConfig) {
        try {
            Push-Location $modctlPath
            foreach ($mod in $Mods) {
                Write-Log "Shipping modctl mod: $mod" "INFO"
                & python -m modctl -c mods.yaml ship $mod 2>&1
                if ($LASTEXITCODE -ne 0) {
                    throw "modctl ship $mod failed with exit code $LASTEXITCODE"
                }
            }
            Pop-Location
            Write-Log "Mod build complete" "SUCCESS"
            return $true
        } catch {
            Pop-Location -ErrorAction SilentlyContinue
            Write-Log "modctl build failed: $_" "ERROR"
            return $false
        }
    }
    
    # Fallback to build.bat
    $buildScript = Join-Path $PSScriptRoot "build-pipeline\build.bat"
    if (Test-Path $buildScript) {
        try {
            foreach ($mod in $Mods) {
                $folderName = switch ($mod.ToLowerInvariant()) {
                    "bosssignal" { "BossSignal" }
                    "hiveapi" { "HiveApiMod" }
                    "trophyhunter" { "TrophyHunter" }
                    "markscontent" { "MarksContent" }
                    default { $mod }
                }
                & cmd /c $buildScript $folderName 2>&1
                if ($LASTEXITCODE -ne 0) {
                    throw "build.bat $folderName failed with exit code $LASTEXITCODE"
                }
            }
            Write-Log "Mod build complete (build.bat)" "SUCCESS"
            return $true
        } catch {
            Write-Log "build.bat failed: $_" "ERROR"
            return $false
        }
    }
    
    Write-Log "No build system found, proceeding anyway" "WARN"
    return $true
}

# Main loop
Write-Log "=== DayZ Crash-Resistant Launcher ===" "INFO"
Write-Log "Max retries: $MaxRetries" "INFO"
Write-Log "Monitor timeout: $MonitorTimeoutSeconds seconds" "INFO"
Write-Log "Quick fail: $QuickFail" "INFO"

$attempt = 0
$successfulStarts = 0

while ($attempt -lt $MaxRetries) {
    $attempt++
    Write-Log "========================================" "INFO"
    Write-Log "Attempt $attempt of $MaxRetries" "INFO"
    Write-Log "========================================" "INFO"
    
    # Stop any existing servers
    Stop-DayZServer
    
    # Build mods (unless skipped)
    if (-not (Build-Mods)) {
        Write-Log "Build failed, cannot continue" "ERROR"
        exit 1
    }
    
    # Start server
    $serverProc = Start-DayZServer
    if ($null -eq $serverProc) {
        Write-Log "Failed to start server process" "ERROR"
        if ($QuickFail) { exit 1 }
        Start-Sleep -Seconds $CrashCooldownSeconds
        continue
    }
    
    # Monitor until ready, crashed, or hung
    $outcome = Invoke-Monitoring -ServerProcess $serverProc
    
    switch ($outcome) {
        "READY" {
            $successfulStarts++
            Write-Log "Server successfully started! (Success count: $successfulStarts)" "SUCCESS"
            Write-Log "Server is running. Press Ctrl+C to stop." "SUCCESS"
            
            # Keep monitoring in foreground
            try {
                while ($true) {
                    if ($serverProc.HasExited) {
                        Write-Log "Server exited unexpectedly!" "ERROR"
                        break
                    }
                    Start-Sleep -Seconds 5
                }
            } catch {
                Write-Log "Monitoring interrupted" "WARN"
            }
            
            # Server died after being ready - restart
            Write-Log "Restarting after crash..." "WARN"
            Invoke-Diagnosis
            Start-Sleep -Seconds $CrashCooldownSeconds
            continue
        }
        
        "CRASH" {
            Write-Log "Server crashed during startup" "ERROR"
            Invoke-Diagnosis
            if ($QuickFail) { exit 1 }
            Start-Sleep -Seconds $CrashCooldownSeconds
            continue
        }
        
        "HANG" {
            Write-Log "Server hung during startup" "ERROR"
            Stop-DayZServer
            Invoke-Diagnosis
            if ($QuickFail) { exit 1 }
            Start-Sleep -Seconds $CrashCooldownSeconds
            continue
        }
        
        default {
            Write-Log "Unknown outcome: $outcome" "ERROR"
            Stop-DayZServer
            if ($QuickFail) { exit 1 }
            Start-Sleep -Seconds $CrashCooldownSeconds
            continue
        }
    }
}

Write-Log "Max retries ($MaxRetries) exceeded. Giving up." "ERROR"
Stop-DayZServer
exit 1
