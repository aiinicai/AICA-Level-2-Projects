@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"
if errorlevel 1 (
    echo [ERROR] Could not open the application folder.
    if /I not "%~1"=="/quiet" pause
    exit /b 1
)

echo =======================================================================
echo      HARSH RESTRORECO - Installing / updating dependencies
echo =======================================================================
echo.

set "QUIET=0"
if /I "%~1"=="/quiet" set "QUIET=1"

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [ERROR] Python was not found on PATH.
    echo Install Python 3.12 or newer from https://www.python.org/
    echo Tick "Add python.exe to PATH" during setup.
    if "!QUIET!"=="0" pause
    exit /b 1
)

echo [INFO] Using: !PY!
echo [INFO] Folder: %CD%
echo.

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Existing virtual environment is broken. Recreating...
        rmdir /s /q venv
    )
)

if not exist "venv\Scripts\python.exe" (
    echo [INFO] Creating Python virtual environment...
    !PY! -m venv venv
    if errorlevel 1 (
        echo [ERROR] Could not create venv.
        if "!QUIET!"=="0" pause
        exit /b 1
    )
)

set "VPY=%CD%\venv\Scripts\python.exe"
if not exist "%VPY%" (
    echo [ERROR] venv Python is missing: %VPY%
    if "!QUIET!"=="0" pause
    exit /b 1
)

echo [INFO] Upgrading pip...
"%VPY%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] pip upgrade failed.
    if "!QUIET!"=="0" pause
    exit /b 1
)

echo [INFO] Installing packages from requirements.txt...
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    if "!QUIET!"=="0" pause
    exit /b 1
)

if not exist "data" mkdir data
if not exist "uploads" mkdir uploads
if not exist "exports" mkdir exports
if not exist "logs" mkdir logs
if not exist "sample_data" mkdir sample_data

echo [INFO] Preparing client data folder on this PC...
"%VPY%" -c "from app.services.client_store import data_root; print(data_root())"

echo [INFO] Checking database seed...
"%VPY%" -m app.seed
if errorlevel 1 (
    echo [WARN] Seed script reported an error. You can still start the app with run.bat
)

echo [INFO] Registering Windows Startup shortcut so the app opens after login...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0register_startup.ps1"
if errorlevel 1 (
    echo [WARN] Could not create the Startup shortcut. You can still use run.bat.
) else (
    echo [INFO] Startup shortcut created.
)

echo.
echo =======================================================================
echo [SUCCESS] Dependencies are installed.
echo Start the app with run.bat — it will also open after you sign in to Windows.
echo =======================================================================
echo.
if "!QUIET!"=="0" pause
exit /b 0
