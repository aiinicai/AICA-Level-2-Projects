@echo off
setlocal EnableExtensions EnableDelayedExpansion
title GSTR-2B Recon Suite - SERVER HOST (network)
cd /d "%~dp0"

echo ====================================================================
echo   GSTR-2B Recon Suite
echo   Mode: SERVER HOST (other computers on your network can use the app)
echo ====================================================================
echo.

echo [1/4] Checking Node.js...
call "%~dp0tools\setup-node.cmd"
if errorlevel 1 goto :fail
call :install_deps
if errorlevel 1 goto :fail

echo [2/4] Building the application for production...
call npm run build
if errorlevel 1 goto :fail

if "%PORT%"=="" set "PORT=3100"
if "%HTTPS_PORT%"=="" set "HTTPS_PORT=3443"
set "HOST=0.0.0.0"
set "NODE_ENV=production"
rem https lets phones and tablets install the app (Add to Home Screen / Install app)
set "HTTPS=1"

echo.
echo [3/4] Allowing ports %PORT% and %HTTPS_PORT% through Windows Firewall...
call :firewall %PORT%
call :firewall %HTTPS_PORT%

echo.
echo [4/4] Starting server...
echo.
echo   SHARE ONE OF THESE LINKS with people on your network ^(same Wi-Fi / LAN^):
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R /C:"IPv4"') do (
  set "IP=%%a"
  set "IP=!IP: =!"
  echo      https://!IP!:%HTTPS_PORT%     ^(installable on phones / tablets^)
  echo      http://!IP!:%PORT%
)
echo      http://%COMPUTERNAME%:%PORT%
echo.
echo   First time on a phone / tablet: open  http://^<link above^>:%PORT%/install
echo   and follow the steps to trust this computer, then use the https link.
echo.
echo   On this computer:  http://localhost:%PORT%
echo   Keep this window OPEN while others use the app. Close it (or Ctrl+C) to stop.
echo.
start "" cmd /c "timeout /t 4 /nobreak >nul & start "" http://localhost:%PORT%"
node server.mjs
echo.
echo The server has stopped.
pause
exit /b 0

:firewall
netsh advfirewall firewall show rule name="GSTR-2B Recon Suite (TCP %1)" >nul 2>nul
if not errorlevel 1 (
  echo       Firewall rule for port %1 already present.
  exit /b 0
)
netsh advfirewall firewall add rule name="GSTR-2B Recon Suite (TCP %1)" dir=in action=allow protocol=TCP localport=%1 profile=private,domain >nul 2>nul
if errorlevel 1 (
  echo       [NOTE] Could not add the firewall rule for port %1 ^(needs Administrator^).
  echo              If other devices cannot connect, right-click this file and
  echo              choose "Run as administrator" once, or allow Node.js when Windows asks.
) else (
  echo       Firewall rule for port %1 added.
)
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
