@echo off
title Quarterly Billing & Invoice Automation System
cd /d "%~dp0"

echo ============================================================
echo   Quarterly Billing and Invoice Automation System
echo ============================================================
echo.
echo Starting the app server (frontend + mail server)...
echo (A separate window will open showing server logs - you can
echo  minimize it, just don't close it while using the app.)
echo.

start "Billing App Server" cmd /k "npm run dev:all"

echo Waiting for the server to start...
timeout /t 6 /nobreak >nul

echo Opening the app in your browser...
start "" "http://localhost:3000"

exit
