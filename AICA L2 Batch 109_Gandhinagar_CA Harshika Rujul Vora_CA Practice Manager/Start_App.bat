@echo off
REM Double-click this file to start CA Practice Manager from the source code.
cd /d "%~dp0"
echo Checking required packages (first time takes a few minutes)...
python -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo Package installation failed. Scroll up to see why, then send a screenshot.
  pause
  exit /b 1
)
echo Starting the app... keep this window open while you work.
python -m streamlit run app.py
pause
