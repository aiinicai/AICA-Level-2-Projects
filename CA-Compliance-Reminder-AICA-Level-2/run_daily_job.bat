@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
python daily_job.py
