@echo off
title CA Docs - launcher
cd /d "%~dp0backend"

if not exist "dist\server.js" (
    echo CA Docs has not been set up yet.
    echo Please run setup.bat first.
    echo.
    pause
    exit /b 1
)

echo Starting CA Docs...
start "CA Docs - server (do not close this window while using CA Docs)" cmd /k "node dist\server.js"

echo Waiting for it to be ready...
timeout /t 4 /nobreak >nul

start "" http://localhost:4000

echo.
echo CA Docs should now be open in your browser at http://localhost:4000
echo A second window titled "CA Docs - server" is now running the application -
echo keep that window open for as long as you want to use CA Docs.
echo.
echo This window can be closed.
pause
