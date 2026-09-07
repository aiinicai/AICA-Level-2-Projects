@echo off
setlocal
title myvaluation - Start

cd /d "%~dp0"
set "ROOT=%CD%"
set "BACKEND=%ROOT%\backend"

echo.
echo ============================================================
echo                  Starting myvaluation
echo ============================================================
echo.

if not exist "%BACKEND%\venv\Scripts\python.exe" (
    echo First-run setup has not been completed.
    echo Launching Setup-and-Start-MyValuation.bat...
    call "%ROOT%\Setup-and-Start-MyValuation.bat"
    exit /b
)

if not exist "%ROOT%\node_modules" (
    echo Frontend dependencies are missing.
    echo Launching Setup-and-Start-MyValuation.bat...
    call "%ROOT%\Setup-and-Start-MyValuation.bat"
    exit /b
)

echo Starting backend...
start "myvaluation Backend" cmd /k "cd /d ""%BACKEND%"" && ""%BACKEND%\venv\Scripts\python.exe"" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak >nul

echo Starting frontend...
start "myvaluation Frontend" cmd /k "cd /d ""%ROOT%"" && npm run dev"

timeout /t 6 /nobreak >nul

start "" "http://localhost:3000"

echo myvaluation launched successfully.
timeout /t 2 /nobreak >nul
exit
