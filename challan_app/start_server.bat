@echo off
cd /d "%~dp0"
call venv\Scripts\activate
python run_server.py 8080
pause
