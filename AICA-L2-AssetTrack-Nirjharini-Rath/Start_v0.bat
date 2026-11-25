@echo off
setlocal
title AssetTrack v0 - Windows Launcher
cd /d "%~dp0"

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python 3.10+ is required. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating local Python virtual environment...
    python -m venv .venv
)

echo [2/3] Installing v0 dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -r requirements_v0.txt -q

echo [3/3] Starting AssetTrack v0 on http://127.0.0.1:8000 ...
".venv\Scripts\python.exe" run_v0.py
pause
