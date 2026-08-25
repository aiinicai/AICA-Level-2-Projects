@echo off
setlocal enabledelayedexpansion
title Bank Statement Analyzer

echo ================================================================
echo           BANK STATEMENT ANALYZER - PORTABLE v1.6.1
echo ================================================================
echo.

cd /d "%~dp0"

REM --- Check 1: Portable Executable in Current Directory ---
if exist "BankStatementAnalyzerPortable.exe" (
    echo [INFO] Found portable executable: BankStatementAnalyzerPortable.exe
    echo [INFO] All dependencies and Python runtime are pre-packaged.
    echo [INFO] Starting Bank Statement Analyzer...
    echo.
    start "" "BankStatementAnalyzerPortable.exe"
    goto :SUCCESS
)

if exist "BankStatementAnalyzerPortable\BankStatementAnalyzerPortable.exe" (
    echo [INFO] Found portable executable in .\BankStatementAnalyzerPortable
    echo [INFO] All dependencies and Python runtime are pre-packaged.
    echo [INFO] Starting Bank Statement Analyzer...
    echo.
    cd /d "%~dp0BankStatementAnalyzerPortable"
    start "" "BankStatementAnalyzerPortable.exe"
    goto :SUCCESS
)

REM --- Check 2: Fallback to Python Environment and Dependency Install ---
echo [INFO] Portable executable not directly found. Checking for Python installation...

where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Neither BankStatementAnalyzerPortable.exe nor Python was found.
        echo Please ensure the portable app folder is intact or install Python 3.9+.
        goto :FAIL
    ) else (
        set "PY_CMD=py"
    )
) else (
    set "PY_CMD=python"
)

echo [INFO] Using Python: !PY_CMD!
echo [INFO] Checking and installing required dependencies...
echo.

!PY_CMD! -m pip install --upgrade pip
!PY_CMD! -m pip install streamlit pandas altair plotly pyarrow pdfminer.six pypdfium2 openpyxl xlsxwriter cryptography

if %errorlevel% neq 0 (
    echo [WARNING] Some dependencies might have encountered issues during install.
)

echo.
echo [INFO] Launching Streamlit Application...

if exist "_internal\streamlit_app.py" (
    !PY_CMD! -m streamlit run "_internal\streamlit_app.py"
) else if exist "BankStatementAnalyzerPortable\_internal\streamlit_app.py" (
    !PY_CMD! -m streamlit run "BankStatementAnalyzerPortable\_internal\streamlit_app.py"
) else if exist "streamlit_app.py" (
    !PY_CMD! -m streamlit run "streamlit_app.py"
) else (
    echo [ERROR] Could not locate streamlit_app.py
    goto :FAIL
)

:SUCCESS
echo.
echo ================================================================
echo  Application launched successfully!
echo ================================================================
timeout /t 3 >nul
exit /b 0

:FAIL
echo.
echo ================================================================
echo  Startup failed. Press any key to exit.
echo ================================================================
pause
exit /b 1
