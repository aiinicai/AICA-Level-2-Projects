@echo off
title Bank Statement Summariser v1.2

:: Get the folder where THIS batch file lives (handles spaces in path)
set "BAT_DIR=%~dp0"
:: Remove trailing backslash
if "%BAT_DIR:~-1%"=="\" set "BAT_DIR=%BAT_DIR:~0,-1%"

echo  Batch file location: %BAT_DIR%

:: ── Find Anaconda / Miniconda Python ─────────────────────────────────────────
set "PYTHON="

for %%P in (
    "%USERPROFILE%\anaconda3\python.exe"
    "%USERPROFILE%\Anaconda3\python.exe"
    "%USERPROFILE%\miniconda3\python.exe"
    "%USERPROFILE%\Miniconda3\python.exe"
    "C:\anaconda3\python.exe"
    "C:\Anaconda3\python.exe"
    "C:\ProgramData\Anaconda3\python.exe"
    "C:\ProgramData\anaconda3\python.exe"
    "C:\miniconda3\python.exe"
    "C:\Miniconda3\python.exe"
) do (
    if exist %%P (
        set "PYTHON=%%P"
        goto :found_python
    )
)

:: Fallback – try whatever is in PATH
where python >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON=python"
    goto :found_python
)

echo.
echo  ERROR: Python / Anaconda not found.
echo  Please install Anaconda from https://www.anaconda.com
echo.
pause
exit /b 1

:found_python
echo  Python found: %PYTHON%

:: ── Check app.py exists in same folder as this batch file ────────────────────
if not exist "%BAT_DIR%\app.py" (
    echo.
    echo  ERROR: app.py not found.
    echo  Looking in: %BAT_DIR%
    echo  Contents of that folder:
    dir "%BAT_DIR%" /b
    echo.
    echo  Please make sure this batch file is in the same folder as app.py
    echo.
    pause
    exit /b 1
)

echo  app.py found OK.

:: ── Install / check dependencies ──────────────────────────────────────────────
echo  Checking dependencies...
"%PYTHON%" -m pip install -q PyQt5 pandas openpyxl pdfplumber pypdf rapidfuzz xlrd 2>nul

:: ── Launch the app ────────────────────────────────────────────────────────────
echo  Starting Bank Statement Summariser...
echo.
cd /d "%BAT_DIR%"
"%PYTHON%" "%BAT_DIR%\app.py"

if %errorlevel% neq 0 (
    echo.
    echo  The application closed with an error.
    echo  Please check the logs\ folder inside the app folder for details.
    pause
)
