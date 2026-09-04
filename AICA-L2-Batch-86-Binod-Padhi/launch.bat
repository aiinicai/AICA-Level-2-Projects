@echo off
title India Property Rent & Valuation Analyzer
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found.
    echo Please run run_app.bat first to set up the application.
    echo.
    pause
    exit /b 1
)

call "venv\Scripts\activate.bat"
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] The application exited with an error. See the messages above.
    pause
)
