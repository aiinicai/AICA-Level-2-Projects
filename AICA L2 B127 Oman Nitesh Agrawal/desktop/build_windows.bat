@echo off
setlocal enabledelayedexpansion
echo ============================================================
echo RealEstate 360 - Windows EXE & Offline Installer Builder
echo ============================================================

cd /d "%~dp0"

echo [1/4] Verifying Python packages (PySide6, PyInstaller)...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install pyside6 pyinstaller
if errorlevel 1 (
  echo ERROR: Failed to install PySide6/PyInstaller. Ensure Python 3.11+ x64 is in PATH.
  pause
  exit /b 1
)

echo [2/4] Packaging RealEstate360.exe via PyInstaller...
if not exist "Prerequisites" mkdir "Prerequisites"
if not exist "output" mkdir "output"
python -m PyInstaller --noconfirm --clean RealEstate360.spec
if errorlevel 1 (
  echo ERROR: PyInstaller packaging failed.
  pause
  exit /b 1
)

echo [3/4] Creating RealEstate360_Portable.zip...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\RealEstate360\*' -DestinationPath 'output\RealEstate360_Portable.zip' -Force"

echo [4/4] Building RealEstate360_Setup.exe and RealEstate360_Update.exe (Inno Setup 6)...
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%ISCC%" (
  "%ISCC%" RealEstate360_Setup.iss
  "%ISCC%" RealEstate360_Update.iss
  echo SUCCESS: Built output\RealEstate360_Setup.exe, output\RealEstate360_Update.exe, output\RealEstate360_Portable.zip, and dist\RealEstate360\RealEstate360.exe
) else (
  echo WARNING: Inno Setup 6 not found at default path. RealEstate360.exe and RealEstate360_Portable.zip are ready!
  echo Download Inno Setup 6 from https://jrsoftware.org/isdl.php and run ISCC.exe RealEstate360_Setup.iss
)
pause
