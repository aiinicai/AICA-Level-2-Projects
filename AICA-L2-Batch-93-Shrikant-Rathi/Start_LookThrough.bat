@echo off
setlocal
title LookThrough Data Bridge
cd /d "%~dp0"
echo.
echo  LookThrough Data Bridge
echo  -----------------------

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo  Python was not found. Install Python 3.11 or later from python.org and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo  First run: creating a private Python environment in .venv ...
  %PY% -m venv .venv
  if errorlevel 1 ( echo  Could not create the environment. & pause & exit /b 1 )
)

rem a later version may need new packages (e.g. pypdf for contract notes): reinstall when one is missing
".venv\Scripts\python.exe" -c "import pypdf, cryptography" >nul 2>nul || if exist ".venv\installed.flag" del ".venv\installed.flag"
if not exist ".venv\installed.flag" (
  echo  Installing packages: yfinance, pandas, openpyxl, xlrd  ^(one time, 1-3 minutes^) ...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
  if not exist logs mkdir logs
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt > logs\setup.log 2>&1
  if errorlevel 1 (
    powershell -NoProfile -Command "Get-Content logs\setup.log -Tail 25"
    echo.
    echo  Package installation failed. The full log is in logs\setup.log
    pause & exit /b 1
  )
  echo ok> ".venv\installed.flag"
)

echo  Starting. Your browser will open at http://localhost:8765  (keep this window open while you use the app)
".venv\Scripts\python.exe" bridge\lookthrough_bridge.py serve
echo.
echo  The bridge has stopped.
pause
