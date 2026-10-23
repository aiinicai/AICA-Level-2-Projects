@echo off
title TickTrail
cd /d "%~dp0"
where node >nul 2>nul || (echo Node.js is not installed. Install the LTS version from https://nodejs.org and try again. & pause & exit /b 1)
echo Starting TickTrail. Leave this window open while you use it; close it to stop.
echo.
start "" "http://localhost:8080"
node --disable-warning=ExperimentalWarning server.js
pause
