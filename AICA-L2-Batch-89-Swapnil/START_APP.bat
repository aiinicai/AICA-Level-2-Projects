@echo off
rem MCA Compliance Mapper - double-click to start (Windows).
rem First run: creates the virtual environment, installs pinned packages, creates .env,
rem migrates the database and loads the FICTITIOUS demo firm. Later runs just start the app.
setlocal
cd /d "%~dp0"
title MCA Compliance Mapper
chcp 65001 >nul

if exist ".venv\Scripts\python.exe" goto deps
echo Creating the Python virtual environment (first run only)...
where py >nul 2>nul && (py -3 -m venv .venv) || (python -m venv .venv)
if not exist ".venv\Scripts\python.exe" (
  echo.
  echo Python 3.12 or newer is required. Install it from https://www.python.org/downloads/
  echo ^(tick "Add python.exe to PATH"^), then double-click START_APP.bat again.
  pause
  exit /b 1
)

:deps
echo Checking packages...
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo.
  echo Could not install the required packages. Check the internet connection for the first run.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" cli.py init-db || goto failed
".venv\Scripts\python.exe" cli.py seed-demo --if-empty || goto failed
".venv\Scripts\python.exe" run.py
goto end

:failed
echo.
echo Start-up failed - see the message above.

:end
pause
