@echo off
cd /d "%~dp0"
node --disable-warning=ExperimentalWarning server.js --list-users
echo.
set /p TTUSER=Type the user name to reset and press Enter: 
node --disable-warning=ExperimentalWarning server.js --reset-password "%TTUSER%"
pause
