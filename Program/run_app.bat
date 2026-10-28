@echo off
title Ind AS 116 Lease Accounting Tool
echo ========================================================
echo   Ind AS 116 Lease Accounting Tool (Offline Desktop App)
echo ========================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in system PATH.
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b
)

echo [INFO] Python detected. Launching application...
echo [INFO] Application will open in your default browser at http://localhost:8501
echo [INFO] Press Ctrl+C in this terminal window to stop the application.
echo.

streamlit run app.py --server.headless=false --server.port=8501

pause
