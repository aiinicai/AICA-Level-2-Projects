@echo off
setlocal
cd /d "%~dp0"
set "PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
set "APP=%~dp0net_asset_report.py"
set "LOG=%~dp0launch_error.log"
if not exist "%PYTHONW%" (
  echo Missing virtual environment: %PYTHONW%>"%LOG%"
  start "" notepad.exe "%LOG%"
  exit /b 1
)
if not exist "%APP%" (
  echo Missing application: %APP%>"%LOG%"
  start "" notepad.exe "%LOG%"
  exit /b 1
)
start "Net Asset Report" /b "%PYTHONW%" "%APP%"
exit /b 0
