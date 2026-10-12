@echo off
rem TrogloDAW command line (compatible mm alias). Example: mm.bat list / mm.bat demo
"%~dp0python\python.exe" "%~dp0app\backend\cli.py" %*
