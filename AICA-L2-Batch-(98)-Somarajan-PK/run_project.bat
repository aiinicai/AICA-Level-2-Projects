@echo off
setlocal
title Bank Reconciliation Assistant
cd /d "%~dp0"

set "PY=python"
%PY% --version >nul 2>&1
if errorlevel 1 set "PY=py"
%PY% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found. Install it from python.org and tick "Add python.exe to PATH".
    pause
    exit /b 1
)

echo Checking required packages (first run only)...
%PY% -m pip install --quiet pandas openpyxl
if errorlevel 1 (
    echo [ERROR] Could not install pandas/openpyxl. Check your internet connection.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  AI-Powered Bank Reconciliation and Audit Assistant
echo.
echo  The application opens in your browser. Inside it:
echo   1. Pull bank books from Tally and select the bank
echo   2. Add the bank statement
echo   3. Run the reconciliation
echo   4. Review the results
echo   5. Approve, then export to Excel
echo.
echo  For Tally: open the company, then F1 (Help) ^> Settings ^>
echo  Connectivity ^> Client/Server ^> Server (or Both), port 9000.
echo  No Tally? Use "Load demo data" inside the app.
echo.
echo  Keep this window open while you work. Close it to stop.
echo ============================================================
echo.
%PY% tool_server.py
pause
endlocal
