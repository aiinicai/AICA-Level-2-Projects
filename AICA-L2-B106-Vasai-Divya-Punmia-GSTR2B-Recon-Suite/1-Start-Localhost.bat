@echo off
setlocal EnableExtensions
title GSTR-2B Recon Suite - LOCALHOST
cd /d "%~dp0"

echo ====================================================================
echo   GSTR-2B Recon Suite
echo   Mode: LOCALHOST (only this computer can open the app)
echo ====================================================================
echo.

echo [1/3] Checking Node.js...
call "%~dp0tools\setup-node.cmd"
if errorlevel 1 goto :fail
call :install_deps
if errorlevel 1 goto :fail

echo [2/3] Building the application...
call npm run build
if errorlevel 1 goto :fail

if "%PORT%"=="" set "PORT=3100"
set "HOST=127.0.0.1"
set "NODE_ENV=production"

echo.
echo [3/3] Starting app on  http://localhost:%PORT%
echo       Your browser will open automatically in a few seconds.
echo       Keep this window OPEN while using the app. Close it (or Ctrl+C) to stop.
echo.
start "" cmd /c "timeout /t 4 /nobreak >nul & start "" http://localhost:%PORT%"
node server.mjs
echo.
echo The application has stopped.
pause
exit /b 0

:install_deps
if exist "node_modules\vite\package.json" if exist "node_modules\sql.js\package.json" if exist "node_modules\xlsx\package.json" (
  echo       Dependencies already installed.
  exit /b 0
)
echo       Installing dependencies ^(first run only, needs internet, 1-3 minutes^)...
call npm install
if errorlevel 1 exit /b 1
exit /b 0

:fail
echo.
echo [FAILED] See the messages above. Fix the issue and run this file again.
pause
exit /b 1
