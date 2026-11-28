@echo off
set "PYTHONW=C:\Users\RANJAN\AppData\Local\Programs\Python\Python315\pythonw.exe"
if not exist "%PYTHONW%" (
  echo Python is not available at the expected location.
  echo Install Python, then run: python -m pip install -r requirements.txt
  pause
  exit /b 1
)
start "PDF Tool Suite" "%PYTHONW%" "%~dp0pdf_tool_suite.py"
