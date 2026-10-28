@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
py -3.13 --version >nul 2>&1
if not errorlevel 1 (
  py -3.13 -m venv .venv
) else (
  py -3 -m venv .venv
)
if errorlevel 1 (
  echo ERROR: Install Python 3.13 or a compatible Python 3 version from python.org.
  pause
  exit /b 1
)
:install
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "from core import init; init(); print('Database and storage initialised.')"
if errorlevel 1 goto failed
echo Setup complete. Double-click run_app.bat to start AuditFile CA.
pause
exit /b 0
:failed
echo Setup failed. Read the error messages above.
pause
exit /b 1
