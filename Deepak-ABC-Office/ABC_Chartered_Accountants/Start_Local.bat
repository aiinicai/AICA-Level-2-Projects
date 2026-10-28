@echo off
cd /d "%~dp0"
"%~dp0runtime\python.exe" -I "%~dp0app\app.py"
pause
