@echo off
title BizCard UAE - Complete System Launcher
echo ========================================================
echo        BizCard UAE - Complete System Launcher
echo ========================================================
echo.
cd /d "%~dp0"
echo 1. Starting Backend & Vision API Server in background...
start "" cmd /k call "%~dp0start_backend.bat"

echo 2. Waiting 3 seconds for server initialization...
timeout /t 3 /nobreak >nul

echo 3. Launching Mobile Field App...
start "" "http://127.0.0.1:8000/mobile/"

echo 4. Launching Desktop Application...
start "" cmd /c call "%~dp0start_desktop.bat"

echo.
echo ========================================================
echo All services launched!
echo - Mobile Field App:      http://127.0.0.1:8000/mobile/
echo - Desktop Web Portal:    http://127.0.0.1:8000/desktop/
echo - Backend API Docs:      http://127.0.0.1:8000/docs
echo ========================================================
