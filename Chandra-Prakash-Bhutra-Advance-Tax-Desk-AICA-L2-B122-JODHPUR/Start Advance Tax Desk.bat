@echo off
setlocal
title Advance Tax Desk
cd /d "%~dp0"

set "PORT=8501"
set "URL=http://localhost:%PORT%"
set "ENVDIR=%LOCALAPPDATA%\AdvanceTaxDesk\venv"
set "NEEDS=import streamlit, pandas, openpyxl, docx, requests, selenium, pypdf"

rem ---- Already running? Just open the browser.
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul 2>&1
if not errorlevel 1 goto already_running

rem ---- Find Python: our own environment, then the one installed on this computer.
if exist "%ENVDIR%\Scripts\python.exe" goto use_env
set "PY="
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto have_python
where python >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto have_python
goto no_python

:have_python
rem ---- If everything is already installed, start straight away.
%PY% -c "%NEEDS%" >nul 2>&1
if not errorlevel 1 goto run

echo.
echo  Setting up Advance Tax Desk. This takes a few minutes and needs internet.
echo  It is done only when something is missing.
echo.
%PY% -m pip install -r requirements.txt
%PY% -c "%NEEDS%" >nul 2>&1
if not errorlevel 1 goto run

echo.
echo  Trying a separate environment...
%PY% -m venv "%ENVDIR%"
if errorlevel 1 goto setup_failed
"%ENVDIR%\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
"%ENVDIR%\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto setup_failed

:use_env
set "PY="%ENVDIR%\Scripts\python.exe""
%PY% -c "%NEEDS%" >nul 2>&1
if not errorlevel 1 goto run
echo  Updating the required packages...
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto setup_failed

:run
rem ---- Keep an icon on the Desktop for next time.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\make_shortcut.ps1" >nul 2>&1

echo.
echo  Advance Tax Desk is starting. The browser will open by itself.
echo  Next time use the "Advance Tax Desk" icon on the Desktop.
echo  Keep this window open while you work. Close it to stop the app.
echo.
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "for($i=0;$i -lt 120;$i++){try{(New-Object Net.Sockets.TcpClient('127.0.0.1',%PORT%)).Close();Start-Process '%URL%';break}catch{Start-Sleep -Milliseconds 500}}"
%PY% -m streamlit run app.py --server.port %PORT% --server.headless true --browser.gatherUsageStats false
echo.
echo  Advance Tax Desk has stopped.
pause
goto end

:already_running
echo  Advance Tax Desk is already running. Opening it in the browser.
start "" "%URL%"
goto end

:no_python
echo.
echo  Python was not found on this computer.
echo  Install Python 3.10 or later from https://www.python.org/downloads/
echo  Tick "Add python.exe to PATH" during installation, then double-click this file again.
echo.
pause
goto end

:setup_failed
echo.
echo  Setup could not be completed. Check the internet connection and try again.
echo  To set up by hand, see "How to run" in README.md.
echo.
pause

:end
endlocal
