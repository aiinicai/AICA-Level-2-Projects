@echo off
rem Stop the app started by start_app.bat or its shortcut. (Not the server service set up by setup_server.ps1.)
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" -m app.launcher --stop
