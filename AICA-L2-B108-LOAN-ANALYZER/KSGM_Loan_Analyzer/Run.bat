@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  call Install_and_Run.bat
  exit /b
)
.venv\Scripts\python.exe app.py
if errorlevel 1 pause
