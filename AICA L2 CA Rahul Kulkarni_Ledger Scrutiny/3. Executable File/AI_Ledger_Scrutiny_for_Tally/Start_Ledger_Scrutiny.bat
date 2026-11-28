@echo off
title AI Ledger Scrutiny for Tally
cd /d "%~dp0"
echo ============================================================
echo   AI Ledger Scrutiny for Tally  -  starting...
echo ============================================================
where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo Python is not installed. Install Python 3.10 or later from
  echo https://www.python.org/downloads/  and tick "Add Python to PATH".
  echo Then double-click this file again.
  pause
  exit /b
)
python -c "import streamlit, pandas, numpy, requests, openpyxl, sklearn" >nul 2>nul
if errorlevel 1 (
  echo Installing required libraries - first run only, please wait...
  python -m pip install -r requirements.txt
)
echo.
echo The app will open in your browser at http://localhost:8501
echo Choose "Demo data" in the sidebar to try it without Tally.
echo Keep this window open while using the app.
echo.
python -m streamlit run app.py --server.maxUploadSize 500
pause
