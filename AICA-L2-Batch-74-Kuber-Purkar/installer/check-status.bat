@echo off
title CMA Pro Builder - Status
echo.
tasklist /FI "IMAGENAME eq CMA-Pro-Builder.exe" | find /I "CMA-Pro-Builder.exe" >nul
if errorlevel 1 (
  echo   Server:  NOT RUNNING   ^(double-click start.bat to start it^)
) else (
  echo   Server:  RUNNING
  echo   Open in browser:  http://localhost:8080
)
echo.
pause
