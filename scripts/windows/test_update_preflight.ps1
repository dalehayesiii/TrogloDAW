# Use the actual Windows helper with synthetic bytes; no installer is executed.
param([Parameter(Mandatory=$true)][string]$HelperPath,[Parameter(Mandatory=$true)][string]$TestRoot)
$ErrorActionPreference = 'Stop'
$baseRoot = [IO.Path]::GetFullPath($TestRoot).TrimEnd('\')
$fixtureRoot = [IO.Path]::GetFullPath((Join-Path $baseRoot 'preflight rejection with spaces'))
if (-not $fixtureRoot.StartsWith($baseRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe preflight test root' }
foreach ($mode in @('free','occupied')) {
    $caseRoot = Join-Path $fixtureRoot $mode
    $installRoot = Join-Path $caseRoot 'synthetic-install'
    New-Item -ItemType Directory -Force -Path $caseRoot,$installRoot | Out-Null
    $helper = Join-Path $caseRoot 'app_update.ps1'
    Copy-Item -LiteralPath $HelperPath -Destination $helper -Force
    $installer = Join-Path $caseRoot 'synthetic-installer.exe'
    [IO.File]::WriteAllText($installer,'Synthetic rejected installer; must never execute.')
    $statusPath = Join-Path $caseRoot 'status.json'
    Remove-Item -LiteralPath $statusPath -ErrorAction SilentlyContinue
    $planPath = Join-Path $caseRoot 'plan.json'
    $stdout = Join-Path $caseRoot 'helper.stdout'
    $stderr = Join-Path $caseRoot 'helper.stderr'
    $probe = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0)
    $probe.Server.ExclusiveAddressUse = $true
    $runner = $null
    try {
        $probe.Start()
        $port = $probe.LocalEndpoint.Port
        if ($mode -eq 'free') { $probe.Stop() }
        $plan = @{installer=$installer;sha256=('0'*64);version='0.0.0';source_sha=('0'*40);install_root=$installRoot;pid=$PID;host='127.0.0.1';port=$port;status=$statusPath}
        [IO.File]::WriteAllText($planPath,($plan|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
        $runner = Start-Process -FilePath powershell.exe -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',"`"$helper`"",'-Plan',"`"$planPath`"") -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        $null = $runner.Handle
        if (-not $runner.WaitForExit(15000)) {
            $detail = if (Test-Path -LiteralPath $statusPath) { Get-Content -LiteralPath $statusPath -Raw } else { 'No failure status' }
            throw "Rejected preflight retained its helper on a $mode port: $detail"
        }
        $runner.Refresh()
        if ($runner.ExitCode -ne 1) { throw "Rejected preflight returned exit code $($runner.ExitCode): $(Get-Content -LiteralPath $stderr -Raw)" }
        $status = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
        if ($status.phase -ne 'failed' -or $status.message -notmatch 'Installer verification failed') { throw "Rejected preflight lost its checksum failure: $($status.message)" }
        if ($mode -eq 'free') {
            $available = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$port)
            try { $available.Start() } finally { $available.Stop() }
        } elseif ($probe.LocalEndpoint.Port -ne $port) { throw 'Rejected preflight changed the occupied listener' }
        Write-Output "Native checksum rejection exited promptly without a recovery listener on the $mode port."
    } finally {
        if ($runner -and -not $runner.HasExited) { Stop-Process -Id $runner.Id -Force }
        $probe.Stop()
    }
}
