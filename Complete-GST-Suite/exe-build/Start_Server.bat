@echo off
title Complete GST Suite - office server
cd /d "%~dp0"
rem Runs as a server for the whole office network. Nothing needs to be installed.
if not defined PORT set PORT=8080
set HOST=0.0.0.0
set NITRO_HOST=%HOST%
set NITRO_PORT=%PORT%
echo.
echo  Complete GST Suite is starting as an OFFICE SERVER on port %PORT%.
echo.
echo  On this computer open:   http://localhost:%PORT%
echo  Other computers in the office open one of these addresses:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
  for /f "tokens=* delims= " %%b in ("%%a") do echo      http://%%b:%PORT%
)
echo.
echo  If Windows Firewall asks, click "Allow access" for private networks.
echo  Note: each person's clients and runs are saved in their own browser.
echo  Keep this window open while people use the app. Close it to stop.
echo.
start "" cmd /c "timeout /t 3 >nul & start http://localhost:%PORT%"
"%~dp0node\node.exe" "%~dp0app\server\index.mjs"
echo.
echo The server stopped. If it said the port is in use, close the other copy or run:  set PORT=8081 ^& Start_Server.bat
pause
