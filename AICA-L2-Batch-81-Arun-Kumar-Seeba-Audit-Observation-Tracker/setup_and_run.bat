@echo off
setlocal
title Audit Observation ^& Query Tracker - Quick Setup ^& Run
cd /d "%~dp0"

echo ================================================================
echo    AUDIT OBSERVATION ^& QUERY TRACKER - 1-CLICK SETUP ^& RUN
echo ================================================================
echo.

:: 1. Check if running from inside unextracted ZIP or missing manage.py
if exist "%~dp0manage.py" goto :FILES_OK

echo [ERROR] Project files were not found next to this script!
echo.
echo Common Cause:
echo If you opened this file directly from inside a ZIP folder,
echo Windows has not extracted the project files yet.
echo.
echo SOLUTION:
echo 1. Right-click the downloaded ZIP file.
echo 2. Click "Extract All..." and extract to a folder (e.g. Desktop).
echo 3. Open the extracted folder and double-click "setup_and_run.bat".
echo.
pause
exit /b 1

:FILES_OK

:: 2. Detect Python executable (try 'python', then 'py')
set PYTHON_CMD=
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python
    goto :PYTHON_FOUND
)

py -3 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=py -3
    goto :PYTHON_FOUND
)

py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=py
    goto :PYTHON_FOUND
)

:: Python not found
echo [ERROR] Python is not detected on this computer!
echo.
echo To run this application, Python 3.10+ is required:
echo 1. Download Python from: https://www.python.org/downloads/
echo 2. During installation, MUST CHECK the box:
echo    "[X] Add python.exe to PATH" (at the bottom of the installer)
echo 3. After installing, run setup_and_run.bat again.
echo.
pause
exit /b 1

:PYTHON_FOUND
echo Python found: %PYTHON_CMD%
echo.

:: 3. Install dependencies
echo [1/4] Installing / Verifying required Python packages...
%PYTHON_CMD% -m pip install -r "%~dp0requirements.txt"
echo.

:: 4. Run database migrations
echo [2/4] Initializing database schema...
%PYTHON_CMD% "%~dp0manage.py" migrate --noinput
echo.

:: 5. Seed demo data if database is fresh
echo [3/4] Ensuring demo seed data is loaded...
%PYTHON_CMD% "%~dp0manage.py" seed_demo_data
echo.

:: 6. Detect Free Port and Local Network IP
echo [4/4] Detecting network and available port...
set PORT=8000
for /f %%p in ('%PYTHON_CMD% -c "import socket; ports=[8000, 8008, 8080, 8888, 5000]; print(next((p for p in ports if socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(('127.0.0.1', p)) != 0), 8008))"') do set PORT=%%p

for /f "tokens=*" %%a in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback|vEthernet' -and $_.IPAddress -notlike '169.254*' } | Select-Object -First 1).IPAddress"') do set LOCAL_IP=%%a

if "%LOCAL_IP%"=="" set LOCAL_IP=127.0.0.1

echo.
echo ================================================================
echo   AUDIT TRACKER PORTAL ACCESSIBILITY URLs:
echo ================================================================
echo   [Local Access (This PC)]:     http://127.0.0.1:%PORT%/
echo   [Network Access (LAN/Wi-Fi)]: http://%LOCAL_IP%:%PORT%/
echo ================================================================
echo.
echo ----------------------------------------------------------------
echo   Demo Login Credentials (Password for all: Password@123)
echo     - Partner:    partner1@firm.com       (CA Rajesh Sharma)
echo     - Manager:    manager1@firm.com       (CA Amit Verma)
echo     - Senior:     senior1@firm.com        (Rohan Deshmukh)
echo     - Article:    article1@firm.com       (Vikram Malhotra)
echo     - Client CFO: cfo@apexindustries.com  (Suresh Menon)
echo     - Admin:      admin@firm.com          (System Administrator)
echo ----------------------------------------------------------------
echo.
echo Server is starting on port %PORT%. Keep this window open.
echo Press Ctrl+C in this window to stop the server.
echo.

:: Launch browser after 1 second delay
start "" "http://127.0.0.1:%PORT%/"
%PYTHON_CMD% "%~dp0manage.py" runserver 0.0.0.0:%PORT%

pause