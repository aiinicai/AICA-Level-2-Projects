@echo off
REM Double-click launcher for the Audit Sampling & Fraud Detection Tool.
REM Just runs "python app.py" so the evaluator never has to open a
REM command prompt manually.
cd /d "%~dp0"
python app.py
pause
