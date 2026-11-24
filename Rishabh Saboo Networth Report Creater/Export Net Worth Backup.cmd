@echo off
setlocal
cd /d "%~dp0"
if not exist "networth.sqlite3" (
    echo Existing Net Worth Office database was not found in this folder.
    pause
    exit /b 1
)
set "NW_DB=%CD%\networth.sqlite3"
".venv\Scripts\python.exe" networth.py backup "%CD%\networth-backup.sqlite3"
if errorlevel 1 echo Backup failed. If a backup already exists, rename it and retry.
pause
