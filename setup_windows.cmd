@echo off
setlocal
cd /d "%~dp0"
echo Setting up 1-Click Tax Notice Decoder...
echo Internet access is needed to download Python packages.
echo.
if exist ".venv\Scripts\python.exe" goto install
py -3 -c "import sys; sys.exit(sys.version_info < (3,11))" >nul 2>&1
if not errorlevel 1 (
  py -3 -m venv .venv
  goto checkenv
)
python -c "import sys; sys.exit(sys.version_info < (3,11))" >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 or newer was not found.
  echo Install 64-bit Python from https://www.python.org/downloads/windows/
  echo Select Add Python to PATH during installation, then run this file again.
  goto failed
)
python -m venv .venv
:checkenv
if not exist ".venv\Scripts\python.exe" goto failed
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
if not exist ".env" copy /y ".env.example" ".env" >nul
echo.
echo Setup complete. Existing API settings have been preserved.
echo Read INSTALLATION_INSTRUCTIONS.txt for API and optional OCR setup.
echo Double-click start_app.cmd to open the app.
pause
exit /b 0
:failed
echo.
echo Setup could not finish. Read the message above and INSTALLATION_INSTRUCTIONS.txt.
pause
exit /b 1
