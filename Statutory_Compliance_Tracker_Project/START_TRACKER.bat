@echo off
title Statutory Compliance Tracker
cd /d "%~dp0"
python -m streamlit run Statutory_Compliance_Tracker.py
echo.
echo If the app did not start, run INSTALL_REQUIREMENTS.bat first.
pause
