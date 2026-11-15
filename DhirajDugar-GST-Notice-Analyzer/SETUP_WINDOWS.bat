@echo off
setlocal
cd /d "%~dp0"
echo GST Notice Analyzer - one-time setup
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 -m venv .venv
if errorlevel 1 goto failed
goto install
:usepython
python -m venv .venv
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Setup complete. Double-click RUN_WINDOWS.bat to open the app.
pause
exit /b 0
:failed
echo.
echo Setup failed. Check internet access and install 64-bit Python 3.11.
echo See README.md for manual setup instructions.
pause
exit /b 1
