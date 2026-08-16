@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo The 45-Day Clock - AICA Source Build
echo ============================================================
echo.

set "PYTHON=.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [SETUP] Creating local Python virtual environment...
    py -m venv .venv
    if errorlevel 1 goto :failed
)

echo [SETUP] Installing / confirming dependencies...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :failed

"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo [CHECK] Confirming required application assets...

if not exist "app.py" (
    echo [ERROR] app.py is missing.
    goto :failed
)

if not exist "clock45.spec" (
    echo [ERROR] clock45.spec is missing.
    goto :failed
)

if not exist "assets\clock45.ico" (
    echo [ERROR] assets\clock45.ico is missing.
    echo Restore the application icon before building.
    goto :failed
)

echo.
if exist "tests\test_rules.py" (
    echo [TEST] Running statutory rule tests...
    "%PYTHON%" tests\test_rules.py
    if errorlevel 1 goto :tests_failed
)

echo.
echo [BUILD] Building Windows onedir application with PyInstaller...
"%PYTHON%" -m PyInstaller --noconfirm --clean clock45.spec
if errorlevel 1 goto :failed

if not exist "dist\The45DayClock\The45DayClock.exe" (
    echo [ERROR] Expected executable was not created.
    goto :failed
)

echo.
echo ============================================================
echo BUILD COMPLETE
echo Application:
echo dist\The45DayClock\The45DayClock.exe
echo ============================================================
echo.
echo Note:
echo This AICA build script creates the desktop application only.
echo It does not require Inno Setup and does not create a commercial
echo installer package.
echo.
exit /b 0

:tests_failed
echo.
echo [REFUSED] A test failed. The build was stopped.
exit /b 1

:failed
echo.
echo [FAILED] The build did not complete. Review the message above.
exit /b 1
