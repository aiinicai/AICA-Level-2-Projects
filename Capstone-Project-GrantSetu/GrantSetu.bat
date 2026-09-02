@echo off
title GrantSetu - Indian NGO Grant Management ERP
cls
echo ======================================================================
echo             GrantSetu - NGO Grant Management ERP System
echo ======================================================================
echo.
echo  Starting local desktop application for GrantSetu...
echo.

cd /d "%~dp0"

IF NOT EXIST "node_modules" (
    echo [INFO] First-time setup detected. Installing dependencies...
    cmd /c npm install
    echo.
)

echo [INFO] Launching GrantSetu server at http://localhost:5173 ...
echo [INFO] Opening your web browser...
echo.

start http://localhost:5173

cmd /c npm run dev

pause
