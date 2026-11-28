@echo off
REM Safe online backup of the database (can run while users are working). Schedule daily in Task Scheduler.
cd /d "%~dp0"
call venv\Scripts\activate
python backup.py
