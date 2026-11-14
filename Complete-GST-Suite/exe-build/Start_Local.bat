@echo off
title Complete GST Suite - this computer only
cd /d "%~dp0"
rem Runs only on this computer (localhost). Nothing needs to be installed.
if not defined PORT set PORT=8080
set HOST=127.0.0.1
set NITRO_HOST=%HOST%
set NITRO_PORT=%PORT%
echo.
echo  Complete GST Suite is starting on THIS computer only...
echo  Open:  http://localhost:%PORT%
echo.
echo  Keep this window open while you use the app. Close it to stop.
echo.
start "" cmd /c "timeout /t 3 >nul & start http://localhost:%PORT%"
"%~dp0node\node.exe" "%~dp0app\server\index.mjs"
echo.
echo The server stopped. If it said the port is in use, close the other copy or run:  set PORT=8081 ^& Start_Local.bat
pause
