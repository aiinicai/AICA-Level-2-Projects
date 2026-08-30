@echo off
setlocal
cd /d "%~dp0"
title Red Flag Engine — Forensic Accounting Desktop App

echo ===============================================================
echo   RED FLAG ENGINE - Forensic Accounting Desktop App
echo ===============================================================
echo.

python desktop_app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ===============================================================
    echo   The application stopped with exit code %ERRORLEVEL%.
    echo ===============================================================
    pause
)

endlocal
