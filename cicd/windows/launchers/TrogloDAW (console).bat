@echo off
title TrogloDAW
cd /d "%~dp0"
echo Starting TrogloDAW... your browser will open at http://127.0.0.1:7860
echo Keep this window open while you use the app. Close it (or use Quit in the app) to stop.
"%~dp0python\python.exe" "%~dp0app\backend\app.py" %*
if errorlevel 1 pause
