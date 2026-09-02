@echo off
title DocDeskew AI - Document Processing App
cd /d "%~dp0"
echo Launching DocDeskew AI...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application exited with error code %ERRORLEVEL%.
    pause
)
