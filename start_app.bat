@echo off
REM ============================================================
REM  Tally Converter - Quick Start
REM  Double-click this file to launch the app.
REM  (Run setup_first_time.bat once before using this, if you
REM   haven't already installed the Python packages.)
REM ============================================================

cd /d "%~dp0backend"

if not exist venv (
    echo.
    echo ============================================================
    echo  Setup has not been run yet.
    echo  Please run setup_first_time.bat first, then try again.
    echo ============================================================
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python run.py

pause
