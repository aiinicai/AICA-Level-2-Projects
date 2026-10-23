@echo off
REM Starts the app on this computer only. No data is uploaded to a cloud service.
cd /d "%~dp0"
py -3.11 -m streamlit run app.py
if errorlevel 1 (
  echo.
  echo The app could not start. Please see the instructions in README.md.
  pause
)
