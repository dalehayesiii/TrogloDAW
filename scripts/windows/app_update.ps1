# Run outside the installed directory so NSIS can replace the app safely.
param([Parameter(Mandatory=$true)][string]$Plan)
$ErrorActionPreference = 'Stop'
$listener = $null
$installerProcess = $null
$settings = $null
$state = $null
$restartProcess = $null
function Get-InstallerHash([string]$path) {
    $stream=[System.IO.File]::OpenRead($path)
    $hash=[System.Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($hash.ComputeHash($stream)).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $hash.Dispose() }
}
function Write-UpdateState([string]$phase, [string]$message) {
    $script:state = @{phase=$phase; message=$message; available_version=$settings.version; version=$settings.version; helper=$true}
    $temporary = $settings.status + '.tmp'
    [System.IO.File]::WriteAllText($temporary, ($script:state | ConvertTo-Json -Compress), [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $settings.status -Force
}
function Start-UpdateListener {
    $address = if ($settings.host -eq '::1') {[System.Net.IPAddress]::IPv6Loopback} else {[System.Net.IPAddress]::Loopback}
    $script:listener = [System.Net.Sockets.TcpListener]::new($address,[int]$settings.port)
    $script:listener.Start()
}
function Serve-UpdateStatus {
    if (-not $listener.Pending()) { return }
    $client = $listener.AcceptTcpClient()
    try {
        $stream = $client.GetStream()
        $stream.ReadTimeout = 2000
        $buffer = New-Object byte[] 2048
        $length = $stream.Read($buffer,0,$buffer.Length)
        $request = [System.Text.Encoding]::ASCII.GetString($buffer,0,$length)
        $allowed = $request -match '^GET /api/updates(?:\?[^ ]*)? HTTP/1\.[01]'
        $health = $request -match '^GET /api/health HTTP/1\.[01]' -and $script:state.phase -ne 'failed'
        $homeRequest = $request -match '^GET / HTTP/1\.[01]'
        $status = if ($allowed -or $health -or $homeRequest) {'200 OK'} else {'503 Service Unavailable'}
        $contentType = 'application/json'
        $body = if ($allowed) {$script:state | ConvertTo-Json -Compress} elseif ($health) {'{"application":"troglodaw","frontend":true,"updating":true}'} else {'{"detail":"Update installation in progress"}'}
        if ($homeRequest) {
            $contentType = 'text/html; charset=utf-8'
            $body = @'
<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>TrogloDAW update</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;font:18px system-ui;background:#f1eaf1;color:#332538}main{max-width:600px;margin:20px;padding:40px;border-radius:28px;border-top:5px solid #dba0d2;background:#fffafd}h1{font-size:32px}p{line-height:1.6;overflow-wrap:anywhere}@media(prefers-color-scheme:dark){body{background:#1c1720;color:#f5eaf4}main{background:#2d2431}}</style>
<main><h1>Updating TrogloDAW</h1><p id="message" role="status">Checking installation status...</p><p>Your library, models and preferences are kept. This page returns to the app after restart.</p><p>If installation fails, run the verified installer shown above or reopen the app from its shortcut.</p></main>
<script>setInterval(async()=>{try{const s=await(await fetch('/api/updates',{cache:'no-store'})).json();document.getElementById('message').textContent=s.message||'Reopening TrogloDAW...';if(!s.helper&&s.version==='__VERSION__')location.reload()}catch{}},1000)</script></html>
'@
            $body = $body.Replace('__VERSION__',$settings.version)
        }
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
        $header = [System.Text.Encoding]::ASCII.GetBytes("HTTP/1.1 $status`r`nContent-Type: $contentType`r`nCache-Control: no-store`r`nConnection: close`r`nContent-Length: $($bytes.Length)`r`n`r`n")
        $stream.Write($header,0,$header.Length)
        $stream.Write($bytes,0,$bytes.Length)
    } catch {
        # A browser can disconnect while the app's listener is changing.
    } finally {
        $client.Close()
    }
}
try {
    $settings = Get-Content -LiteralPath $Plan -Raw | ConvertFrom-Json
    $installRoot = [System.IO.Path]::GetFullPath($settings.install_root).TrimEnd('\')
    $installer = [System.IO.Path]::GetFullPath($settings.installer)
    $helperRoot = [System.IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
    if ($helperRoot -eq $installRoot -or $helperRoot.StartsWith($installRoot+'\',[System.StringComparison]::OrdinalIgnoreCase)) { throw 'Update helper is inside the installed app' }
    if (-not $installer.StartsWith($helperRoot+'\',[System.StringComparison]::OrdinalIgnoreCase) -or
        [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($settings.status)) -ne $helperRoot -or
        [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($Plan)) -ne $helperRoot) { throw 'Update files do not belong to the helper directory' }
    if ($settings.version -notmatch '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$' -or
        $settings.sha256 -notmatch '^[0-9a-f]{64}$' -or
        $settings.source_sha -notmatch '^[0-9a-f]{40}$' -or
        $settings.host -notin @('127.0.0.1','localhost','::1') -or
        [int]$settings.port -lt 1 -or [int]$settings.port -gt 65535 -or
        [int]$settings.pid -le 0) { throw 'Invalid update plan' }
    if ((Get-InstallerHash $installer) -ne $settings.sha256) { throw 'Installer verification failed' }
    if (-not (Test-Path -LiteralPath (Join-Path $installRoot 'python/python.exe'))) { throw 'Installed Python is missing' }
    $original = Get-Process -Id $settings.pid -ErrorAction Stop
    $originalPath = $original.Path
    if (-not $originalPath.StartsWith($installRoot+'\',[System.StringComparison]::OrdinalIgnoreCase)) { throw 'Running app is outside the installation' }
    $originalStarted = $original.StartTime
    $others = @(Get-Process python,pythonw,uv,ffmpeg-win-x86_64-v7.1 -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $settings.pid -and $_.Path -and $_.Path.StartsWith($installRoot+'\',[System.StringComparison]::OrdinalIgnoreCase) })
    if ($others.Count) { throw 'Another app instance or helper is still running' }
    Write-UpdateState 'waiting' 'Update started. Waiting for TrogloDAW to stop.'
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    while ($running = Get-Process -Id $settings.pid -ErrorAction SilentlyContinue) {
        if ($running.StartTime -ne $originalStarted -or $running.Path -ne $originalPath) { throw 'Original app process identity changed' }
        if ([DateTime]::UtcNow -gt $deadline) {
            # The app reserved an idle handoff before acknowledging this plan.
            # Never terminate a reused PID or another installation's executable.
            $null = $running.Handle
            if ($running.HasExited) { break }
            if ($running.StartTime -ne $originalStarted -or $running.Path -ne $originalPath) { throw 'Original app process identity changed' }
            Write-UpdateState 'waiting' 'Finishing idle app shutdown before installation...'
            $running.Kill()
            if (-not $running.WaitForExit(5000)) { throw 'The original idle app could not stop' }
            break
        }
        Start-Sleep -Milliseconds 100
    }
    Start-UpdateListener
    if ((Get-InstallerHash $installer) -ne $settings.sha256) { throw 'Installer changed before launch' }
    Write-UpdateState 'installing' 'Installing the verified update. Your library and models are kept.'
    $installerProcess = Start-Process -FilePath $installer -ArgumentList @('/S',"/D=$installRoot") -PassThru -WindowStyle Hidden
    while (-not $installerProcess.HasExited) {
        Serve-UpdateStatus
        Start-Sleep -Milliseconds 100
        $installerProcess.Refresh()
    }
    if ($installerProcess.ExitCode -ne 0) { throw 'The installer reported a failure' }
    $identity = Get-Content -LiteralPath (Join-Path $installRoot 'app/version.json') -Raw | ConvertFrom-Json
    if ($identity.version -ne $settings.version -or $identity.sha -ne $settings.source_sha -or $identity.repository -ne 'dalehayesiii/music-maker') { throw 'Installed identity did not match the verified release' }
    $python = Join-Path $installRoot 'python/pythonw.exe'
    $app = Join-Path $installRoot 'app/backend/app.py'
    if (-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $app)) { throw 'Updated app files are missing' }
    Write-UpdateState 'restarting' 'Update installed. Reopening TrogloDAW...'
    $listener.Stop()
    $listener = $null
    $restartLog = Join-Path $helperRoot 'restart.stderr.log'
    $restartProcess = Start-Process -FilePath $python -ArgumentList @("`"$app`"", '--host', $settings.host, '--port', $settings.port, '--no-browser') -WindowStyle Hidden -PassThru -RedirectStandardError $restartLog -RedirectStandardOutput (Join-Path $helperRoot 'restart.stdout.log')
    $hostAddress = if ($settings.host -eq '::1') {'[::1]'} else {$settings.host}
    $healthUrl = "http://${hostAddress}:$($settings.port)/api/health"
    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    $healthy = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        $restartProcess.Refresh()
        if ($restartProcess.HasExited) { throw "Updated app exited before startup. Diagnostic log: $restartLog" }
        try {
            $health = Invoke-RestMethod $healthUrl -TimeoutSec 2
            if ($health.application -eq 'troglodaw' -and -not $health.updating) {
                if ($health.version -ne $settings.version -or $health.sha -ne $settings.source_sha -or -not $health.frontend) { throw 'Restarted app identity or frontend differs from the verified release' }
                $healthy = $true
                break
            }
        } catch {
            if ($_.Exception.Message -match '^Restarted app identity') { throw }
        }
        Start-Sleep -Milliseconds 200
    }
    if (-not $healthy) { throw "Updated app did not become healthy. Diagnostic log: $restartLog" }
    Write-UpdateState 'complete' 'Update installed and TrogloDAW reopened successfully.'
} catch {
    $failure = $_.Exception.Message
    if ($restartProcess -and -not $restartProcess.HasExited) {
        try { $restartProcess.Kill(); $restartProcess.WaitForExit(5000) | Out-Null } catch { }
    }
    if ($settings) {
        try {
            Write-UpdateState 'failed' ("Update could not finish: $failure. Your library/models are kept. Verified installer: $installer")
            if (-not $listener) {
                try { Start-UpdateListener } catch { $listener = $null }
            }
            if ($listener) {
                $deadline = [DateTime]::UtcNow.AddMinutes(10)
                while ([DateTime]::UtcNow -lt $deadline) { Serve-UpdateStatus; Start-Sleep -Milliseconds 100 }
            }
        } catch { }
    }
    exit 1
} finally {
    if ($listener) { $listener.Stop() }
}
