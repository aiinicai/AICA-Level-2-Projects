@echo off
REM BRMCo Accounting Hub - Local Host launcher.
REM Double-click this file. Keep this window open while you work; close it to stop the app.
cd /d "%~dp0"
title BRMCo Accounting Hub - Local Host

if not exist ".venv\Scripts\python.exe" (
    echo First run: setting up Python environment. This takes a minute...
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv .venv
    ) else (
        py -3 -m venv .venv 2>nul || python -m venv .venv
    )
    if not exist ".venv\Scripts\python.exe" (
        echo.
        echo Python was not found. Install Python 3.12 from https://www.python.org and tick "Add python.exe to PATH".
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Installing requirements failed. Check your internet connection and try again.
        pause
        exit /b 1
    )
)

echo Starting BRMCo Local Host at http://127.0.0.1:8000
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
echo.
echo The Local Host has stopped.
pause
