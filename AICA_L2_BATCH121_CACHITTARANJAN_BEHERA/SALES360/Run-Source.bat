@echo off
setlocal
cd /d "%~dp0"
if not exist "output\releases\SALES360-Offline-0.9.1\SALES360.py" (
 echo Run Prepare-BuildTools.bat and Build-Windows.bat first.
 exit /b 1
)
call "output\releases\SALES360-Offline-0.9.1\Start-SALES360.bat" %*
