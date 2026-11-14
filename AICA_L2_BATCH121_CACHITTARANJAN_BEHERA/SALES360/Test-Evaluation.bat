@echo off
setlocal
cd /d "%~dp0"
".tools\python-embed\python.exe" "tests\integration\evaluation.py" "output\releases\SALES360-Offline-0.9.1" "evaluation-%RANDOM%-%RANDOM%"
exit /b %ERRORLEVEL%
