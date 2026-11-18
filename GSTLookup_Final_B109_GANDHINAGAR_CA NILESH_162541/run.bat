@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
 echo Python 3.10 or newer is required. Install it for your user account from python.org.
 pause
 exit /b 1
)
if not exist .venv\Scripts\python.exe python -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe main.py %*
if errorlevel 1 goto failed
exit /b 0
:failed
echo Setup or launch failed. Check Internet, Python version and proxy settings; see README.md.
pause
exit /b 1
