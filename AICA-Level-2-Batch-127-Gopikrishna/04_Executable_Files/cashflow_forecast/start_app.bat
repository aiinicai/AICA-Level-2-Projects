@echo off
rem Start the app hidden and open it in the browser. No console stays open: the server runs in the
rem background and writes to instance\logs\app.log. The first Admin is created in the browser.
rem For no window at all, use the "Cash Flow Forecast" shortcut (make_shortcuts.ps1 creates it).
rem Troubleshooting: run  .venv\Scripts\python.exe run.py  in a console to see the messages.
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo The virtual environment is missing. Create it once with:
  echo   py -3 -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m app.launcher
