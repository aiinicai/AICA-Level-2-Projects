@echo off
setlocal enabledelayedexpansion
title India Property Rent & Valuation Analyzer - Setup and Run
cd /d "%~dp0"

echo ============================================================
echo  India Property Rent and Valuation Analyzer
echo  Setup and Launch
echo ============================================================
echo.

REM --- 1. Locate a Python interpreter -------------------------------------
set "PYTHON_CMD="

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 --version >nul 2>nul
    if !ERRORLEVEL!==0 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if !ERRORLEVEL!==0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [ERROR] Python was not found on this system.
    echo Please install Python 3.10 or later from https://www.python.org/downloads/
    echo During installation, make sure to check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo Using Python command: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

REM --- 2. Create a virtual environment if it doesn't exist ----------------
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment in .\venv ...
    %PYTHON_CMD% -m venv venv
    if not exist "venv\Scripts\activate.bat" (
        echo [ERROR] Failed to create the virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists. Skipping creation.
)
echo.

REM --- 3. Activate the virtual environment ---------------------------------
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate the virtual environment.
    pause
    exit /b 1
)

REM --- 4. Install / update dependencies ------------------------------------
echo Upgrading pip ...
python -m pip install --upgrade pip >nul

echo Installing required packages from requirements.txt ...
echo (this may take a few minutes the first time)
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed. Check your internet connection
    echo and the error messages above, then run this file again.
    pause
    exit /b 1
)
echo.
echo Dependencies installed successfully.
echo.

REM --- 5. Launch the application --------------------------------------------
echo Launching India Property Rent and Valuation Analyzer ...
echo.
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] The application exited with an error. See the messages above.
    pause
    exit /b 1
)

echo.
echo Application closed.
pause
endlocal
