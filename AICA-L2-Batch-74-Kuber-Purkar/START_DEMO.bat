@echo off
setlocal
title CMA Pro Builder - AICA Capstone Demo
cd /d "%~dp0"

echo.
echo ============================================================
echo  CMA Pro Builder - AICA Level 2 Capstone Evaluation
echo  Kuber Ranjan Purkar - ICAI Membership No. 187707
echo ============================================================
echo.

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is not installed or is not available in PATH.
  echo Install Node.js 20 or later from https://nodejs.org/
  echo Then double-click START_DEMO.bat again.
  echo.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo npm was not found. Reinstall Node.js with npm included.
  echo.
  pause
  exit /b 1
)

if not exist "node_modules\vite\bin\vite.js" (
  echo First run: installing the packages recorded in package-lock.json...
  echo This requires an internet connection and may take several minutes.
  call npm ci
  if errorlevel 1 (
    echo.
    echo Package installation failed. Review the message above and try again.
    pause
    exit /b 1
  )
)

echo Starting the application at http://localhost:41731 ...
start "CMA Pro Builder Server" cmd /k "cd /d ""%~dp0"" && npm run dev"
timeout /t 4 /nobreak >nul
start "" "http://localhost:41731"

echo.
echo The application has been opened in your browser.
echo Keep the server window open while reviewing the project.
echo Close the server window or press Ctrl+C there when finished.
echo.
pause
endlocal
