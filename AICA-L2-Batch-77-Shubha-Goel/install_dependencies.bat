@echo off
title HDFC Bank Statement Analyzer - Install Dependencies
cd /d "%~dp0"

echo ================================================
echo   HDFC Bank Statement Analyzer
echo   Dependency Installation
echo ================================================
echo.

python --version
if errorlevel 1 (
    echo ERROR: Python was not found in PATH.
    echo Please install Python 3.11+ and enable Add Python to PATH.
    pause
    exit /b 1
)

echo.
echo Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo ERROR: Could not create virtual environment.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing required packages...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo ================================================
echo Installation completed.
echo ================================================
pause
