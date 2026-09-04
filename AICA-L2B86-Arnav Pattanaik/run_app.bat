@echo off
REM ============================================================
REM  DISCOM Audit Data Compiler — Run App (Python, no exe)
REM  Quick way to launch the app for testing without building
REM  the standalone .exe. Requires setup_first_time.bat to have
REM  been run at least once.
REM ============================================================

setlocal
cd /d "%~dp0"

if not exist venv\Scripts\activate.bat (
    echo.
    echo ERROR: Virtual environment not found.
    echo Please run setup_first_time.bat first.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python main.py

if errorlevel 1 (
    echo.
    echo The app closed with an error. See the messages above.
    pause
)
