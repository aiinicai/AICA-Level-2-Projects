@echo off
cd /d "%~dp0"
"%~dp0runtime\python.exe" -I "%~dp0app\self_test.py"
echo.
echo These tests use temporary data and do not change your office database.
pause
