@echo off
cd /d "%~dp0python"
pip install pyinstaller
pyinstaller --noconsole --onefile --name CTWorkpaper --add-data "..\data\sample_trial_balance.csv;data" ct_app.pyw
echo.
echo Done. Your app is in python\dist\CTWorkpaper.exe
pause
