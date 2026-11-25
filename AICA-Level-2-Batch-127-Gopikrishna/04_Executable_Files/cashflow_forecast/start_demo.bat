@echo off
rem Demo with SYNTHETIC data, kept apart from your real database (%LOCALAPPDATA%\CashFlowForecast\demo),
rem on http://localhost:8001 so it can run next to the real app. Starts hidden and opens the browser;
rem the demo sign-in details are shown on the sign-in page (on this PC only).
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo The virtual environment is missing. Create it once with:
  echo   py -3 -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m app.launcher --demo
