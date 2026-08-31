@echo off
REM ============================================================
REM  Tally Converter - First-Time Setup
REM  Double-click this ONCE before using start_app.bat.
REM  Re-run it only if you receive updated code from the developer.
REM  Requires: Python 3.12 and Node.js already installed
REM  (see INSTALLATION.md for download links).
REM ============================================================

echo ============================================================
echo  Tally Converter - First-Time Setup
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found. Install Python 3.12 from
    echo        https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe
    echo        and check "Add python.exe to PATH" during install.
    pause
    exit /b 1
)

py -3.12 --version >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python 3.12 specifically was not found ^(you may have a
    echo        different version installed^). Install it from
    echo        https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo ERROR: Node.js was not found. Install it from https://nodejs.org/
    pause
    exit /b 1
)

echo [1/3] Building frontend...
cd /d "%~dp0frontend"
call npm install
if errorlevel 1 (
    echo.
    echo ERROR: npm install failed. See the error above.
    pause
    exit /b 1
)
call npm run build
if errorlevel 1 (
    echo.
    echo ERROR: npm run build failed. See the error above.
    pause
    exit /b 1
)
echo Frontend build complete.
echo.

echo [2/3] Setting up Python environment...
cd /d "%~dp0backend"
if not exist venv (
    py -3.12 -m venv venv
)
call venv\Scripts\activate.bat
echo.

echo [3/3] Installing Python requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. See the error above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Setup complete! Double-click start_app.bat to launch the app.
echo ============================================================
pause
