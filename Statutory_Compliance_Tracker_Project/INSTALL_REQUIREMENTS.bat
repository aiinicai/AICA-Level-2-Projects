@echo off
title Install Tracker Requirements
cd /d "%~dp0"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
echo.
echo Installation complete. Now double-click START_TRACKER.bat
pause
