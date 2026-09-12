@echo off
REM Cash Runway - start the application.
REM
REM Everything needed is inside this folder. No internet connection is
REM required: the Python packages are bundled in backend\vendor and the
REM frontend is already built, so there is nothing to download.
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo   Cash Runway
echo   ===========
echo.

REM ---- Find a usable Python -------------------------------------------
REM On Windows "python" is often a Microsoft Store stub, so fall back to the
REM py launcher before giving up.
set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY (py -3 --version >nul 2>&1 && set "PY=py -3")
if not defined PY (
  echo   Python was not found.
  echo.
  echo   Install Python 3.12, 3.13 or 3.14 from
  echo     https://www.python.org/downloads/
  echo   and tick "Add python.exe to PATH" on the FIRST installer screen.
  echo.
  pause
  exit /b 1
)
for /f "tokens=*" %%v in ('%PY% --version 2^>^&1') do echo   Using %%v
echo.

REM ---- Dependencies, from the bundled folder ---------------------------
pushd backend
%PY% -c "import fastapi, sqlalchemy, pydantic, jwt, bcrypt, openpyxl, requests, dateutil, uvicorn" >nul 2>&1
if errorlevel 1 (
  echo   [1/2] Installing the bundled Python packages. No download needed.
  echo.
  %PY% -m pip install --no-index --find-links vendor -r requirements.txt --disable-pip-version-check
  if errorlevel 1 (
    echo.
    echo   ------------------------------------------------------------------
    echo   The bundled packages could not be installed.
    echo.
    echo   Read the last ERROR line above:
    echo.
    echo     "No matching distribution found for ^<name^>"
    echo         A package is missing from backend\vendor.
    echo.
    echo     Anything mentioning cp3XX or win_amd64
    echo         Your Python version is not one of the bundled ones.
    echo         The bundle covers Python 3.12, 3.13 and 3.14 on 64-bit
    echo         Windows. Install one of those from python.org.
    echo.
    echo   With internet access this always works instead:
    echo       %PY% -m pip install -r backend\requirements.txt
    echo   ------------------------------------------------------------------
    echo.
    popd & pause & exit /b 1
  )
) else (
  echo   [1/2] Python packages already installed.
)
echo.

REM No seeding here, deliberately. The application creates the sign-in accounts
REM itself on first start, and then ASKS which data to load — demonstration
REM company, or your own. Loading the demo here would answer that question on
REM the user's behalf and the first-run screen would never appear.
REM
REM To load the demo from the command line instead:  %PY% seed_db.py

echo   [2/2] Starting Cash Runway on http://localhost:8000
echo.
echo   ==================================================================
echo.
echo     Open   http://localhost:8000
echo.
echo     Sign in with
echo       guru@northwindrobotics.in  /  cashrunway
echo.
echo     First time? You will be asked whether to load the demonstration
echo     company or set up your own.
echo.
echo     API documentation is at http://localhost:8000/docs
echo     Something wrong?  %PY% doctor.py   (run it in the backend folder)
echo.
echo     Press Ctrl-C in this window to stop.
echo.
echo   ==================================================================
echo.

REM Bound to this machine only, by default. Uvicorn's default host is
REM 127.0.0.1, so no other device on the network can reach it -- which is the
REM right default for a laptop on a cafe wi-fi.
REM
REM To let colleagues sign in from their own machines, set CR_HOST before
REM running this:
REM
REM     set CR_HOST=0.0.0.0
REM     run.bat
REM
REM They then open http://<this-machine's-ip>:8000. Note there is no HTTPS:
REM passwords cross the network in clear text, so do that on a trusted
REM office network and not on a public one.
if "%CR_HOST%"=="" set CR_HOST=127.0.0.1

start "" http://localhost:8000
%PY% -m uvicorn app.main:app --host %CR_HOST% --port 8000
popd
pause
