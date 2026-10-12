# Exercise the actual installed runtime/UI; shared by preview builds and semantic-release prepare.
$ErrorActionPreference = 'Stop'
$testWork = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [System.IO.Path]::GetTempPath() }
$installRoot = Join-Path $testWork ('MusicMaker-check-' + [System.Guid]::NewGuid().ToString('N'))
$installer = Start-Process -FilePath ./dist/MusicMaker-Setup.exe -ArgumentList @('/S', "/D=$installRoot") -Wait -PassThru -WindowStyle Hidden
if ($installer.ExitCode) { throw 'Installer failed' }
$python = Join-Path $installRoot 'python/python.exe'
& $python (Join-Path $installRoot 'app/backend/cli.py') demo
if ($LASTEXITCODE) { throw 'Embedded CLI demo failed' }
& $python scripts/smoke_producer.py
if ($LASTEXITCODE) { throw 'Embedded producer failed' }
$env:MM_TEST_PYTHON = $python
$env:MM_TEST_APP = Join-Path $installRoot 'app/backend/app.py'
npm run e2e
if ($LASTEXITCODE) { throw 'Installed Angular UI / Python service failed' }
$manifest = Get-Content dist/release.json -Raw | ConvertFrom-Json
$version = (Get-ItemProperty 'HKCU:/Software/Microsoft/Windows/CurrentVersion/Uninstall/MusicMaker').DisplayVersion
if ($version -ne $manifest.version) { throw 'Installed version differs from build' }
