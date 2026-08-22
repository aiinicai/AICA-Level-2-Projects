@echo off
setlocal
cd /d %~dp0
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js 22+ is required. Install Node.js from https://nodejs.org/
  pause
  exit /b 1
)
if not exist node_modules (
  echo Installing dependencies...
  call npm install
  if errorlevel 1 exit /b 1
)
start "Litigation Tracker API" cmd /k "node server/server.js"
start "Litigation Tracker Frontend" cmd /k "npm run client"
timeout /t 3 >nul
start http://localhost:5173
