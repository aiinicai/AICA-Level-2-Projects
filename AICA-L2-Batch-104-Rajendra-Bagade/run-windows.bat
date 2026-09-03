@echo off
REM AuditLens - start on Windows.
REM Sets up a private environment on first run, then starts the server.
REM The browser is opened by the launcher only once the server is
REM actually listening, so it never lands on a connection-refused page.

setlocal
cd /d "%~dp0"
title AuditLens

echo.
echo   AuditLens - starting up
echo   ======================
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
  echo   Python was not found on this computer.
  echo.
  echo   Install Python 3.10 or later from https://www.python.org/downloads/
  echo   and tick "Add python.exe to PATH" on the first screen of the installer.
  echo   Then run this file again.
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo   First run - setting up. This takes a minute or two.
  echo.
  %PY% -m venv .venv
  if errorlevel 1 goto :setup_failed
  .venv\Scripts\python.exe -m pip install --upgrade pip
  if errorlevel 1 goto :setup_failed
  .venv\Scripts\python.exe -m pip install -e ".[dev]"
  if errorlevel 1 goto :setup_failed
  echo.
  echo   Setup complete.
  echo.
)

.venv\Scripts\python.exe -m auditlens.launch
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
  echo.
  echo   AuditLens stopped with an error. The message above says why.
  echo.
  pause
)
exit /b %EXITCODE%

:setup_failed
echo.
echo   Setup failed. The message above says why.
echo   The usual causes are no internet connection, or antivirus blocking
echo   the creation of the .venv folder.
echo.
echo   You can also set it up by hand:
echo     py -3 -m venv .venv
echo     .venv\Scripts\activate
echo     pip install -e ".[dev]"
echo     python -m auditlens.launch
echo.
pause
exit /b 1
