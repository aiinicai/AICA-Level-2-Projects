@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Python environment missing. Follow the Windows setup steps in README.md first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" networth.py local
if errorlevel 1 pause
