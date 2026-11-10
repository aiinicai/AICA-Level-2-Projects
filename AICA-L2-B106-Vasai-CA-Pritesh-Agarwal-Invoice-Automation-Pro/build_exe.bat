@echo off
title Building CA Firm Invoice & Practice Automation Pro Desktop App
echo =====================================================================
echo  CA Firm Invoice & Practice Automation Pro - Standalone App Builder
echo =====================================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not detected in your PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)

echo [1/3] Checking and installing PyInstaller & dependencies...
python -m pip install --upgrade pip
python -m pip install pyinstaller PyQt6 reportlab openpyxl requests

echo.
echo [2/3] Compiling standalone executable (.exe)...
echo Packaging with embedded icon and hiding console window...
python -m PyInstaller --noconsole --onefile ^
    --name "CA_Firm_Invoice_Pro" ^
    --icon "app_icon.ico" ^
    --add-data "app_icon.ico;." ^
    --add-data "app_icon.png;." ^
    --hidden-import "PyQt6" ^
    --hidden-import "PyQt6.QtCore" ^
    --hidden-import "PyQt6.QtGui" ^
    --hidden-import "PyQt6.QtWidgets" ^
    --hidden-import "reportlab" ^
    --hidden-import "openpyxl" ^
    --hidden-import "requests" ^
    --clean ^
    ca_firm_invoice_automation_pro.py

if %errorlevel% equ 0 (
    echo.
    echo =====================================================================
    echo  SUCCESS! Application generated successfully!
    echo =====================================================================
    echo Your standalone application is ready at:
    echo   dist\CA_Firm_Invoice_Pro.exe
    echo.
    echo You can copy this .exe file anywhere or create a desktop shortcut!
    echo Double-click it to run the app without opening Python or CMD.
    echo.
) else (
    echo.
    echo [ERROR] Build failed. Please check the error messages above.
)

pause
