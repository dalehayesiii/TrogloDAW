# Exercise the shipped helper against the real native installer in an isolated test installation.
param([Parameter(Mandatory=$true)][string]$InstallRoot,[Parameter(Mandatory=$true)][string]$TestRoot)
$ErrorActionPreference = 'Stop'
$previousConfig = $env:TROGLODAW_CONFIG_DIR
$previousTestApp = $env:TROGLODAW_TEST_APP
$previousMarker = $env:TROGLODAW_TEST_BLOCKED_MARKER
$previousUnbounded = $env:TROGLODAW_TEST_UNBOUNDED_SHUTDOWN
$env:TROGLODAW_CONFIG_DIR = Join-Path $InstallRoot 'app'
$baseRoot = [System.IO.Path]::GetFullPath($TestRoot).TrimEnd('\')
$installed = [System.IO.Path]::GetFullPath($InstallRoot).TrimEnd('\')
if (-not $installed.StartsWith($baseRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe handoff test installation' }
$helperRoot = Join-Path $baseRoot 'update helper with spaces'
New-Item -ItemType Directory -Path $helperRoot -Force | Out-Null
$manifest = Get-Content ./dist/release.json -Raw | ConvertFrom-Json
$installerName = "TrogloDAW-Setup-$($manifest.version).exe"
if ($manifest.installer -cne $installerName) { throw 'Handoff installer filename differs from build version' }
$installer = Join-Path $helperRoot $installerName
Copy-Item -LiteralPath (Join-Path './dist' $installerName) -Destination $installer
$helper = Join-Path $helperRoot 'app_update.ps1'
Copy-Item -LiteralPath (Join-Path $installed 'app/scripts/windows/app_update.ps1') -Destination $helper
$configPath = Join-Path $installed 'app/config.local.json'
$before = [System.IO.File]::ReadAllBytes($configPath)
$probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,0)
$probe.Start(); $port=$probe.LocalEndpoint.Port; $probe.Stop()
$python = Join-Path $installed 'python/python.exe'
$app = Join-Path $installed 'app/backend/app.py'
$server = Start-Process -FilePath $python -ArgumentList @("`"$app`"",'--port',$port,'--no-browser') -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $helperRoot 'server.stdout') -RedirectStandardError (Join-Path $helperRoot 'server.stderr')
$url="http://127.0.0.1:$port"
$planPath=Join-Path $helperRoot 'plan.json'
$statusPath=Join-Path $helperRoot 'status.json'
$runner=$null
$blockedConnection=$null
function Wait-Healthy {
    $deadline=[DateTime]::UtcNow.AddSeconds(60)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $value=Invoke-RestMethod "$url/api/health" -TimeoutSec 2
            if ($value.application -eq 'troglodaw' -and -not $value.updating) { return $value }
        } catch { }
        Start-Sleep -Milliseconds 200
    }
    throw 'Updated installed service did not become healthy'
}
function Start-TestHelper {
    return Start-Process -FilePath powershell.exe -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',"`"$helper`"",'-Plan',"`"$planPath`"") -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $helperRoot 'helper.stdout') -RedirectStandardError (Join-Path $helperRoot 'helper.stderr')
}
try {
    $null=Wait-Healthy
    $plan=@{installer=$installer;sha256=('0'*64);version=$manifest.version;source_sha=$manifest.sha;install_root=$installed;pid=$server.Id;host='127.0.0.1';port=$port;status=$statusPath}
    [System.IO.File]::WriteAllText($planPath,($plan|ConvertTo-Json),[System.Text.UTF8Encoding]::new($false))
    $runner=Start-TestHelper
    if (-not $runner.WaitForExit(15000) -or $runner.ExitCode -eq 0) { throw 'Tampered installer was not rejected before handoff' }
    $server.Refresh()
    if ($server.HasExited -or (Wait-Healthy).application -ne 'troglodaw') { throw 'Pre-handoff failure stopped the running app' }
    $plan.sha256=(Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLower()
    # A successful native installer with an unexpected identity must retain recovery
    # status and data, without restarting a payload it has not validated.
    $plan.source_sha='0'*40
    [System.IO.File]::WriteAllText($planPath,($plan|ConvertTo-Json),[System.Text.UTF8Encoding]::new($false))
    Remove-Item -LiteralPath $statusPath -ErrorAction SilentlyContinue
    $runner=Start-TestHelper
    $deadline=[DateTime]::UtcNow.AddSeconds(15)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ((Test-Path -LiteralPath $statusPath) -and (Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json).phase -eq 'waiting') { break }
        Start-Sleep -Milliseconds 100
    }
    if ((Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json).phase -ne 'waiting') { throw 'Failure-path helper did not acknowledge its plan' }
    $null=Invoke-RestMethod "$url/api/shutdown" -Method Post -Headers @{'X-TrogloDAW-Request'='1'} -ContentType 'application/json' -Body '{}'
    if (-not $server.WaitForExit(15000)) { throw 'Failure-path original app did not stop' }
    $deadline=[DateTime]::UtcNow.AddSeconds(120)
    $failed=$false
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $status=Invoke-RestMethod "$url/api/updates" -TimeoutSec 2
            if ($status.helper -and $status.phase -eq 'failed') { $failed=$true; break }
        } catch { }
        Start-Sleep -Milliseconds 150
    }
    if (-not $failed -or $status.message -notmatch 'identity') { throw 'Native post-install failure did not expose recovery status' }
    if (-not (Test-Path -LiteralPath $installer) -or [Convert]::ToBase64String($before) -ne [Convert]::ToBase64String([IO.File]::ReadAllBytes($configPath))) { throw 'Native failure discarded recovery artifact or preferences' }
    Stop-Process -Id $runner.Id -Force
    $runner.WaitForExit()
    $env:TROGLODAW_TEST_APP = $app
    $env:TROGLODAW_TEST_BLOCKED_MARKER = Join-Path $helperRoot 'blocked-request-entered'
    $env:TROGLODAW_TEST_UNBOUNDED_SHUTDOWN = '1'
    $shutdownFixture = [IO.Path]::GetFullPath('scripts/serve_shutdown_fixture.py')
    $server = Start-Process -FilePath $python -ArgumentList @("`"$shutdownFixture`"",'--port',$port,'--no-browser') -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $helperRoot 'retry.stdout') -RedirectStandardError (Join-Path $helperRoot 'retry.stderr')
    $null=Wait-Healthy
    $blockedConnection = [Net.Sockets.TcpClient]::new('127.0.0.1',$port)
    $requestBytes = [Text.Encoding]::ASCII.GetBytes("GET /api/fixture/blocked HTTP/1.1`r`nHost: localhost`r`nConnection: close`r`n`r`n")
    $blockedConnection.GetStream().Write($requestBytes,0,$requestBytes.Length)
    $deadline=[DateTime]::UtcNow.AddSeconds(5)
    while (-not (Test-Path -LiteralPath $env:TROGLODAW_TEST_BLOCKED_MARKER) -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
    if (-not (Test-Path -LiteralPath $env:TROGLODAW_TEST_BLOCKED_MARKER)) { throw 'Native stalled HTTP request did not enter the service' }
    $plan.pid=$server.Id
    $plan.source_sha=$manifest.sha
    [IO.File]::WriteAllText($planPath,($plan|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    Remove-Item -LiteralPath $statusPath
    $runner=Start-TestHelper
    $deadline=[DateTime]::UtcNow.AddSeconds(15)
    $acknowledged=$false
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-Path -LiteralPath $statusPath) {
            $status=Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
            if ($status.phase -eq 'waiting') { $acknowledged=$true; break }
            if ($status.phase -eq 'failed') { throw ("Native helper failed before acknowledgment: " + $status.message) }
        }
        Start-Sleep -Milliseconds 100
    }
    if (-not $acknowledged) { throw 'Native helper did not acknowledge its plan' }
    $null=Invoke-RestMethod "$url/api/shutdown" -Method Post -Headers @{'X-TrogloDAW-Request'='1'} -ContentType 'application/json' -Body '{}'
    if ($server.WaitForExit(1500)) { throw 'Legacy shutdown fixture did not reproduce the lingering process' }
    $deadline=[DateTime]::UtcNow.AddSeconds(180)
    $observed=$false
    while (-not $runner.HasExited -and [DateTime]::UtcNow -lt $deadline) {
        try {
            $status=Invoke-RestMethod "$url/api/updates" -TimeoutSec 2
            if ($status.helper) { $observed=$true }
        } catch { }
        Start-Sleep -Milliseconds 150
        $runner.Refresh()
    }
    if (-not $runner.HasExited -or $runner.ExitCode -ne 0) { throw 'Native update installation/restart failed' }
    if (-not $server.WaitForExit(5000)) { throw 'Updater fallback left the original process alive' }
    if (-not $observed) { throw 'Temporary update status listener was not observable' }
    $health=Wait-Healthy
    if ($health.version -ne $manifest.version -or $health.sha -ne $manifest.sha) { throw 'Restarted runtime identity differs from the verified update' }
    $after=[System.IO.File]::ReadAllBytes($configPath)
    if ([Convert]::ToBase64String($before) -ne [Convert]::ToBase64String($after)) { throw 'Native update changed persisted storage preferences' }
    $null=Invoke-RestMethod "$url/api/shutdown" -Method Post -Headers @{'X-TrogloDAW-Request'='1'} -ContentType 'application/json' -Body '{}'
    Start-Sleep -Milliseconds 1000
    if ((Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json).phase -ne 'complete') { throw 'Helper did not confirm healthy restart' }
    Write-Output 'Real stalled-process handoff recovery, status listener, confirmed healthy restart and pre-handoff tamper rejection passed.'
} finally {
    if ($blockedConnection) { $blockedConnection.Close() }
    if ($runner -and -not $runner.HasExited) { Stop-Process -Id $runner.Id -Force }
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force }
    # Only processes executing inside this isolated installation may be stopped.
    Get-Process python,pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($installed+'\',[StringComparison]::OrdinalIgnoreCase) } | Stop-Process -Force
    $env:TROGLODAW_CONFIG_DIR = $previousConfig
    $env:TROGLODAW_TEST_APP = $previousTestApp
    $env:TROGLODAW_TEST_BLOCKED_MARKER = $previousMarker
    $env:TROGLODAW_TEST_UNBOUNDED_SHUTDOWN = $previousUnbounded
}
