@echo off
title Maropost India - Cash Requirements Dashboard
echo ===================================================
echo   Starting Maropost India Financial Dashboard...
echo ===================================================

cd /d "%~dp0"

:: Check if node_modules exists, install if missing
if not exist "node_modules\" (
    echo Installing required packages...
    call npm install
)

:: Start local server and open in default browser
echo Launching application on http://localhost:3000
start "" http://localhost:3000
call npm run dev
pause
