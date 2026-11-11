@echo off
cd /d "%~dp0"
echo Checking SmartHire configuration...
if not exist ".env" (echo ERROR: .env file missing & pause & exit /b 1)
type .env
echo.
echo Starting frontend. Keep this window open.
call npm run dev
pause
