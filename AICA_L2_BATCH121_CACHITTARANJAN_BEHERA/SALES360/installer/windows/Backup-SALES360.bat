@echo off
setlocal
cd /d "%~dp0"
"runtime\python\python.exe" "%~dp0SALES360.py" --backup %*
if errorlevel 1 pause
