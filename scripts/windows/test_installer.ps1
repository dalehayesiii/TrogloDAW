# Exercise native install/upgrade/uninstall and the actual embedded browser service.
param([switch]$ReleaseSmoke)

$ErrorActionPreference = 'Stop'
$testWork = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [System.IO.Path]::GetTempPath() }
$testRoot = [System.IO.Path]::GetFullPath((Join-Path $testWork ('TrogloDAW-check-' + [System.Guid]::NewGuid().ToString('N'))))
if (-not $testRoot.StartsWith([System.IO.Path]::GetFullPath($testWork).TrimEnd('\') + '\')) { throw 'Unsafe installer test root' }
$installRoot = Join-Path $testRoot 'installed with spaces'
$modelRoot = Join-Path $testRoot 'models with spaces'
$credentialOwner = 'installercheck' + [System.Guid]::NewGuid().ToString('N')
$credentialOther = 'installerother' + [System.Guid]::NewGuid().ToString('N')
$libraryRoot = Join-Path $testRoot 'library'
New-Item -ItemType Directory -Path $testRoot,$modelRoot,$libraryRoot -Force | Out-Null
# Restore pre-existing registration and shortcuts even after a failed test.
$registryPaths = @('HKCU:/Software/TrogloDAW','HKCU:/Software/Microsoft/Windows/CurrentVersion/Uninstall/TrogloDAW')
$registryBackup = @{}
foreach ($path in $registryPaths) {
    if (Test-Path -LiteralPath $path) {
        $key = Get-Item -LiteralPath $path
        $registryBackup[$path] = @($key.GetValueNames() | ForEach-Object { @{Name=$_; Value=$key.GetValue($_); Kind=$key.GetValueKind($_)} })
    }
}
$desktopRoot = [Environment]::GetFolderPath('Desktop')
$programsRoot = [Environment]::GetFolderPath('Programs')
$shortcutPaths = @((Join-Path $desktopRoot 'TrogloDAW.lnk'),(Join-Path $programsRoot 'TrogloDAW'))
foreach ($path in $shortcutPaths) {
    $parent = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($path))
    if ($parent -notin @($desktopRoot,$programsRoot)) { throw 'Unsafe shortcut test path' }
}
$shortcutBackup = @{}
foreach ($path in $shortcutPaths) {
    if (Test-Path -LiteralPath $path) {
        $backup = Join-Path $testRoot ([System.Guid]::NewGuid().ToString('N'))
        Copy-Item -LiteralPath $path -Destination $backup -Recurse
        $shortcutBackup[$path] = $backup
    }
}
function Install-TestApp {
    $process = Start-Process -FilePath ./dist/TrogloDAW-Setup.exe -ArgumentList @('/S', "/D=$installRoot") -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode) { throw 'Installer failed' }
}
function Uninstall-TestApp($keepModels) {
    $arguments = @('/S')
    if ($keepModels) { $arguments += '/KEEP_MODELS' }
    $arguments += "_?=$installRoot"
    $process = Start-Process -FilePath (Join-Path $installRoot 'Uninstall.exe') -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -or (Test-Path (Join-Path $installRoot 'python'))) { throw 'Native uninstall failed' }
}
try {
    $programFolder = Join-Path $programsRoot 'TrogloDAW'
    New-Item -ItemType Directory -Path $programFolder -Force | Out-Null
    $customShortcut = Join-Path $programFolder 'Custom entry.txt'
    [System.IO.File]::WriteAllText($customShortcut,'Synthetic custom entry; preserved during installation')
    Install-TestApp
    if (-not (Test-Path (Join-Path $programFolder 'TrogloDAW.lnk')) -or -not (Test-Path $customShortcut) -or -not (Test-Path (Join-Path $desktopRoot 'TrogloDAW.lnk'))) { throw 'TrogloDAW shortcut installation failed' }
    if ((Get-ItemProperty $registryPaths[1]).DisplayName -ne 'TrogloDAW') { throw 'Uninstall display branding differs' }
    $python = Join-Path $installRoot 'python/python.exe'
    & $python (Join-Path $installRoot 'app/backend/folders.py')
    if ($LASTEXITCODE) { throw 'Embedded native folder picker initialization failed' }
    $env:TROGLODAW_LIBRARY = $libraryRoot
    $manifest = Get-Content dist/release.json -Raw | ConvertFrom-Json
    $version = (Get-ItemProperty $registryPaths[1]).DisplayVersion
    if ($version -ne $manifest.version) { throw 'Installed version differs from build' }
    $identity = Get-Content (Join-Path $installRoot 'app/version.json') -Raw | ConvertFrom-Json
    if ($identity.version -ne $manifest.version -or $identity.sha -ne $manifest.sha -or $identity.repository -ne 'dalehayesiii/music-maker') { throw 'Installed runtime identity differs from published manifest' }
    if ($ReleaseSmoke) {
        # Final versioning changes installer metadata, not the checked app payload.
        # Verify service/static delivery without replaying browser/audio workflows.
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
        $listener.Start()
        $port = $listener.LocalEndpoint.Port
        $listener.Stop()
        $env:TROGLODAW_CONFIG_DIR = Join-Path $installRoot 'app'
        $env:TROGLODAW_HOST = '127.0.0.1'
        $app = Join-Path $installRoot 'app/backend/app.py'
        $server = Start-Process -FilePath $python -ArgumentList @("`"$app`"", '--port', $port, '--no-browser') -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $testRoot 'service.stdout') -RedirectStandardError (Join-Path $testRoot 'service.stderr')
        try {
            $baseUrl = "http://127.0.0.1:$port"
            $ready = $false
            $deadline = [DateTime]::UtcNow.AddSeconds(60)
            while ([DateTime]::UtcNow -lt $deadline) {
                $server.Refresh()
                if ($server.HasExited) { throw "Installed service exited: $(Get-Content (Join-Path $testRoot 'service.stderr') -Raw)" }
                try {
                    $health = Invoke-RestMethod "$baseUrl/api/health" -TimeoutSec 2
                    if ($health.application -eq 'troglodaw' -and $health.frontend -eq $true) { $ready = $true; break }
                } catch { }
                Start-Sleep -Milliseconds 250
            }
            if (-not $ready) { throw 'Installed service did not become healthy' }
            if ($health.version -ne $manifest.version -or $health.sha -ne $manifest.sha) { throw 'Installed service identity differs from published manifest' }
            $page = Invoke-WebRequest "$baseUrl/" -UseBasicParsing -TimeoutSec 10
            if ($page.Content -notmatch '<troglodaw-app') { throw 'Installed Angular document missing' }
            $assets = [regex]::Matches($page.Content, '(?:src|href)="([^"<>]+\.(?:js|css))"')
            if (-not $assets.Count) { throw 'Installed Angular entry assets missing' }
            foreach ($asset in $assets) {
                $response = Invoke-WebRequest ([Uri]::new([Uri]"$baseUrl/", $asset.Groups[1].Value)) -UseBasicParsing -TimeoutSec 10
                if ($response.StatusCode -ne 200 -or $response.Headers['Content-Type'] -match 'text/html') { throw 'Installed Angular asset did not load' }
            }
        } finally {
            if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force }
            $server.WaitForExit()
        }
        Uninstall-TestApp $true
        Write-Output 'Final installer version, API startup, static UI and uninstall smoke checks passed.'
        return
    }
    & (Join-Path $installRoot 'troglodaw.bat') demo
    if ($LASTEXITCODE) { throw 'Embedded CLI demo failed' }
    & $python scripts/smoke_producer.py
    if ($LASTEXITCODE) { throw 'Embedded producer failed' }
    $env:TROGLODAW_TEST_PYTHON = $python
    $env:TROGLODAW_TEST_APP = Join-Path $installRoot 'app/backend/app.py'
    npm run e2e
    if ($LASTEXITCODE) { throw 'Installed Angular UI / Python service failed' }
    $owned = Join-Path $modelRoot 'installed.bin'
    $shared = Join-Path $modelRoot 'shared.bin'
    $unrelated = Join-Path $modelRoot 'personal.txt'
    [System.IO.File]::WriteAllText($owned,'synthetic owned asset')
    [System.IO.File]::WriteAllText($shared,'synthetic shared asset')
    [System.IO.File]::WriteAllText($unrelated,'preserve unrelated files')
    New-Item -ItemType Directory (Join-Path $modelRoot '.troglodaw') -Force | Out-Null
    $ownedFiles = @{ 'installed.bin'=(Get-FileHash $owned -Algorithm SHA256).Hash.ToLower(); 'shared.bin'=(Get-FileHash $shared -Algorithm SHA256).Hash.ToLower() }
    # A canceled setup can own thousands of wheel/cache fragments. The cleanup
    # helper must not overflow nsExec's log with one enormous per-file JSON line.
    $cacheRoot = Join-Path $modelRoot 'cache/installercheck/canceled-setup'
    New-Item -ItemType Directory -Path $cacheRoot -Force | Out-Null
    $cacheChecksum = (Get-FileHash $owned -Algorithm SHA256).Hash.ToLower()
    foreach ($index in 0..4999) {
        $relative = 'cache/installercheck/canceled-setup/runtime-package-fragment-{0:D5}.bin' -f $index
        [System.IO.File]::WriteAllText((Join-Path $modelRoot $relative),'synthetic owned asset')
        $ownedFiles[$relative] = $cacheChecksum
    }
    @{files=$ownedFiles} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $modelRoot ('.troglodaw/'+$credentialOwner+'.json'))
    @{files=@{'shared.bin'=$ownedFiles['shared.bin']}} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $modelRoot '.troglodaw/otherowner.json')
    $configPath = Join-Path $installRoot 'app/config.local.json'
    @{installation_id=$credentialOwner; setup_seen=$true; check_updates=$false; model_dir=$modelRoot; model_roots=@($modelRoot); library_dir=$libraryRoot} | ConvertTo-Json | Set-Content $configPath
    $before = Get-Content $configPath -Raw
    $unsafeLibrary = Join-Path $installRoot 'app/legacy-library'
    New-Item -ItemType Directory -Path $unsafeLibrary -Force | Out-Null
    $unsafeFile = Join-Path $unsafeLibrary 'preserve.wav'
    [System.IO.File]::WriteAllText($unsafeFile,'synthetic legacy library')
    @{installation_id='installercheck'; library_dir=$unsafeLibrary; model_dir=$modelRoot} | ConvertTo-Json | Set-Content $configPath
    $blocked = Start-Process -FilePath (Join-Path $installRoot 'Uninstall.exe') -ArgumentList @('/S','/KEEP_MODELS',"_?=$installRoot") -PassThru -Wait -WindowStyle Hidden
    if ($blocked.ExitCode -eq 0 -or -not (Test-Path $unsafeFile) -or -not (Test-Path $python)) { throw 'Unsafe legacy library was not preserved before uninstall' }
    Set-Content -LiteralPath $configPath -Value $before -NoNewline
    Remove-Item -LiteralPath $unsafeFile
    Install-TestApp
    if ((Get-Content $configPath -Raw) -ne $before -or -not (Test-Path $owned)) { throw 'Upgrade changed preferences or models' }
    & ./scripts/windows/test_update_handoff.ps1 -InstallRoot $installRoot -TestRoot $testRoot
    if (-not (Test-Path $owned) -or -not (Test-Path (Join-Path $libraryRoot 'catalog.json'))) { throw 'In-app update lost library/model data' }
    uv run --locked python scripts/windows/test_update_access.py save $credentialOwner $credentialOther
    if ($LASTEXITCODE) { throw 'Native release credential preparation failed' }
    Uninstall-TestApp $false
    uv run --locked python scripts/windows/test_update_access.py verify $credentialOwner $credentialOther
    if ($LASTEXITCODE) { throw 'Native uninstall credential cleanup failed' }
    if ((Test-Path $owned) -or -not (Test-Path $shared) -or -not (Test-Path $unrelated) -or -not (Test-Path (Join-Path $libraryRoot 'catalog.json'))) { throw 'Default model removal violated ownership/library contract' }
    if (@(Get-ChildItem -LiteralPath $cacheRoot -File).Count) { throw 'Canceled setup cache files survived default uninstall' }
    Install-TestApp
    [System.IO.File]::WriteAllText($owned,'keep this owned asset')
    @{files=@{'installed.bin'=(Get-FileHash $owned -Algorithm SHA256).Hash.ToLower()}} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $modelRoot ('.troglodaw/'+$credentialOwner+'.json'))
    @{installation_id=$credentialOwner; model_roots=@($modelRoot)} | ConvertTo-Json | Set-Content $configPath
    uv run --locked python scripts/windows/test_update_access.py save $credentialOwner $credentialOther
    Uninstall-TestApp $true
    uv run --locked python scripts/windows/test_update_access.py verify $credentialOwner $credentialOther
    if ($LASTEXITCODE) { throw 'Retaining models also retained private release access' }
    if (-not (Test-Path $owned)) { throw 'Uninstall opt-out removed model assets' }
    Write-Output 'Native install, upgrade, default removal, opt-out and installed browser checks passed.'
} finally {
    if (-not $ReleaseSmoke) { uv run --locked python scripts/windows/test_update_access.py cleanup $credentialOwner $credentialOther }
    foreach ($path in $registryPaths) {
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse }
        if ($registryBackup.ContainsKey($path)) {
            $key = New-Item -Path $path -Force
            foreach ($entry in $registryBackup[$path]) { $key.SetValue($entry.Name,$entry.Value,$entry.Kind) }
        }
    }
    foreach ($path in $shortcutPaths) {
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
        if ($shortcutBackup.ContainsKey($path)) { Copy-Item -LiteralPath $shortcutBackup[$path] -Destination $path -Recurse }
    }
    Remove-Item Env:TROGLODAW_TEST_PYTHON,Env:TROGLODAW_TEST_APP -ErrorAction SilentlyContinue
    if ($ReleaseSmoke) {
        Remove-Item Env:TROGLODAW_CONFIG_DIR,Env:TROGLODAW_HOST -ErrorAction SilentlyContinue
    }
}
