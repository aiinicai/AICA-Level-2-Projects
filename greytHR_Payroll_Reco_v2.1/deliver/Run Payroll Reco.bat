@echo off
setlocal EnableExtensions
title greytHR Payroll Reconciliation

rem ---------------------------------------------------------------
rem  greytHR Payroll Reconciliation - launcher
rem  Double-click this file. Keep it in the same folder as app.py.
rem  It does NOT create an .exe; it starts the Streamlit app in your
rem  web browser using the Python installed on this computer.
rem ---------------------------------------------------------------

rem 1. Work from the folder this launcher is in (spaces in the path are fine)
cd /d "%~dp0"
if not exist "app.py" goto :no_app
if not exist "requirements.txt" goto :no_req

rem 2. Find a working Python (the "py" launcher first, then "python")
set "PY="
where py >nul 2>&1
if errorlevel 1 goto :try_python
py -3 -c "import sys" >nul 2>&1
if errorlevel 1 goto :try_python
set "PY=py -3"
goto :have_python
:try_python
where python >nul 2>&1
if errorlevel 1 goto :no_python
python -c "import sys" >nul 2>&1
if errorlevel 1 goto :no_python
set "PY=python"
:have_python
%PY% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
if errorlevel 1 goto :old_python
for /f "delims=" %%v in ('%PY% --version 2^>^&1') do echo Using %%v

rem 3. Install only what is missing
%PY% -c "import streamlit, pandas, openpyxl, xlrd, lxml" >nul 2>&1
if not errorlevel 1 goto :packages_ok
echo.
echo Installing the required packages - first run only, this can take a few minutes...
%PY% -m pip install -r "requirements.txt"
if errorlevel 1 goto :pip_failed
%PY% -c "import streamlit, pandas, openpyxl, xlrd, lxml"
if errorlevel 1 goto :pip_failed
:packages_ok
echo All required packages are installed.

rem 4. Skip Streamlit's one-time e-mail question so the app starts straight away
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
if exist "%USERPROFILE%\.streamlit\credentials.toml" goto :start
>"%USERPROFILE%\.streamlit\credentials.toml" echo [general]
>>"%USERPROFILE%\.streamlit\credentials.toml" echo email = ""

:start
echo.
echo Starting the app. Your browser will open in a few seconds.
echo Keep this window open while you use the app. Close it to stop the app.
echo.
%PY% -m streamlit run "app.py" --browser.gatherUsageStats false
if errorlevel 1 goto :run_failed
goto :end

:no_app
echo [ERROR] app.py was not found in "%~dp0".
echo Keep this launcher in the same folder as app.py and requirements.txt.
goto :fail
:no_req
echo [ERROR] requirements.txt was not found in "%~dp0".
goto :fail
:no_python
echo [ERROR] Python was not found on this computer.
echo Install Python 3.10 or newer from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during installation, then run this file again.
goto :fail
:old_python
echo [ERROR] Python 3.9 or newer is required. Installed version:
%PY% --version
goto :fail
:pip_failed
echo.
echo [ERROR] The packages could not be installed. Check your internet connection
echo or proxy, then run this file again. Command used:
echo     %PY% -m pip install -r requirements.txt
goto :fail
:run_failed
echo.
echo [ERROR] The app stopped with an error - see the messages above.
goto :fail

:fail
echo.
echo Press any key to close this window.
pause >nul
endlocal
exit /b 1

:end
endlocal
exit /b 0
