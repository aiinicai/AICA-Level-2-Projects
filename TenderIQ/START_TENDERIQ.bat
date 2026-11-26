@echo off
title TenderIQ - AI Tender Intelligence Agent
cd /d "%~dp0"

echo ========================================================
echo   TENDERIQ - AI-POWERED TENDER INTELLIGENCE AGENT
echo ========================================================
echo.

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ and re-run this script.
    pause
    exit /b 1
)

python -c "import streamlit, playwright, bs4, pandas, openpyxl, pypdf, openai, dotenv, reportlab" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Required Python packages are missing.
    echo Run this command in CMD:
    echo   pip install streamlit playwright beautifulsoup4 pandas openpyxl pypdf openai python-dotenv reportlab
    echo   playwright install chromium
    pause
    exit /b 1
)

if not exist ".env" (
    echo [WARNING] .env file not found in %cd%.
    echo AI document analysis will be skipped until you copy .env.example to .env and add OPENAI_API_KEY.
    echo.
)

echo Starting TenderIQ web application...
echo Press Ctrl+C in this window to stop TenderIQ.
echo.
python -m streamlit run app.py --browser.gatherUsageStats false

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] TenderIQ failed to start. See error details above.
    pause
    exit /b %ERRORLEVEL%
)
