@echo off
REM ============================================================
REM  AutoContract2Tally - one-click Windows .exe builder
REM  Double-click this file (or run it from Command Prompt) on
REM  the Windows machine you want the .exe to run on.
REM  Requires: Python 3.10+ installed and on PATH.
REM ============================================================

setlocal
cd /d "%~dp0"

echo.
echo [1/4] Creating virtual environment (.venv) ...
python -m venv .venv
if errorlevel 1 (
  echo ERROR: Python not found on PATH. Install Python 3.10+ from python.org and re-run this script.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat

echo.
echo [2/4] Installing dependencies ...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: dependency install failed. See messages above.
  pause
  exit /b 1
)

echo.
echo [3/4] Building AutoContract2Tally.exe with PyInstaller ...
pyinstaller --noconfirm --onefile --name AutoContract2Tally ^
  --add-data "templates;templates" ^
  --paths parsers --paths accounting_engine --paths automation --paths gmail_fetch ^
  --hidden-import broker_parsers ^
  --hidden-import accounting_engine ^
  --hidden-import watch_and_post ^
  --hidden-import gmail_fetcher ^
  --hidden-import googleapiclient.discovery ^
  --hidden-import google_auth_oauthlib.flow ^
  --hidden-import google.auth.transport.requests ^
  --collect-all googleapiclient ^
  app.py

if errorlevel 1 (
  echo ERROR: PyInstaller build failed. See messages above.
  pause
  exit /b 1
)

echo.
echo [4/4] Done. Your app is at: dist\AutoContract2Tally.exe
echo Copy that single file anywhere you like and double-click it to run the app.
echo.
pause
