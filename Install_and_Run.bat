@echo off
setlocal
cd /d "%~dp0"
title Ledger Reconciliation App - Installer

echo ================================================
echo Installing Ledger Reconciliation App dependencies
echo ================================================

where py >nul 2>nul
if %errorlevel%==0 (
    set PY=py
) else (
    set PY=python
)

%PY% --version
if errorlevel 1 (
    echo Python is not installed or not available in PATH.
    echo Please install Python 3.10 or later from python.org and tick "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    %PY% -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Starting application...
python reconciliation_app.py
pause
