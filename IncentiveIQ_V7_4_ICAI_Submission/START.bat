@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 goto end
python -m streamlit run app.py
:end
pause
