@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe python -m venv .venv
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --name GSTLookup --add-data "templates;templates" --collect-all playwright --exclude-module numpy --exclude-module pandas --exclude-module lxml main.py
if errorlevel 1 exit /b 1
echo Built dist\GSTLookup.exe. Chromium is downloaded separately only if fallback is required.
dist\GSTLookup.exe --smoke-test --no-browser
pause
