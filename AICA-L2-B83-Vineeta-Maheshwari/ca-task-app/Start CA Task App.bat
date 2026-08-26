@echo off
title CA Task App - Launcher
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo.
  echo  ============================================================
  echo   Node.js was not found on this computer.
  echo.
  echo   Please install it first:
  echo     1. Go to https://nodejs.org
  echo     2. Download and install the LTS version
  echo     3. Run this launcher again
  echo  ============================================================
  echo.
  pause
  exit /b 1
)

echo.
echo  Starting the CA Task Delegation App...
echo  (A small "CA Task App Server" window will open and stay running.
echo   Keep it open while your team is using the app. Closing it stops
echo   the app for everyone.)
echo.

start "CA Task App Server - keep this window open" /min cmd /k "node server.js"

timeout /t 2 /nobreak >nul
start "" http://localhost:3000

exit
