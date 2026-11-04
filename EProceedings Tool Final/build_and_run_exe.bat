@echo off
setlocal
cd /d "%~dp0"
title E-Proceedings Tool - Build and Run

rem ---- If exe already exists, just launch it
if exist "EProceedingsTool.exe" (
  if /I not "%1"=="rebuild" (
    echo Starting EProceedingsTool.exe ...
    start "" "EProceedingsTool.exe"
    exit /b 0
  )
)

python --version >nul 2>&1
if errorlevel 1 (
  echo Python is not installed. Install Python 3.10+ from python.org
  echo and tick "Add python.exe to PATH" during setup.
  pause
  exit /b 1
)

if not exist "app.py" (
  echo app.py not found in: %~dp0
  echo Keep this .bat and app.py in the same folder.
  pause
  exit /b 1
)

echo [1/3] Installing required libraries...
python -m pip install --upgrade pip
python -m pip install pandas openpyxl xlrd lxml playwright customtkinter pyinstaller
if errorlevel 1 (
  echo Library installation failed. Check your internet connection.
  pause
  exit /b 1
)

echo [2/3] Building the exe (takes a few minutes, please wait)...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name EProceedingsTool --collect-all playwright --collect-all customtkinter app.py
if errorlevel 1 (
  echo Build failed. Scroll up to see the error.
  pause
  exit /b 1
)

copy /Y "dist\EProceedingsTool.exe" "%~dp0EProceedingsTool.exe" >nul

echo [3/3] Done. Launching the tool...
start "" "%~dp0EProceedingsTool.exe"
echo.
echo Next time just double-click EProceedingsTool.exe (or this .bat).
echo To rebuild after changing app.py, run:  build_and_run_exe.bat rebuild
timeout /t 8 >nul
