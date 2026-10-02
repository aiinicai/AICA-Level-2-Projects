@echo off
title ABC Travel ^& Expense - PUBLIC MOBILE LINK
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is not installed. Run Start_ABC_Travel_App.bat first - it installs Node.js.
  pause
  exit /b 1
)
set CF=
where cloudflared >nul 2>nul && set CF=1
if exist "%ProgramFiles(x86)%\cloudflared\cloudflared.exe" set CF=1
if exist "%ProgramFiles%\cloudflared\cloudflared.exe" set CF=1
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\cloudflared.exe" set CF=1
if not defined CF (
  echo Installing Cloudflare Tunnel - free, one time only - using winget...
  winget install -e --id Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements
)
echo.
echo Starting ABC Travel app and creating a secure https link for mobile phones...
echo.
node public_link.js
pause
