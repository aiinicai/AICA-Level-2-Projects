@echo off
REM ============================================================
REM  DISCOM Audit Data Compiler — Launcher
REM  For team members who received the .exe (not the source code).
REM  Double-click this file to start the app.
REM ============================================================

setlocal
cd /d "%~dp0"

if not exist "DISCOM_Audit_Compiler.exe" (
    echo.
    echo ERROR: DISCOM_Audit_Compiler.exe was not found in this folder.
    echo Please make sure this launcher is in the same folder as the .exe file.
    echo.
    pause
    exit /b 1
)

echo Starting DISCOM Audit Data Compiler...
start "" "DISCOM_Audit_Compiler.exe"
