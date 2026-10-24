@echo off
title Fixed Asset Register - Windows Launcher
cd /d "%~dp0"

where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pythonw fixed_asset_register.py
    exit /b 0
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python fixed_asset_register.py
    exit /b 0
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py fixed_asset_register.py
    exit /b 0
)

echo Python was not found in your Windows PATH.
echo Launching the standalone offline Fixed Asset Register interface in your default browser...
start "" "Fixed_Asset_Register_Standalone.html"
pause
