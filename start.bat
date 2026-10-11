@echo off
setlocal EnableExtensions
title musicmaker
cd /d "%~dp0"

echo ============================================
echo   musicmaker - starting up
echo ============================================

rem ---- find a Python 3.10-3.14 ----
set "PY="
for %%V in (3.14 3.13 3.12 3.11 3.10) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
  )
)
if not defined PY (
  python -c "import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,14) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo.
  echo  Python 3.10 - 3.14 was not found on this computer.
  echo.
  echo  1. Download Python 3.12 from:  https://www.python.org/downloads/windows/
  echo     ^(direct: https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe^)
  echo  2. In the installer, tick "Add python.exe to PATH", then click Install Now.
  echo  3. Double-click start.bat again.
  echo.
  start "" "https://www.python.org/downloads/windows/"
  pause
  exit /b 1
)
echo Using Python: %PY%

rem ---- create venv on first run ----
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment ^(first run only^)...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo Failed to create the virtual environment.
    pause
    exit /b 1
  )
)

rem ---- install / update deps when requirements.txt changes ----
set "STAMP=.venv\requirements.installed"
fc /b requirements.txt "%STAMP%" >nul 2>&1
if errorlevel 1 (
  echo Installing dependencies ^(first run takes a few minutes^)...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo Dependency install failed. Check your internet connection and try again.
    pause
    exit /b 1
  )
  copy /y requirements.txt "%STAMP%" >nul
)

echo.
echo Launching musicmaker... your browser will open at http://127.0.0.1:7860
echo Keep this window open while you use the app. Close it to quit.
echo.
".venv\Scripts\python.exe" app.py %*
if errorlevel 1 pause
endlocal
