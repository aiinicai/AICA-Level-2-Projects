@echo off
title Imprest and Settlement App
cd /d "%~dp0"

if not exist node_modules (
  echo First-time setup - installing dependencies, this can take a minute...
  call npm install
  if errorlevel 1 (
    echo.
    echo npm install failed. Make sure Node.js is installed, then try again.
    pause
    exit /b 1
  )
)

echo Starting the Imprest and Settlement app...
echo.
echo IMPORTANT: Keep this window open. Closing it stops the app for everyone.
echo.
call npm start

echo.
echo The app has stopped. Press any key to close this window.
pause >nul
