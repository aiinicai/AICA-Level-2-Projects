@echo off
cd /d "%~dp0"
echo Starting BharatBill Enterprise GST v2...
echo.
python main.py
if errorlevel 1 (
    echo.
    echo ERROR: Application failed to start.
    echo Please check your Python installation and dependencies.
    pause
)