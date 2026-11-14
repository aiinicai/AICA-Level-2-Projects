@echo off
rem Use only if the program does not open: runs it with a visible console and a self-check.
cd /d "%~dp0program"
"%~dp0python\python.exe" "%~dp0program\main_qt.py" --selfcheck
echo.
echo If you see FAIL lines above, or an error, send a screenshot of this window.
pause
