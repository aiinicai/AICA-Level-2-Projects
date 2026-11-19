@echo off
title GST Automation - Invoice PDFs to GSTR-1 JSON
cd /d "%~dp0"

echo.
echo   ==================================================
echo     GST AUTOMATION  -  Invoice PDFs to GSTR-1 JSON
echo   ==================================================
echo.

REM ---- find Python -------------------------------------------------------
set PYTHON=
where py >nul 2>&1 && set PYTHON=py
if "%PYTHON%"=="" (where python >nul 2>&1 && set PYTHON=python)
if "%PYTHON%"=="" (
  echo   Python was not found on this PC.
  echo.
  echo   Install it from https://www.python.org/downloads/
  echo   and tick "Add Python to PATH" during setup.
  echo   Then double-click this file again.
  echo.
  pause
  exit /b 1
)

REM ---- install the two libraries the first time only ---------------------
%PYTHON% -c "import pdfplumber, openpyxl" >nul 2>&1
if errorlevel 1 (
  echo   First run - installing pdfplumber and openpyxl. Once only.
  echo.
  %PYTHON% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo   Setup failed. Check the internet connection and try again.
    echo.
    pause
    exit /b 1
  )
  echo.
)

REM ---- run both steps ----------------------------------------------------
%PYTHON% run_gst_automation.py %*

echo.
pause
