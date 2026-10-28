@echo off
echo ============================================================================
echo   TaxShield CA - Standalone Windows .EXE Compiler (PyInstaller)
echo ============================================================================
echo.
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python 3.9+ from python.org
    pause
    exit /b 1
)
echo [1/3] Installing PyInstaller...
pip install --upgrade pyinstaller
echo.
echo [2/3] Compiling taxshield_ca_desktop.py into single-file Windows Executable (.exe)...
pyinstaller --noconfirm --onefile --windowed --name "TaxShield_CA_Depreciation_Suite" taxshield_ca_desktop.py
echo.
echo [3/3] Build Complete!
echo Your standalone Windows .exe file is ready at:
echo     dist\TaxShield_CA_Depreciation_Suite.exe
echo.
pause
