@echo off
title Second hand vessel valuation : setup
setlocal
cd /d "%~dp0"

rem --- Find a REAL Python installation (ignores the Microsoft Store alias stub) ---
set PY=
py -3 --version >nul 2>nul
if not errorlevel 1 set PY=py -3

if not defined PY (
    python --version >nul 2>nul
    if not errorlevel 1 set PY=python
)

if not defined PY (
    echo.
    echo Python 3 was not found on this computer.
    echo.
    echo 1. Download Python 3.10 or newer from https://www.python.org/downloads/
    echo 2. Run the installer and TICK "Add python.exe to PATH" at the bottom.
    echo 3. Close this window and double-click install_and_run.bat again.
    echo.
    pause
    exit /b 1
)

echo Using: %PY%
echo.
echo Installing / updating the required Python libraries (PyQt5)...
%PY% -m pip install --upgrade pip
%PY% -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo.
    echo Library installation failed. Check the messages above and your internet connection.
    pause
    exit /b 1
)

echo.
echo Starting "Second hand vessel valuation"...
%PY% main.py
echo.
pause
