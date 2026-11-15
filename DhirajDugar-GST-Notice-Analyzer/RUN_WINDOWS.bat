@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
echo Starting GST Notice Analyzer. Keep this window open.
echo Press Ctrl+C here when you have finished.
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 pause
exit /b
:missing
echo Please run SETUP_WINDOWS.bat first. See README.md for instructions.
pause
exit /b 1
