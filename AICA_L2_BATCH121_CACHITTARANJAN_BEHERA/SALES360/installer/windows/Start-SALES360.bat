@echo off
setlocal
cd /d "%~dp0"
if not exist "runtime\python\python.exe" (
 echo Please extract the complete SALES360 package or run the Windows installer first.
 pause
 exit /b 1
)
"runtime\python\python.exe" "%~dp0SALES360.py" %*
if errorlevel 1 pause
