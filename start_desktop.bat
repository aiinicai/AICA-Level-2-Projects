@echo off
title BizCard UAE - Windows Desktop Application
echo ========================================================
echo        BizCard UAE - Windows Desktop Application
echo ========================================================
echo.
cd /d "%~dp0"
if exist "dist\BizCardUAE\BizCardUAE.exe" (
    echo Launching compiled Windows Executable: dist\BizCardUAE\BizCardUAE.exe ...
    start "" "dist\BizCardUAE\BizCardUAE.exe"
) else (
    echo Launching Python PyQt6 Desktop Application...
    python desktop_app\main_desktop.py
)
