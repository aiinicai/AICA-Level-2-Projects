@echo off
rem Double-click to start the Vouchr demo (dummy data) and open it in your browser.
rem Keep this window open during the demo; close it to stop the app.
cd /d "%~dp0"
title Vouchr demo - keep this window open

where npm >nul 2>nul
if errorlevel 1 (
  echo Node.js is not installed on this computer. Install it from https://nodejs.org and try again.
  pause
  exit /b 1
)

if not exist node_modules (
  echo First run: installing the app's libraries. This takes a few minutes...
  call npm install
)

echo Preparing the demo version...
call npm run build:demo
if errorlevel 1 (
  echo The demo could not be prepared. See the messages above.
  pause
  exit /b 1
)

echo.
echo Vouchr demo is running at http://localhost:4173
echo Your browser opens automatically. Close this window to stop the demo.
echo.
call npm run preview -- --port 4173 --open
