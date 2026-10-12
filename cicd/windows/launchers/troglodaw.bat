@echo off
rem TrogloDAW command line. Example: troglodaw.bat list / troglodaw.bat demo
"%~dp0python\python.exe" "%~dp0app\backend\cli.py" %*
