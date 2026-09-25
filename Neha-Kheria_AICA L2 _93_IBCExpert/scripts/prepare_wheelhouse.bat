@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0prepare_wheelhouse.ps1" %*
exit /b %ERRORLEVEL%
