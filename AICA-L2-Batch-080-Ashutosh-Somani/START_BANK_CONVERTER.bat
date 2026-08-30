@echo off
setlocal EnableDelayedExpansion
title Bank Statement Converter - Launcher

echo ========================================================
echo BANK STATEMENT CONVERTER
echo Version 1.0.0
echo ========================================================
echo.

:: 1. Determine project root safely
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

:: 2. Detect Python
set "PYTHON_EXE="

py -3.12 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 set "PYTHON_EXE=py -3.12"

if "%PYTHON_EXE%"=="" (
    py -3.13 --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 set "PYTHON_EXE=py -3.13"
)

if "%PYTHON_EXE%"=="" (
    python --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 set "PYTHON_EXE=python"
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python 3.12 or higher was not found.
    echo Please install Python 3.12+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: 3. Verify supported Python version (>= 3.12)
for /f "tokens=2" %%I in ('%PYTHON_EXE% -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"') do set "PY_VER=%%I"
:: A very simple string compare, assumes Python 3.12 or 3.13...
%PYTHON_EXE% -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python version must be 3.12 or higher.
    echo Detected version: %PY_VER%
    pause
    exit /b 1
)
echo [OK] Python detected: %PY_VER%

:: 4. Create virtual environment if missing
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [INFO] First time setup: Creating local Python virtual environment...
    %PYTHON_EXE% -m venv .venv
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment found.
)

:: 5. Launch python script to handle dependencies and start server
echo.
echo [INFO] Launching Bank Statement Converter...
echo.
.venv\Scripts\python.exe launcher.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application exited with an error code.
    pause
)
