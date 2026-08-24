@echo off
title FS Builder Lite - Frontend
echo ============================================
echo  FS BUILDER LITE - Frontend Dev Server
echo ============================================
echo.

cd /d "%~dp0frontend"

:: Kill any stale Node process holding port 5173
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":5173 "') do (
    echo [INFO] Freeing port 5173 (PID %%p)...
    taskkill /PID %%p /F >nul 2>&1
)

echo [OK] Port 5173 is free.
echo [INFO] Starting Vite on http://localhost:5173 ...
echo.
echo  FRONTEND RUNNING - keep this window open
echo ============================================
echo.

npm run dev

echo.
echo [STOPPED] Frontend has exited.
pause
