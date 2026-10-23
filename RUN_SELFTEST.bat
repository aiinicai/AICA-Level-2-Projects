@echo off
title Portfolio Analyzer - Self-test
cd /d "%~dp0"

set PY=python
%PY% --version >nul 2>&1
if errorlevel 1 set PY=py
%PY% --version >nul 2>&1
if errorlevel 1 (
  echo Python is not installed, or "Add Python to PATH" was not ticked.
  pause
  exit /b 1
)

echo Checking / installing required packages...
%PY% -m pip install -r requirements.txt --upgrade --quiet --disable-pip-version-check
echo.
%PY% portfolio_analyzer.py --selftest
