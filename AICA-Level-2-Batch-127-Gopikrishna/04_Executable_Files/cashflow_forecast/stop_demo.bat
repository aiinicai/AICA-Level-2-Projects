@echo off
rem Stop the demo started by start_demo.bat or its shortcut.
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" -m app.launcher --demo --stop
