@echo off
setlocal EnableExtensions
title AuditPro - Internal Audit Management System
cd /d "%~dp0"

echo ============================================================
echo   AuditPro - Internal Audit Management System
echo   Installs dependencies (first run) and starts the app
echo ============================================================
echo.

REM ---------- locate Python 3 (skip the Microsoft Store alias) ----------
set "PYEXE="
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PYEXE (
        echo %%P | find /i "WindowsApps" >nul || set "PYEXE=%%P"
    )
)
if not defined PYEXE (
    for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
        if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
    )
)
if not defined PYEXE (
    for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%P"
)
if not defined PYEXE (
    echo [ERROR] Python 3.10 or later was not found.
    echo         Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
    goto :fail
)
echo Using Python: %PYEXE%
"%PYEXE%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo [ERROR] Python 3.10 or later is required.
    goto :fail
)

REM ---------- virtual environment ----------
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Creating virtual environment in .venv ...
    "%PYEXE%" -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        goto :fail
    )
)
set "VPY=%~dp0.venv\Scripts\python.exe"

REM ---------- dependencies ----------
echo.
echo Checking / installing dependencies ...
"%VPY%" -m pip install --upgrade pip --disable-pip-version-check -q
"%VPY%" -m pip install -r requirements.txt --disable-pip-version-check -q
if errorlevel 1 (
    echo [ERROR] Dependency installation failed. Check your internet / proxy settings.
    echo         Behind a corporate proxy, run:  set HTTPS_PROXY=http://proxy:port   then re-run this file.
    goto :fail
)

REM ---------- start ----------
if not exist "data" mkdir "data"
echo.
echo Starting AuditPro at http://127.0.0.1:5050  (browser opens automatically)
echo Close this window or press Ctrl+C to stop the server.
echo.
"%VPY%" backend\app.py
if errorlevel 1 goto :fail
goto :eof

:fail
echo.
echo Setup did not complete. See the messages above.
pause
exit /b 1
