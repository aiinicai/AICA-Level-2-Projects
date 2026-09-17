@echo off
setlocal enabledelayedexpansion
title myvaluation - First Run Setup and Start

cd /d "%~dp0"
set "ROOT=%CD%"
set "BACKEND=%ROOT%\backend"

echo.
echo ============================================================
echo             myvaluation - First Run Setup
echo ============================================================
echo.

REM ------------------------------------------------------------
REM Basic project checks
REM ------------------------------------------------------------
if not exist "%ROOT%\package.json" (
    echo ERROR: package.json was not found in:
    echo %ROOT%
    echo.
    echo Please keep this file in the root of the myvaluation project folder.
    pause
    exit /b 1
)

if not exist "%BACKEND%\main.py" (
    echo ERROR: backend\main.py was not found.
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM Python check
REM ------------------------------------------------------------
where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        set "PYTHON_CMD=python"
    ) else (
        echo ERROR: Python is not installed or is not available in PATH.
        echo.
        echo Please install Python 3.11 or 3.12 from python.org,
        echo then run this file again.
        pause
        exit /b 1
    )
)

REM ------------------------------------------------------------
REM Node / npm check
REM ------------------------------------------------------------
where npm >nul 2>&1
if not %errorlevel%==0 (
    echo ERROR: Node.js / npm is not installed or is not available in PATH.
    echo.
    echo Please install Node.js LTS from nodejs.org,
    echo then run this file again.
    pause
    exit /b 1
)

echo Python and Node.js detected.
echo.

REM ------------------------------------------------------------
REM Backend environment
REM ------------------------------------------------------------
if not exist "%BACKEND%\venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    %PYTHON_CMD% -m venv "%BACKEND%\venv"
    if not %errorlevel%==0 (
        echo ERROR: Could not create Python virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Python virtual environment already exists.
)

echo.
echo Installing / checking Python packages...

if exist "%BACKEND%\requirements.txt" (
    "%BACKEND%\venv\Scripts\python.exe" -m pip install --upgrade pip
    "%BACKEND%\venv\Scripts\python.exe" -m pip install -r "%BACKEND%\requirements.txt"

    if not %errorlevel%==0 (
        echo.
        echo ERROR: Python dependency installation failed.
        echo Check your internet connection and requirements.txt.
        pause
        exit /b 1
    )
) else (
    echo ERROR: backend\requirements.txt was not found.
    echo Please generate and include it before submission.
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM Frontend dependencies
REM ------------------------------------------------------------
echo.
if not exist "%ROOT%\node_modules" (
    echo Installing frontend dependencies...
    call npm install

    if not %errorlevel%==0 (
        echo.
        echo ERROR: npm install failed.
        echo Check your internet connection and package.json.
        pause
        exit /b 1
    )
) else (
    echo Frontend dependencies already exist.
)

REM ------------------------------------------------------------
REM Ensure data directory exists
REM ------------------------------------------------------------
if not exist "%BACKEND%\data" (
    mkdir "%BACKEND%\data"
)

REM ------------------------------------------------------------
REM Start servers
REM ------------------------------------------------------------
echo.
echo Starting myvaluation backend...
start "myvaluation Backend" cmd /k "cd /d ""%BACKEND%"" && ""%BACKEND%\venv\Scripts\python.exe"" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo Starting myvaluation frontend...
start "myvaluation Frontend" cmd /k "cd /d ""%ROOT%"" && npm run dev"

echo.
echo Waiting for the application to start...
timeout /t 8 /nobreak >nul

echo Opening browser...
start "" "http://localhost:3000"

echo.
echo ============================================================
echo myvaluation should now be running.
echo.
echo Frontend: http://localhost:3000
echo Backend : http://127.0.0.1:8000
echo.
echo Keep the two server windows open while using the application.
echo For future runs, use Start-MyValuation.bat.
echo ============================================================
echo.
pause
