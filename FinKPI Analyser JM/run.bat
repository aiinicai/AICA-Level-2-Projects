@echo off
title FinKPI Analyzer Server
cls
echo =====================================================================
echo           FINKPI ANALYZER - ENTERPRISE FINANCIAL DASHBOARD          
echo =====================================================================
echo.
echo [1/3] Checking and installing Python dependencies...
python -m pip install -r requirements.txt

echo.
echo [2/3] Validating and seeding Trial Balance database...
python seed_data.py

echo.
echo [3/3] Starting FastAPI Web Application Server on http://127.0.0.1:8000...
echo Opening dashboard in your default browser...
timeout /t 2 >nul
start "" "http://127.0.0.1:8000"

python run.py
pause
