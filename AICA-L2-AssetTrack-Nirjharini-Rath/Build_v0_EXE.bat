@echo off
setlocal
title Build AssetTrack_v0.exe (Windows)
cd /d "%~dp0"

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python 3.10+ is required to build AssetTrack_v0.exe.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)

echo [1/2] Installing dependencies and PyInstaller...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -r requirements_v0.txt pyinstaller -q

echo [2/2] Compiling dist\AssetTrack_v0.exe ...
".venv\Scripts\pyinstaller.exe" --clean --noconfirm v0_assettrack.spec
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo SUCCESS! Standalone executable ready at: dist\AssetTrack_v0.exe
pause
