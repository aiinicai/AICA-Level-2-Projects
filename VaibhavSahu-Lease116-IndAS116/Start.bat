@echo off
setlocal
cd /d "%~dp0"
set "VPY=%LOCALAPPDATA%\Lease116\venv\Scripts\python.exe"
if not exist "%VPY%" (
  echo   Lease116 is not set up on this PC yet - running Setup first...
  call "%~dp0Setup.bat" /quiet
  if errorlevel 1 exit /b 1
)
title Lease116 - Ind AS 116 lease accounting (close this window to stop the app)
"%VPY%" -m app
if errorlevel 1 pause
