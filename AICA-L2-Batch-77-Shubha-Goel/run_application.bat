@echo off
title HDFC Bank Statement Analyzer
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Please run install_dependencies.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m streamlit run hdfc_bank_statement_analyzer.py

pause
