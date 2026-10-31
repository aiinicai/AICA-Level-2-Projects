@echo off
setlocal
cd /d "%~dp0"
echo Restore needs a backup and a NEW isolated data directory. See INSTALLATION-AND-USAGE.html.
if "%~1"=="" (
 echo Usage: Restore-SALES360.bat --restore "backup.s360local" --data-dir "new-folder"
 pause
 exit /b 1
)
"runtime\python\python.exe" "%~dp0SALES360.py" %*
if errorlevel 1 pause
