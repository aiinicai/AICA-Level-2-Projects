@echo off
cd /d "%~dp0"
echo Starting TreatyLens AI V5.1 at http://127.0.0.1:8765
start "" "http://127.0.0.1:8765"
py -3 server.py
if errorlevel 1 python server.py
pause
