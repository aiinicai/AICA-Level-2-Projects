@echo off
REM BRMCo Accounting Hub - Server Host launcher (development). Keep this window open.
cd /d "%~dp0"
title BRMCo Accounting Hub - Server Host

if not exist ".venv\Scripts\python.exe" (
    echo First run: setting up Python environment...
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv .venv
    ) else (
        py -3 -m venv .venv 2>nul || python -m venv .venv
    )
    if not exist ".venv\Scripts\python.exe" (
        echo Python was not found. Install Python 3.12 from https://www.python.org
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || (pause & exit /b 1)
)

echo Starting BRMCo Server Host at http://127.0.0.1:8001
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8001
pause
