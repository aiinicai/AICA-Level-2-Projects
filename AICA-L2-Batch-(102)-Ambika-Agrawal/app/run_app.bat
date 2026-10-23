@echo off
rem Starts the SURL Checker using the local virtual environment (created with: py -m venv .venv, then .venv\Scripts\pip install -r requirements.txt)
cd /d "%~dp0"
".venv\Scripts\python.exe" -m streamlit run surl_checker_app.py
pause
