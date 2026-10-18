@echo off
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
%PY% -c "import pandas, openpyxl" 2>nul || %PY% -m pip install -r requirements.txt
%PY% fifo_gui.py
if errorlevel 1 pause
