@echo off
rem Make an encrypted backup of the database and uploaded files now (the app also does this once a day).
cd /d "%~dp0"
".venv\Scripts\python.exe" -m app.cli backup
echo.
".venv\Scripts\python.exe" -m app.cli list-backups
pause
