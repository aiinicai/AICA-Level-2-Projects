@echo off
rem Restore a backup. STOP THE APP FIRST (close the start_app window).
rem The current data is backed up automatically before it is replaced.
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
echo Backups in this instance (newest first):
"%PY%" -m app.cli list-backups
echo.
echo Enter a file name from the list above, or the full path of a backup copied from elsewhere.
set /p BFILE="Backup file: "
"%PY%" -m app.cli verify-backup "%BFILE%"
if errorlevel 1 (
  pause
  exit /b 1
)
"%PY%" -m app.cli restore-backup "%BFILE%"
pause
