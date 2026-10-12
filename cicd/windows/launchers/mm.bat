@echo off
rem Music Maker command line. Example:  mm.bat list   /   mm.bat demo
"%~dp0python\python.exe" "%~dp0app\cli.py" %*
