@echo off
rem Accounting Assistant - first-time setup AND update (run again after unzipping a new version).
rem Uses only the official, signed Python from python.org / winget, so Smart App Control does not block it.
rem Your data and settings (in %APPDATA%\AccountingAssistant) are never touched.
setlocal
cd /d "%~dp0"
echo.
echo  Accounting Assistant - setup / update
echo  =====================================
echo.

set "PY="
py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
if not defined PY ( python -c "import sys" >nul 2>nul && set "PY=python" )
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" set PY="%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" -3

if not defined PY (
  echo  Python is not installed. Installing the official Python 3.12 for this Windows user...
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" set PY="%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" -3
  if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PY (
  echo.
  echo  Could not install Python automatically.
  echo  Install it from https://www.python.org/downloads/  ^(tick "Add python.exe to PATH"^), then run this file again.
  pause
  exit /b 1
)

echo  [1/3] Installing / updating libraries...
%PY% -m pip install --disable-pip-version-check -q --upgrade -r requirements.txt
if errorlevel 1 (
  echo  Library install failed - see the message above. Check the internet connection and run this file again.
  pause
  exit /b 1
)
echo  [2/3] Checking the setup...
%PY% tools\check_env.py
echo  [3/3] Creating the Desktop icon...
%PY% tools\make_shortcut.py
echo.
echo  Done. Start the app from the "Accounting Assistant" icon on the Desktop.
echo  (First start opens the setup wizard: Tally connection, companies, folders.)
echo.
pause
