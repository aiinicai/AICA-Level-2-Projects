@echo off
setlocal EnableExtensions
title Business Valuation AI - Launcher
cd /d "%~dp0"

if not exist "Business_Valuation_AI.py" (
    echo Put Business_Valuation_AI.py in the same folder as this BAT file.
    pause & exit /b 1
)

set "VENV=%~dp0.venv"
set "VPY=%VENV%\Scripts\python.exe"
set "VPYW=%VENV%\Scripts\pythonw.exe"

rem ---------- Fast path: already set up ----------
if exist "%VENV%\setup.ok" if exist "%VPYW%" goto launch

echo ==========================================================
echo  Business Valuation AI - first-time setup (one time only)
echo ==========================================================

rem ---------- 1. Find Python 3.10+ ----------
call :findpy
if not defined PY (
    echo Python 3.10+ not found. Installing Python 3.12 with winget...
    winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%LOCALAPPDATA%\Programs\Python\Launcher;%PATH%"
    call :findpy
)
if not defined PY (
    echo.
    echo Could not install Python automatically.
    echo Install Python 3.12 from https://www.python.org/downloads/
    echo  ^(tick "Add python.exe to PATH"^), then double-click this file again.
    start "" https://www.python.org/downloads/
    pause & exit /b 1
)
echo Using: %PY%

rem ---------- 2. Private environment + dependencies ----------
if not exist "%VPY%" (
    echo Creating app environment...
    %PY% -m venv "%VENV%" || (echo Could not create environment. & pause & exit /b 1)
)
echo Installing dependencies ^(yfinance, openpyxl, reportlab^)...
"%VPY%" -m pip install --disable-pip-version-check -q --upgrade pip
"%VPY%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo Dependency install failed. Check your internet connection and run again.
    pause & exit /b 1
)
"%VPY%" -c "import tkinter, yfinance, openpyxl, reportlab" || (
    echo Verification failed. Reinstall Python from python.org with Tcl/Tk included.
    pause & exit /b 1
)
echo ok> "%VENV%\setup.ok"

rem ---------- 3. Desktop shortcut ----------
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Business Valuation AI.lnk');" ^
  "$s.TargetPath='%~f0'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%SystemRoot%\System32\imageres.dll,109'; $s.Save()" >nul 2>&1
echo Setup complete. A "Business Valuation AI" shortcut was added to your Desktop.

:launch
start "" "%VPYW%" "%~dp0Business_Valuation_AI.py"
exit /b 0

:findpy
set "PY="
for %%V in (3.15 3.14 3.13 3.12 3.11 3.10) do (
    if not defined PY ( py -%%V -c "import tkinter" >nul 2>&1 && set "PY=py -%%V" )
)
if not defined PY (
    python -c "import sys,tkinter; sys.exit(sys.version_info<(3,10))" >nul 2>&1 && set "PY=python"
)
exit /b 0
