@echo off
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if errorlevel 1 goto failed
echo Installed. Double-click Launch Net Asset Report.vbs to start without a command window.
pause
exit /b 0
:failed
echo Installation failed. Install Python 3.11 or newer for Windows with the Python launcher and Tkinter.
pause
exit /b 1
