@echo off
cd /d "%~dp0"
python --version
if errorlevel 1 goto failed
if not exist .venv\Scripts\python.exe python -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m ensurepip --upgrade
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Installation complete. Double-click run.bat.
pause
exit /b 0
:failed
echo Installation failed. Install Python with tkinter and Add Python to PATH enabled, then retry.
pause
exit /b 1
