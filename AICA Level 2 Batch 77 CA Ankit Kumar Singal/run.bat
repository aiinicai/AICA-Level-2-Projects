@echo off
title GST Notice Tracker
color 0A

echo ============================================================
echo   GST Notice Tracker - Excel-First Workflow
echo ============================================================
echo.

echo [1/3] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

echo [2/3] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo Dependencies installed successfully.
echo.

echo [3/3] Freeing port 8501 if already in use...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8501"') do (
    echo     Stopping process on port 8501 PID=%%a
    taskkill /PID %%a /F >nul 2>&1
)
echo Port 8501 ready.
echo.

echo Launching GST Notice Tracker...
echo The app will open at: http://localhost:8501
echo Press Ctrl+C in this window to stop the server.
echo.
streamlit run app.py --server.headless false --server.port 8501

pause
