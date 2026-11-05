@echo off
setlocal enabledelayedexpansion
title CA Practice Management
cd /d "%~dp0"

echo ========================================================
echo   CA Practice Management - Universal Launcher
echo ========================================================
echo.

:: 1. If the standalone EXE exists, launch it directly!
if exist "CA_Practice_Management.exe" (
    echo [INFO] Starting standalone CA Practice Management executable...
    start "" "CA_Practice_Management.exe"
    exit /b 0
)

:: 2. Check if server is already running
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Server is already active! Opening browser...
    start http://localhost:8000
    exit /b 0
)

:: 3. Test if current .venv is valid on THIS machine
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" --version >nul 2>nul
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=.venv\Scripts\python.exe"
        goto :START_SERVER
    ) else (
        echo [INFO] Detected virtual environment from another machine. Rebuilding for this PC...
        rmdir /s /q .venv >nul 2>nul
    )
)

:: 4. Find system Python
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "SYS_PYTHON=python"
    goto :SETUP_VENV
)
where py >nul 2>nul
if %errorlevel% equ 0 (
    set "SYS_PYTHON=py -3"
    goto :SETUP_VENV
)

echo [ERROR] Python 3.11+ was not found on this computer.
echo Please install Python from https://www.python.org/downloads/
echo Note: Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:SETUP_VENV
echo [*] Setting up Python virtual environment (.venv)...
%SYS_PYTHON% -m venv .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
set "PYTHON_EXE=.venv\Scripts\python.exe"
echo [*] Installing required packages from requirements.txt...
"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install -r requirements.txt

:START_SERVER
echo [*] Starting CA Practice Management Server...
echo [*] Waiting for server and opening HTML front-end in your browser...

start "" /b powershell -NoProfile -Command "$url='http://localhost:8000'; for ($i=0; $i -lt 30; $i++) { Start-Sleep -Milliseconds 500; try { $res=Invoke-WebRequest -Uri ($url + '/health') -UseBasicParsing -TimeoutSec 1; if ($res.StatusCode -eq 200) { Start-Process $url; break } } catch {} }; if ($i -ge 30) { Start-Process $url }"

echo.
echo ========================================================
echo   CA Practice Management is running!
echo   Front-End URL:    http://localhost:8000
echo   Default Username: admin
echo   Default Password: ChangeMe123!
echo ========================================================
echo.

"%PYTHON_EXE%" -m uvicorn app:app --host 0.0.0.0 --port 8000
pause
