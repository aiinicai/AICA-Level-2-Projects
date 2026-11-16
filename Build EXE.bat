@echo off
cd /d "%~dp0"
python -m venv .buildenv
if errorlevel 1 goto :failed
".buildenv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :failed
".buildenv\Scripts\python.exe" -m PyInstaller --noconfirm "Smart Billing Manager.spec"
if errorlevel 1 goto :failed
echo Build ready: dist\Smart Billing Manager.exe
pause
exit /b 0
:failed
echo Build failed. Install Python 3.10 or newer with pip and PATH enabled.
pause
exit /b 1
