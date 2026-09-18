@echo off
setlocal
title Audit Observation ^& Query Tracker - Network Server
cd /d "%~dp0"

echo ================================================================
echo    AUDIT OBSERVATION ^& QUERY TRACKER - CA FIRM PORTAL
echo ================================================================
echo.

:: 1. Check if manage.py exists
if exist "%~dp0manage.py" goto :FILES_OK
echo [ERROR] Project files were not found next to this script!
echo If you downloaded a ZIP file, please make sure you right-clicked
echo the ZIP and selected "Extract All..." before running this.
pause
exit /b 1

:FILES_OK

:: 2. Detect Python executable
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

echo [ERROR] Python is not installed or not found in PATH.
echo Please install Python 3.10+ from https://www.python.org/
echo (Check the box "Add Python to PATH" during installation).
pause
exit /b 1

:PYTHON_FOUND

echo [1/3] Checking database migrations...
%PYTHON_CMD% "%~dp0manage.py" migrate --noinput

echo.
echo [2/3] Detecting available port and network IP...
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
echo [3/3] Opening web browser at http://127.0.0.1:%PORT%/ ...
start "" "http://127.0.0.1:%PORT%/"

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
echo Starting server on 0.0.0.0:%PORT% (accessible across LAN/Wi-Fi)...
echo Press Ctrl+C in this window to stop the server.
echo.

%PYTHON_CMD% "%~dp0manage.py" runserver 0.0.0.0:%PORT%

pause