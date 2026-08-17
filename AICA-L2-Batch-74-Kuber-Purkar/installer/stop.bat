@echo off
echo Stopping CMA Pro Builder...
taskkill /IM CMA-Pro-Builder.exe /F
if errorlevel 1 (echo Server was not running.) else (echo Server stopped.)
timeout /t 3 >nul
