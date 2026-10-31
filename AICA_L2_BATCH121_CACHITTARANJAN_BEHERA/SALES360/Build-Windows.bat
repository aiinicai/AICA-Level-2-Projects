@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build-windows.ps1" %*
set "SALES360_EXIT=%ERRORLEVEL%"
if not "%SALES360_EXIT%"=="0" echo Operation failed. Read the error above.
exit /b %SALES360_EXIT%
