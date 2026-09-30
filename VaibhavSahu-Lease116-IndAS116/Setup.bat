@echo off
setlocal
cd /d "%~dp0"
title Lease116 setup
echo.
echo   Lease116 - one-time setup
echo   Creates a private Python environment and installs the required packages (5-15 minutes, internet needed).
echo.
set "PSARGS=%*"
if /i "%~1"=="/quiet" set "PSARGS="
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\Setup.ps1" %PSARGS%
if errorlevel 1 (
  echo.
  echo   Setup did not complete. Details: %LOCALAPPDATA%\Lease116\setup.log
  pause
  exit /b 1
)
echo.
if /i "%~1"=="/quiet" exit /b 0
pause
exit /b 0
