@echo off
title TaxCompute Pro - Direct Tax Suite Server
color 0B
cd /d "%~dp0"

echo =====================================================================
echo           TAXCOMPUTE PRO - DIRECT TAX COMPUTATION SUITE
echo       Calibrated for FY 2025-26 & FY 2026-27 (AY 2026-27 & 2027-28)
echo =====================================================================
echo.
echo [*] Initializing local application server...
echo [*] Project Directory: %~dp0
echo [*] Local URL: http://localhost:8080
echo.

:: Check if python is available
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] ERROR: Python was not found in your system PATH.
    echo Please install Python from https://www.python.org/ or enable it in PATH.
    pause
    exit /b 1
)

:: Automatically launch the default web browser
echo [*] Opening TaxCompute Pro in your default browser...
start http://localhost:8080

echo [*] Server is now RUNNING. Keep this window open while using the app.
echo [*] Press Ctrl+C in this window whenever you wish to stop the server.
echo.
echo ---------------------------------------------------------------------

:: Start Python HTTP Server on port 8080
python -m http.server 8080

pause
