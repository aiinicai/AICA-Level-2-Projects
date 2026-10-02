@echo off
TITLE AuditVault - Internal Audit ^& Working Paper Management System
color 0B
cd /d "%~dp0"

echo =====================================================================
echo                AuditVault - SECURE AUDIT WORKSPACE
echo           "Every Engagement. Every Version. Securely Vaulted."
echo =====================================================================
echo.

:: Detect Python executable
set "PY_CMD="

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
)

if not defined PY_CMD (
    if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
)

if not defined PY_CMD (
    py --version >nul 2>&1
    if %errorlevel% equ 0 set "PY_CMD=py"
)

if not defined PY_CMD (
    python --version >nul 2>&1
    if %errorlevel% equ 0 set "PY_CMD=python"
)

if not defined PY_CMD (
    echo [ERROR] Python could not be found automatically.
    echo Please make sure Python is installed.
    pause
    exit /b 1
)

echo [OK] Using Python: %PY_CMD%
echo.

:: Prevent the browser from reconnecting to an older cached Streamlit process.
netstat -ano | findstr /R /C:":8501 .*LISTENING" >nul
if %errorlevel% equ 0 (
    echo [ERROR] Port 8501 is already being used by an older AuditVault session.
    echo Close the previous AuditVault black window or press Ctrl+C in it, then run this file again.
    pause
    exit /b 1
)

:: Confirm that matching application and authentication files are present.
"%PY_CMD%" -c "from auth import authorize_demo_device" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] app.py and auth.py do not belong to the same AuditVault version.
    echo Re-extract the complete project folder and do not copy individual files between versions.
    pause
    exit /b 1
)

echo Starting AuditVault at http://localhost:8501 ...
echo.
echo =====================================================================
echo  AuditVault is now RUNNING!
echo  Keep this black window OPEN while you use the application.
echo  To STOP the application: Press Ctrl+C in this window.
echo =====================================================================
echo.

"%PY_CMD%" -m streamlit run app.py --server.headless false

echo.
echo =====================================================================
echo  AuditVault server stopped.
echo =====================================================================
pause
