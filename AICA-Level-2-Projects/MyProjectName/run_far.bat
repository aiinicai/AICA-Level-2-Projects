@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Fixed Asset Register

rem =====================================================================
rem  Fixed Asset Register - one-click launcher
rem
rem  Double-click this file to start the app. The first run takes a
rem  little longer (it sets everything up); every run after that is fast.
rem
rem  This starts a real server on your computer that other people on the
rem  SAME OFFICE NETWORK can also open in their own browser - see the
rem  addresses printed below once it starts. Anyone outside your network
rem  (e.g. over the internet) cannot reach it.
rem
rem  To change the port this runs on, edit the PORT value just below.
rem =====================================================================

set PORT=8000
cd /d "%~dp0"

echo.
echo  Fixed Asset Register
echo  =====================================================================
echo.

rem --- 1) Find a Python launcher -----------------------------------------
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set PYLAUNCHER=python
) else (
    where py >nul 2>nul
    if %ERRORLEVEL%==0 (
        set PYLAUNCHER=py
    ) else (
        echo  [ERROR] Python was not found on this computer.
        echo  Install Python from https://www.python.org/downloads/ ^(tick
        echo  "Add python.exe to PATH" during setup^), then double-click this
        echo  file again.
        echo.
        pause
        exit /b 1
    )
)

rem --- 2) Create the virtual environment the first time only ------------
if not exist "venv\Scripts\activate.bat" (
    echo  First-time setup - this can take a few minutes, please wait...
    echo.
    %PYLAUNCHER% -m venv venv
    if not exist "venv\Scripts\activate.bat" (
        echo  [ERROR] Could not create the Python virtual environment.
        pause
        exit /b 1
    )
)

call "venv\Scripts\activate.bat"

rem --- 3) Make sure all required packages are installed ------------------
echo  Checking required packages...
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
if not %ERRORLEVEL%==0 (
    echo  [ERROR] Could not install the required packages. Check your
    echo  internet connection and try again.
    pause
    exit /b 1
)

rem --- 4) Apply any pending database updates -----------------------------
echo  Checking the database...
python manage.py migrate --noinput
if not %ERRORLEVEL%==0 (
    echo  [ERROR] Database update failed - see the message above.
    pause
    exit /b 1
)

rem --- 5) Refresh the app's stylesheets/icons -----------------------------
python manage.py collectstatic --noinput >nul

rem --- 6) Work out this computer's address on the network -----------------
set LAN_IP=
set "LAN_IP_FILE=%TEMP%\far_lan_ip.txt"
python get_lan_ip.py > "%LAN_IP_FILE%" 2>nul
if exist "%LAN_IP_FILE%" (
    set /p LAN_IP=<"%LAN_IP_FILE%"
    del "%LAN_IP_FILE%" >nul 2>nul
)

if "%LAN_IP%"=="" (
    echo  [Note] Could not detect a network address - other computers may
    echo  not be able to reach this app until you connect this PC to your
    echo  office network. It will still work on this computer.
    set LAN_IP=127.0.0.1
)

rem QR codes need a URL other devices can actually open, so point them at
rem this computer's network address, detected fresh on every start.
set FAR_QR_BASE_URL=http://%LAN_IP%:%PORT%

echo.
echo  =====================================================================
echo   Starting the Fixed Asset Register server...
echo.
echo   On this computer:            http://localhost:%PORT%/
echo   For others on this network:  http://%LAN_IP%:%PORT%/
echo.
echo   Share the second address with colleagues so they can use the app
echo   from their own computers at the same time.
echo.
echo   If Windows Firewall asks for permission just now, click
echo   "Allow access" so colleagues on the network can connect.
echo.
echo   Keep this window open while the app is in use.
echo   Close this window (or press Ctrl+C) to stop the server.
echo  =====================================================================
echo.

rem --- 7) Open this computer's own browser automatically -----------------
start "" cmd /c "timeout /t 2 >nul & start http://localhost:%PORT%/"

rem --- 8) Start the server (this line blocks until the window is closed) -
waitress-serve --host=0.0.0.0 --port=%PORT% config.wsgi:application

echo.
echo  Server stopped.
pause
