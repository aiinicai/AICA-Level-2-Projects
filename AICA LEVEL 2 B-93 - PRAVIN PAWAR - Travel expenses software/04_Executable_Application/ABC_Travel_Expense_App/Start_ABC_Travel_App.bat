@echo off
title ABC Private Limited - Travel ^& Expense App
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Node.js is not installed on this computer.
  echo  Installing Node.js LTS using winget - needs internet and may ask for permission...
  echo.
  winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
  if errorlevel 1 (
    echo.
    echo  Automatic install failed. Please install Node.js LTS from https://nodejs.org and run this file again.
    pause
    exit /b 1
  )
  echo  Node.js installed. Please close this window and double-click Start_ABC_Travel_App.bat again.
  pause
  exit /b 0
)
echo Starting ABC Travel ^& Expense... your browser will open at http://localhost:8080
echo Keep this window open while using the app. Close it to stop the server.
node launch.js
pause
