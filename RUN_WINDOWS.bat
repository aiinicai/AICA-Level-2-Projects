@echo off
title Equity Portfolio Report - SV Arka Advisors
cd /d "%~dp0"

set PY=python
%PY% --version >nul 2>&1
if errorlevel 1 set PY=py
%PY% --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python is not installed, or "Add Python to PATH" was not ticked.
  echo Please install Python from https://www.python.org/downloads/ and run again.
  echo.
  pause
  exit /b 1
)

echo Checking / installing required packages (first run takes a few minutes)...
%PY% -m pip install -r requirements.txt --upgrade --quiet --disable-pip-version-check
echo.

if "%~1"=="" (
  %PY% portfolio_analyzer.py
) else (
  %PY% portfolio_analyzer.py "%~1"
)
