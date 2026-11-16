@echo off
rem =============================================================
rem Start Income Tax Return Download.bat
rem -------------------------------------------------------------
rem Double-click THIS file to run the tool on ANY Windows computer,
rem even one that has never had Python installed before.
rem
rem It is a plain batch file (not Python), so it can always run by
rem itself with no prerequisites - unlike launcher.pyw, which needs
rem a Python already on the computer just to be opened.
rem
rem What it does:
rem   1. Checks for Python 3.12. If missing, downloads the official
rem      installer from python.org and installs it silently (no
rem      windows, no prompts) - only on this very first run on this
rem      computer.
rem   2. Hands off to launcher.pyw, which does everything else:
rem      setting up the project's own venv + packages (first run
rem      only), starting the hidden automation Chrome, starting the
rem      server, and opening your browser.
rem =============================================================

setlocal

where py >nul 2>&1
if %errorlevel%==0 (
    py -3.12 --version >nul 2>&1
    if %errorlevel%==0 goto :run
)

echo Python 3.12 not found on this computer - downloading and
echo installing it now. This only happens once, and can take a
echo few minutes depending on your internet connection.
echo.

set "PY_URL=https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
set "PY_INSTALLER=%TEMP%\python-3.12.7-amd64.exe"

powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_INSTALLER%'"
if not exist "%PY_INSTALLER%" (
    echo ERROR: Could not download the Python installer. Check your
    echo internet connection and try again, or install Python 3.12
    echo yourself from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Installing Python 3.12 silently...
rem InstallAllUsers=0 avoids a Windows admin/UAC prompt; PrependPath=1
rem adds it to PATH for this user; Include_launcher=1 installs the
rem "py" launcher that this script and launcher.pyw both rely on.
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0

py -3.12 --version >nul 2>&1
if not %errorlevel%==0 (
    echo ERROR: Python install finished but "py -3.12" still isn't
    echo found. Close this window, open a NEW PowerShell/Command
    echo Prompt window ^(so it picks up the updated PATH^), and
    echo double-click this file again.
    pause
    exit /b 1
)

:run
echo Starting Income Tax Return Download Tool...

rem Find this Python's own pythonw.exe (the no-console-window
rem version) so launcher.pyw runs without a lingering black window,
rem whatever folder Python ended up installed in.
for /f "delims=" %%P in ('py -3.12 -c "import sys, os; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))"') do set "PYTHONW=%%P"

start "" "%PYTHONW%" "%~dp0launcher.pyw"
exit
