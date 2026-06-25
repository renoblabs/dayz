# auto_capture.ps1 - Watch DayZ server logs and auto-store errors to graph
#
# Usage: .\auto_capture.ps1 [-Watch]
#
# Monitors DayZ server profiles for new crash/script logs and sends
# errors to the dayz-memory MCP server via Neo4j.

param(
    [switch]$Watch
)

# Point DAYZ_SERVER_PATH at your DayZ server install root.
$DayzServerPath = if ($env:DAYZ_SERVER_PATH) { $env:DAYZ_SERVER_PATH } else { "C:\Program Files (x86)\Steam\steamapps\common\DayZServer" }
$DayzProfiles = Join-Path $DayzServerPath "profiles"

# Error patterns to capture
$ErrorPatterns = @(
    @{ Pattern = 'SCRIPT\s*\(E\):.*Undefined function'; Type = 'compile' },
    @{ Pattern = "SCRIPT\s*\(E\):.*Can't find class"; Type = 'compile' },
    @{ Pattern = 'SCRIPT\s*\(E\):.*Bad type'; Type = 'compile' },
    @{ Pattern = "SCRIPT\s*\(E\):.*Can't compile"; Type = 'compile' },
    @{ Pattern = 'FAIL.*->.*code='; Type = 'runtime' },
    @{ Pattern = 'crash|CRASH'; Type = 'runtime' },
    @{ Pattern = '0x000[0-9A-Fa-f]{4,}'; Type = 'verification' },
    @{ Pattern = 'VE_UNEXPECTED_MOD_PBO'; Type = 'verification' }
)

function Get-LatestLog {
    param([string]$Pattern)
    Get-ChildItem $DayzProfiles -Filter $Pattern |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Extract-Errors {
    param([string]$LogPath)

    $content = Get-Content $LogPath -Raw
    $errors = @()

    foreach ($ep in $ErrorPatterns) {
        $matches = [regex]::Matches($content, $ep.Pattern)
        foreach ($m in $matches) {
            # Get context: 2 lines before and 3 after
            $lines = Get-Content $LogPath
            $lineNum = ($content.Substring(0, $m.Index) -split "`n").Count
            $start = [Math]::Max(0, $lineNum - 3)
            $end = [Math]::Min($lines.Count - 1, $lineNum + 3)
            $snippet = ($lines[$start..$end]) -join "`n"

            # Extract mod name from path
            $modMatch = [regex]::Match($m.Value, '@(\w+)/scripts/')
            $modName = if ($modMatch.Success) { $modMatch.Groups[1].Value } else { $null }

            $errors += @{
                message = $m.Value.Trim()
                error_type = $ep.Type
                mod_name = $modName
                raw_snippet = $snippet
                timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
            }
        }
    }

    return $errors
}

function Store-ToNeo4j {
    param($Errors)

    foreach ($err in $Errors) {
        $props = $err | ConvertTo-Json -Compress
        # base64 the payload so multi-line snippets / quotes / control chars can't
        # break the inline json.loads (was a real bug: raw_snippet has newlines).
        $propsB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($props))
        $pythonCmd = @"
from neo4j import GraphDatabase
import json, uuid, hashlib, base64, os
from datetime import datetime

# Supply NEO4J_PASSWORD via environment; there is no usable default.
neo4j_password = os.environ.get('NEO4J_PASSWORD', '<your-neo4j-password>')

err = json.loads(base64.b64decode('$propsB64').decode('utf-8'))
err['timestamp'] = err.get('timestamp') or datetime.utcnow().isoformat()
if not err.get('stack_trace'):
    err['stack_trace'] = ''

# Idempotent fingerprint: same error never creates a second node, no matter how
# many times the scheduled scan re-reads the same log. This is the anti-pollution
# invariant the 5-min schedule depends on.
fp = hashlib.sha1(
    (err['message'] + '|' + err['error_type'] + '|' + str(err.get('mod_name'))).encode('utf-8', 'replace')
).hexdigest()

driver = GraphDatabase.driver('bolt://localhost:6703', auth=('neo4j', neo4j_password))
with driver.session() as session:
    session.run(
        '''
        MERGE (e:DayZError {fingerprint: `$fp})
        ON CREATE SET e.id = `$id, e.first_seen = `$timestamp, e.seen_count = 1
        ON MATCH  SET e.seen_count = coalesce(e.seen_count, 1) + 1
        SET e.message = `$message, e.error_type = `$error_type, e.mod_name = `$mod_name,
            e.raw_snippet = `$raw_snippet, e.last_seen = `$timestamp, e.resolved = false,
            e.stack_trace = `$stack_trace, e.project = 'dayz-mod-<org>',
            e.source = 'auto_capture'
        ''',
        fp=fp, id=str(uuid.uuid4()), message=err['message'], error_type=err['error_type'],
        mod_name=err.get('mod_name'), raw_snippet=err.get('raw_snippet'),
        timestamp=err['timestamp'], stack_trace=err['stack_trace']
    )
driver.close()
"@
        $venvPython = Join-Path $env:USERPROFILE "Dayz\dayz\platform\.venv\Scripts\python.exe"
        $pythonCmd | & $venvPython -
    }
    Write-Host "[capture] Directly stored $($Errors.Count) errors into Neo4j graph"
}

# One-shot capture
function Capture-Once {
    Write-Host "[capture] Scanning DayZ server logs..."

    $scriptLog = Get-LatestLog "script_*.log"
    $crashLog = Get-LatestLog "crash_*.log"
    $rptLog = Get-LatestLog "DayZServer_x64_*.RPT"

    $allErrors = @()

    if ($scriptLog) {
        Write-Host "[capture] Checking: $($scriptLog.Name)"
        $allErrors += Extract-Errors $scriptLog.FullName
    }
    if ($crashLog) {
        Write-Host "[capture] Checking: $($crashLog.Name)"
        $allErrors += Extract-Errors $crashLog.FullName
    }
    if ($rptLog) {
        Write-Host "[capture] Checking: $($rptLog.Name)"
        $allErrors += Extract-Errors $rptLog.FullName
    }

    if ($allErrors.Count -gt 0) {
        Store-ToNeo4j $allErrors
        Write-Host "[capture] Found $($allErrors.Count) errors"
    } else {
        Write-Host "[capture] No new errors found"
    }
}

# Watch mode
function Watch-Logs {
    Write-Host "[capture] Starting watch mode. Press Ctrl+C to stop."
    Write-Host "[capture] Monitoring: $DayzProfiles"

    $lastCheck = Get-Date

    while ($true) {
        Start-Sleep -Seconds 5

        $scriptLog = Get-LatestLog "script_*.log"
        if ($scriptLog -and $scriptLog.LastWriteTime -gt $lastCheck) {
            Write-Host "[capture] New activity detected in $($scriptLog.Name)"
            $errors = Extract-Errors $scriptLog.FullName
            if ($errors.Count -gt 0) {
                Store-ToNeo4j $errors
            }
            $lastCheck = Get-Date
        }
    }
}

# Main
if ($Watch) {
    Watch-Logs
} else {
    Capture-Once
}
