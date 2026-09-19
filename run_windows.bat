@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py
) else (
  python app.py
)
if errorlevel 1 (
  echo.
  echo Check Python with Tcl/Tk is installed and install requirements.txt.
  pause
)
