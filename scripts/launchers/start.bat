@echo off
setlocal
cd /d "%~dp0..\.."
where uv >nul 2>&1
if errorlevel 1 (
  echo Install uv from https://docs.astral.sh/uv/getting-started/installation/ and retry.
  pause
  exit /b 1
)
uv sync --locked
if errorlevel 1 exit /b 1
if not exist "frontend\dist\browser\index.html" (
  where npm >nul 2>&1
  if errorlevel 1 (
    echo Source setup needs Node.js 24.15+ to build the frontend. The installer includes it prebuilt.
    pause
    exit /b 1
  )
  call npm ci --ignore-scripts
  if errorlevel 1 exit /b 1
  call npm run build
  if errorlevel 1 exit /b 1
)
uv run --locked python backend/app.py %*
if errorlevel 1 pause
