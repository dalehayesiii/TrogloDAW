# Exercise native install/upgrade/uninstall and the actual embedded browser service.
$ErrorActionPreference = 'Stop'
$testWork = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [System.IO.Path]::GetTempPath() }
$testRoot = [System.IO.Path]::GetFullPath((Join-Path $testWork ('MusicMaker-check-' + [System.Guid]::NewGuid().ToString('N'))))
if (-not $testRoot.StartsWith([System.IO.Path]::GetFullPath($testWork).TrimEnd('\') + '\')) { throw 'Unsafe installer test root' }
$installRoot = Join-Path $testRoot 'installed'
$modelRoot = Join-Path $testRoot 'models with spaces'
$libraryRoot = Join-Path $testRoot 'library'
New-Item -ItemType Directory -Path $testRoot,$modelRoot,$libraryRoot -Force | Out-Null
# Restore pre-existing registration and shortcuts even after a failed test.
$registryPaths = @('HKCU:/Software/MusicMaker','HKCU:/Software/Microsoft/Windows/CurrentVersion/Uninstall/MusicMaker')
$registryBackup = @{}
foreach ($path in $registryPaths) {
    if (Test-Path -LiteralPath $path) {
        $key = Get-Item -LiteralPath $path
        $registryBackup[$path] = @($key.GetValueNames() | ForEach-Object { @{Name=$_; Value=$key.GetValue($_); Kind=$key.GetValueKind($_)} })
    }
}
$desktopRoot = [Environment]::GetFolderPath('Desktop')
$programsRoot = [Environment]::GetFolderPath('Programs')
$shortcutPaths = @((Join-Path $desktopRoot 'Music Maker.lnk'),(Join-Path $programsRoot 'Music Maker'),(Join-Path $desktopRoot 'TrogloDAW.lnk'),(Join-Path $programsRoot 'TrogloDAW'))
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
    if ((Get-FileHash ./dist/TrogloDAW-Setup.exe).Hash -ne (Get-FileHash ./dist/MusicMaker-Setup.exe).Hash) { throw 'Compatibility installer differs' }
    $legacyFolder = Join-Path $programsRoot 'Music Maker'
    New-Item -ItemType Directory -Path $legacyFolder -Force | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    $legacyShortcut = $shell.CreateShortcut((Join-Path $legacyFolder 'Music Maker.lnk'))
    $legacyShortcut.TargetPath = Join-Path $installRoot 'python/pythonw.exe'
    $legacyShortcut.Save()
    $customShortcut = Join-Path $legacyFolder 'Custom entry.txt'
    [System.IO.File]::WriteAllText($customShortcut,'Synthetic custom entry; preserved during branding migration')
    Install-TestApp
    if ((Test-Path (Join-Path $legacyFolder 'Music Maker.lnk')) -or -not (Test-Path $customShortcut) -or -not (Test-Path (Join-Path $desktopRoot 'TrogloDAW.lnk'))) { throw 'Shortcut branding migration failed' }
    if ((Get-ItemProperty $registryPaths[1]).DisplayName -ne 'TrogloDAW') { throw 'Uninstall display branding differs' }
    $python = Join-Path $installRoot 'python/python.exe'
    $env:MM_LIBRARY = $libraryRoot
    & (Join-Path $installRoot 'mm.bat') demo
    if ($LASTEXITCODE) { throw 'Embedded CLI demo failed' }
    & $python scripts/smoke_producer.py
    if ($LASTEXITCODE) { throw 'Embedded producer failed' }
    $env:MM_TEST_PYTHON = $python
    $env:MM_TEST_APP = Join-Path $installRoot 'app/backend/app.py'
    npm run e2e
    if ($LASTEXITCODE) { throw 'Installed Angular UI / Python service failed' }
    $manifest = Get-Content dist/release.json -Raw | ConvertFrom-Json
    $version = (Get-ItemProperty $registryPaths[1]).DisplayVersion
    if ($version -ne $manifest.version) { throw 'Installed version differs from build' }
    $owned = Join-Path $modelRoot 'installed.bin'
    $shared = Join-Path $modelRoot 'shared.bin'
    $unrelated = Join-Path $modelRoot 'personal.txt'
    [System.IO.File]::WriteAllText($owned,'synthetic owned asset')
    [System.IO.File]::WriteAllText($shared,'synthetic shared asset')
    [System.IO.File]::WriteAllText($unrelated,'preserve unrelated files')
    New-Item -ItemType Directory (Join-Path $modelRoot '.troglodaw') -Force | Out-Null
    $ownedFiles = @{ 'installed.bin'=(Get-FileHash $owned -Algorithm SHA256).Hash.ToLower(); 'shared.bin'=(Get-FileHash $shared -Algorithm SHA256).Hash.ToLower() }
    @{files=$ownedFiles} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $modelRoot '.troglodaw/installercheck.json')
    @{files=@{'shared.bin'=$ownedFiles['shared.bin']}} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $modelRoot '.troglodaw/otherowner.json')
    $configPath = Join-Path $installRoot 'app/config.local.json'
    @{installation_id='installercheck'; model_dir=$modelRoot; model_roots=@($modelRoot); library_dir=$libraryRoot} | ConvertTo-Json | Set-Content $configPath
    $before = Get-Content $configPath -Raw
    Install-TestApp
    if ((Get-Content $configPath -Raw) -ne $before -or -not (Test-Path $owned)) { throw 'Upgrade changed preferences or models' }
    Uninstall-TestApp $false
    if ((Test-Path $owned) -or -not (Test-Path $shared) -or -not (Test-Path $unrelated) -or -not (Test-Path (Join-Path $libraryRoot 'catalog.json'))) { throw 'Default model removal violated ownership/library contract' }
    Install-TestApp
    [System.IO.File]::WriteAllText($owned,'keep this owned asset')
    @{files=@{'installed.bin'=(Get-FileHash $owned -Algorithm SHA256).Hash.ToLower()}} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $modelRoot '.troglodaw/installercheck.json')
    @{installation_id='installercheck'; model_roots=@($modelRoot)} | ConvertTo-Json | Set-Content $configPath
    Uninstall-TestApp $true
    if (-not (Test-Path $owned)) { throw 'Uninstall opt-out removed model assets' }
    Write-Output 'Native install, upgrade, default removal, opt-out and installed browser checks passed.'
} finally {
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
    Remove-Item Env:MM_TEST_PYTHON,Env:MM_TEST_APP -ErrorAction SilentlyContinue
}
