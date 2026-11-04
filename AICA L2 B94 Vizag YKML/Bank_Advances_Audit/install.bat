@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m ensurepip --upgrade
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Installation complete. Double-click run.bat.
pause
exit /b 0
:fail
echo Installation failed. Copy the error shown above for troubleshooting.
pause
exit /b 1
