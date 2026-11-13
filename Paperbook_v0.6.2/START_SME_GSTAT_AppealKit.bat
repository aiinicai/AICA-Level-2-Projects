@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0index.html" (
  echo ERROR: index.html is missing.
  echo Please extract the complete ZIP before running.
  pause
  exit /b 1
)
start "" "%~dp0index.html"
exit /b 0
