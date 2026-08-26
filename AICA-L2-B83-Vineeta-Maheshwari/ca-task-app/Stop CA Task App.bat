@echo off
title Stop CA Task App
echo Stopping the CA Task Delegation App server...
taskkill /FI "WINDOWTITLE eq CA Task App Server*" /T /F >nul 2>nul
if errorlevel 1 (
  echo The server did not appear to be running.
) else (
  echo Done - the server has been stopped.
)
echo.
pause
