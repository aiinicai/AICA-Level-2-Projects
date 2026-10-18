@echo off
REM Double-click to install requirements (first time) and start the dashboard.
cd /d "%~dp0"
python -m pip install -r requirements.txt
python -m streamlit run app.py
pause
