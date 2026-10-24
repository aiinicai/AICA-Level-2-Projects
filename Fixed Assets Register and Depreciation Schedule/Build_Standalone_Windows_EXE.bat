@echo off
title Build Standalone Windows EXE - Fixed Asset Register
cd /d "%~dp0"
echo ============================================================================
echo Building Standalone Windows Executable (Fixed_Asset_Register.exe)...
echo ============================================================================
python -m pip install --upgrade pip pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name "Fixed_Asset_Register" fixed_asset_register.py
echo.
if exist "dist\Fixed_Asset_Register.exe" (
    copy /Y "dist\Fixed_Asset_Register.exe" "Fixed_Asset_Register.exe" >nul
    echo SUCCESS! Standalone executable created at:
    echo   %~dp0Fixed_Asset_Register.exe
    echo You can copy Fixed_Asset_Register.exe to any Windows PC and run it without Python installed.
) else (
    echo Build did not complete. Please ensure Python is installed and internet is connected to fetch PyInstaller.
)
pause
