@echo off
setlocal
cd /d "%~dp0"
title MSME Payables Compliance Tracker

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.10+ from python.org ^(tick "Add Python to PATH"^), then run this again.
  pause
  exit /b 1
)

python -c "import streamlit, pandas, openpyxl, xlrd, pdfplumber, altair" >nul 2>nul
if errorlevel 1 (
  echo Installing required packages ^(first run only, needs internet^)...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Package install failed. Check your internet connection and try again.
    pause
    exit /b 1
  )
)

echo Starting the MSME Tracker - your browser will open. Close this window to stop the app.
python -m streamlit run app.py
pause
