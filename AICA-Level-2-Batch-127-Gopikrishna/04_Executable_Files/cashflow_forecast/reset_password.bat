@echo off
rem Forgotten password (including the Admin's): run this on the PC where the app and its database are.
rem It gives the user a new temporary password, unlocks and reactivates the account.
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo The virtual environment is missing. See README / start_app.bat.
  pause
  exit /b 1
)
echo Users in this database:
"%PY%" -m app.cli list-users
echo.
set /p RUSER="User name to reset: "
"%PY%" -m app.cli reset-password "%RUSER%"
echo.
pause
