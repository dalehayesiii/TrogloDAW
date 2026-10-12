@echo off
cd /d "%~dp0..\.."
uv run --locked python backend/cli.py %*
