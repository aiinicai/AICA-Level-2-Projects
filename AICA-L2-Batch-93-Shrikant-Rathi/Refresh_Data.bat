@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" ( echo Run Start_LookThrough.bat once first. & pause & exit /b 1 )
".venv\Scripts\python.exe" bridge\lookthrough_bridge.py refresh
echo.
echo Done. app\LookThrough.html now contains the latest real data (works offline).
pause
