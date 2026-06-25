
$port = 2302
$address = "127.0.0.1"
$logDir = "C:\Program Files (x86)\Steam\steamapps\common\DayZServer\profiles"
$pondsTimeout = 60
$lastPondsTime = $null
$maxTotalTime = 300 # 5 minute total safety timeout (fail fast)
$scriptStart = Get-Date

while ($true) {
    if (((Get-Date) - $scriptStart).TotalSeconds -gt $maxTotalTime) {
        Write-Output "MONITORING TIMEOUT"
        exit 2
    }

    # 1. Check Port 2302
    $connection = New-Object System.Net.Sockets.TcpClient
    $connected = $false
    try {
        $asyncResult = $connection.BeginConnect($address, $port, $null, $null)
        $wait = $asyncResult.AsyncWaitHandle.WaitOne(500, $false)
        if ($wait -and $connection.Connected) {
            $connected = $true
        }
    } catch {}
    finally {
        $connection.Close()
    }

    if ($connected) {
        Write-Output "SERVER READY"
        exit 0
    }

    # 2. Monitor RPT Log
    $latestRpt = Get-ChildItem -Path $logDir -Filter "*.rpt" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestRpt) {
        $content = Get-Content -Path $latestRpt.FullName -Tail 10
        $foundPonds = $false
        foreach ($line in $content) {
            if ($line -match "ponds") {
                $foundPonds = $true
                break
            }
        }

        if ($foundPonds) {
            if ($null -eq $lastPondsTime) {
                $lastPondsTime = Get-Date
            }
            $elapsed = (Get-Date) - $lastPondsTime
            if ($elapsed.TotalSeconds -gt $pondsTimeout) {
                Write-Output "HANG DETECTED"
                exit 1
            }
        } else {
            $lastPondsTime = $null
        }
    }

    Start-Sleep -Seconds 15
}
