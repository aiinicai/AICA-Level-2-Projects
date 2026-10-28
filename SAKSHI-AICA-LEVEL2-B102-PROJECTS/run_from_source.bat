@echo off
REM Runs the app from source using the build environment (run build_exe.bat once first).
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\MSMEVerificationSystem\venv\Scripts\python.exe"
if not exist "%PY%" (
    echo Build environment not found - run build_exe.bat first.
    pause
    exit /b 1
)
"%PY%" msme_app.py
if errorlevel 1 pause
