@echo off
title FS Builder Lite - Launcher
echo.
echo  ==========================================
echo   FS BUILDER LITE - Application Launcher
echo  ==========================================
echo.

:: ── Step 1: Start backend in a new window ──────────────────────────────────
echo [1/3] Starting Backend Server...
start "FS Builder Lite - Backend" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && echo [OK] venv activated && echo [INFO] Uvicorn starting on http://127.0.0.1:8000 ... && echo. && python -m uvicorn main:app --host 127.0.0.1 --port 8000"

:: ── Step 2: Poll until backend /health returns 200 ─────────────────────────
echo [2/3] Waiting for backend to become healthy...
set RETRIES=0
:HEALTH_LOOP
set /a RETRIES+=1
if %RETRIES% GTR 30 (
    echo [ERROR] Backend did not start in 30 seconds. Check the backend window for errors.
    pause
    exit /b 1
)
timeout /t 1 /nobreak >nul
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:8000/health 2>nul | findstr /c:"200" >nul
if errorlevel 1 (
    echo  ... waiting (%RETRIES%/30)
    goto HEALTH_LOOP
)
echo [OK] Backend is healthy!

:: ── Step 3: Kill stale node on 5173 and start frontend ─────────────────────
echo [3/3] Starting Frontend Dev Server...
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":5173 "') do (
    echo [INFO] Freeing port 5173 (PID %%p)...
    taskkill /PID %%p /F >nul 2>&1
)
start "FS Builder Lite - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

:: ── Step 4: Wait 4 seconds then open browser ───────────────────────────────
timeout /t 4 /nobreak >nul
echo [OK] Opening browser at http://localhost:5173 ...
start "" "http://localhost:5173"

echo.
echo  ==========================================
echo   FS Builder Lite is running!
echo   Frontend : http://localhost:5173
echo   Backend  : http://127.0.0.1:8000
echo   Health   : http://127.0.0.1:8000/health
echo   Login    : EMP001 / Admin@123
echo  ==========================================
echo.
pause
