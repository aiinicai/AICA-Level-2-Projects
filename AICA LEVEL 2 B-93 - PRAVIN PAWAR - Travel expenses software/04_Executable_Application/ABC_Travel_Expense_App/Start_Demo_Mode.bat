@echo off
title ABC Travel ^& Expense - DEMO MODE
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is not installed. Run Start_ABC_Travel_App.bat first - it installs Node.js.
  pause
  exit /b 1
)
echo Starting DEMO MODE with sample data at http://localhost:8081
echo Login: admin@abc-demo.com  /  Demo@1234
node launch.js --demo
pause
