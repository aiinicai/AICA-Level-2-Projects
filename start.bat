@echo off
title Lovable CRM
cd /d "%~dp0"

echo ===================================================
echo           Starting Lovable CRM...
echo ===================================================
echo.

:: Check if node is installed
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not found in PATH!
    echo Please install Node.js from https://nodejs.org/
    echo.
    pause
    exit /b 1
)

:: Run Vite dev server and automatically open browser
echo Launching local server and opening browser...
echo.
call npm.cmd run dev -- --open

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start server. Trying fallback direct runner...
    call npx.cmd vite --open
)

echo.
pause
