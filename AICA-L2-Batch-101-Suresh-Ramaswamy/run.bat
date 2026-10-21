@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
    echo First start: setting up. Please wait a few minutes...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -c "import tkinterdnd2, pandas, openpyxl, pymupdf" 2>nul || (
    echo Installing missing parts. Please wait...
    python -m pip install -r requirements.txt
)
python main.py
if errorlevel 1 pause
