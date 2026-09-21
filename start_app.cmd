@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please follow the setup steps in README.md first.
  pause
  exit /b 1
)
powershell.exe -NoProfile -File "%~dp0start_app.ps1"
if errorlevel 1 pause
