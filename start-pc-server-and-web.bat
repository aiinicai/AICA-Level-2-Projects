@echo off
title INNFLOW Hotel Management - Local Launch System
echo ========================================================
echo   INNFLOW Hotel Management - Local PC Launch System
echo   1. Starting Central Backend Server (Port 11000)
echo   2. Starting Web Management Portal (Port 8081)
echo ========================================================
echo.

echo [1/2] Starting Backend API Database Server on Port 11000...
start "INNFLOW Backend Server (Port 11000)" cmd /k "pnpm.cmd dev:server"
timeout /t 4 >nul

echo [2/2] Starting Web Portal Metro Server on Port 8081...
start "INNFLOW Web Portal (Port 8081)" cmd /k "pnpm.cmd dev:metro"
timeout /t 6 >nul

echo.
echo Opening Web Portal in your browser...
start http://localhost:8081/admin

echo.
echo ========================================================
echo   INNFLOW is running locally on your PC!
echo.
echo   - Web Management Portal: http://localhost:8081/admin
echo   - Mobile Web Simulation: http://localhost:8081
echo   - Backend Database API:  http://localhost:11000/api/health
echo.
echo   Keep the two command windows open while using the app.
echo ========================================================
pause
