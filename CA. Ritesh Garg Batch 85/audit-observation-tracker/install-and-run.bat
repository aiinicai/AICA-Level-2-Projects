@echo off
TITLE Audit Observation Tracker Setup ^& Runner
COLOR 0A
SETLOCAL EnableDelayedExpansion

echo ========================================================================
echo                  AUDIT OBSERVATION TRACKER
echo         CA Audit Management ^& Reporting System (Localhost)
echo ========================================================================
echo.

:: 1. Check Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please download and install Node.js from https://nodejs.org/
    echo.
    pause
    exit /b 1
)

echo [1/3] Node.js environment detected.

:: 2. Install dependencies if node_modules is missing or package-lock changed
if not exist "node_modules\" (
    echo [2/3] Installing application dependencies (this may take a minute)...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Dependency installation failed!
        pause
        exit /b 1
    )
) else (
    echo [2/3] Dependencies verified.
)

:: 3. Build frontend if dist folder is missing
if not exist "dist\" (
    echo [3/3] Building frontend assets...
    call npm run build
    if %errorlevel% neq 0 (
        echo [ERROR] Frontend build failed!
        pause
        exit /b 1
    )
) else (
    echo [3/3] Frontend bundle verified.
)

echo.
echo ========================================================================
echo  Starting SQLite database server and launching web browser...
echo  Application URL: http://localhost:3000
echo ========================================================================
echo.

node server/server.cjs

pause
