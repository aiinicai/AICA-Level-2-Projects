@echo off
title FS Builder Lite - Backend
echo ============================================
echo  FS BUILDER LITE - Backend Server (API)
echo ============================================
echo.

cd /d "%~dp0backend"

if not exist venv\Scripts\activate.bat (
    echo [ERROR] venv not found. Run: python -m venv venv ^&^& venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
echo [OK] Virtual environment activated.
echo [INFO] Starting Uvicorn on http://127.0.0.1:8000 ...
echo.
echo  BACKEND RUNNING - keep this window open
echo ============================================
echo.

python -m uvicorn main:app --host 127.0.0.1 --port 8000

echo.
echo [STOPPED] Backend has exited.
pause
