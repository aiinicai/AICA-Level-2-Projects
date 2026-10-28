@echo off
REM Double-click this file to install what the tool needs (first time only) and start it.
REM Needs Python 3.9+ installed from python.org (tick "Add Python to PATH" during install).
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
  echo Python was not found. Please install it from https://www.python.org/downloads/
  echo and tick "Add Python to PATH" during installation. Then double-click this file again.
  pause
  exit /b 1
)
echo Installing required components (needs internet ONCE; the tool itself works offline)...
python -m pip install --quiet customtkinter pymupdf pillow openpyxl reportlab
if errorlevel 1 (
  echo Installation failed. Check your internet connection and try again.
  pause
  exit /b 1
)
python bankdoc_processor.py
if errorlevel 1 pause
