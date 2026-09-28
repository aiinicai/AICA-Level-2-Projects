@echo off
rem Monthly LookThrough monitor: refresh data, run policy checks, push the result to n8n.
rem Run by hand or from Windows Task Scheduler (e.g. on the 12th, after AMC disclosures are out).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" ( echo Run Start_LookThrough.bat once first. & exit /b 1 )
".venv\Scripts\python.exe" bridge\monitor_push.py --refresh
exit /b %errorlevel%
