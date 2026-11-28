@echo off
cd /d "%~dp0"
REM Runs the AI Resume Screener with Python (no EXE needed)
set "PY=python"
for %%V in (3.13 3.11 3.12) do py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
%PY% -m pip install -q -r requirements.txt
%PY% resume_screener.py
if errorlevel 1 pause
