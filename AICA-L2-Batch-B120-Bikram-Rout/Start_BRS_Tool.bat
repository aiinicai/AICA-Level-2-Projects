@echo off
title BRS Tool - Enterprise Bank Reconciliation
cd /d "%~dp0"
echo ======================================================================
echo           Starting BRS Tool - Bank Reconciliation System
echo ======================================================================
echo.

REM --- 1. Prefer the source code when it is present (always the latest fixed version) ---
IF EXIST "main.py" IF EXIST "backend\api.py" GOTO RUN_SOURCE

REM --- 2. Otherwise use a compiled executable ---
IF EXIST "BRS_Tool.exe" (
    echo Launching compiled executable BRS_Tool.exe...
    BRS_Tool.exe
    GOTO END
)
IF EXIST "dist\BRS_Tool.exe" (
    echo Launching compiled executable dist\BRS_Tool.exe...
    dist\BRS_Tool.exe
    GOTO END
)
echo ERROR: Neither main.py nor BRS_Tool.exe was found in this folder.
GOTO END

:RUN_SOURCE
REM Find Python: try the "py" launcher first, then "python"
SET "PYCMD="
py -3 --version >nul 2>&1 && SET "PYCMD=py -3"
IF NOT DEFINED PYCMD (
    python --version >nul 2>&1 && SET "PYCMD=python"
)
IF NOT DEFINED PYCMD (
    echo ERROR: Python was not found on this computer.
    echo Install Python 3.10 or newer from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during setup, then run this file again.
    GOTO END
)

REM Install required packages if any are missing
%PYCMD% -c "import fastapi, uvicorn, pandas, openpyxl, reportlab, multipart" >nul 2>&1
IF ERRORLEVEL 1 (
    echo Installing required Python packages ^(first run only^)...
    %PYCMD% -m pip install -r requirements.txt
    IF ERRORLEVEL 1 (
        echo.
        echo ERROR: Package installation failed. Check your internet connection and try again.
        GOTO END
    )
)

echo Launching BRS Tool from source ^(main.py^)...
%PYCMD% main.py

:END
echo.
pause
