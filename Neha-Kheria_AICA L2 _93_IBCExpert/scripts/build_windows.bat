@echo off
setlocal
if "%~1"=="" (
  echo Usage: scripts\build_windows.bat C:\path\to\licence_public_key.hex
  exit /b 2
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1" -PublicKeyPath "%~1"
exit /b %ERRORLEVEL%
