@echo off
cd /d "%~dp0"
echo ==== GURU GST Downloader - one-time setup ====
python --version || (echo Python not found. Install Python 3.10+ from python.org and tick "Add python.exe to PATH". & pause & exit /b)
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo Installing browser engine (Chrome or Edge is used if installed)...
python -m playwright install chromium
echo.
echo Setup complete. Double-click run.bat to start.
pause
