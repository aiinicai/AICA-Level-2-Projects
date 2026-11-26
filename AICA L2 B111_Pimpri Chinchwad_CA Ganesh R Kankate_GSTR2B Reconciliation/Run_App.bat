@echo off
cd /d "%~dp0"
echo Starting Tally vs GSTR-2B Reconciliation app...
echo (Close this window to stop the app.)
python -m streamlit run app.py
pause
