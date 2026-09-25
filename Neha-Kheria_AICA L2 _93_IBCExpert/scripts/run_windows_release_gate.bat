@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_windows_release_gate.ps1" %*
exit /b %ERRORLEVEL%
