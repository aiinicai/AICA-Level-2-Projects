@echo off
setlocal
cd /d "%~dp0"
echo ==============================================
echo FinSight AI - Python 3.14 (64-bit) Launcher
echo ==============================================
where py >nul 2>&1
if not errorlevel 1 (
    py -3.14 -c "import sys; assert sys.version_info[:2] == (3,14) and sys.maxsize > 2**32" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3.14"
)
if not defined PYTHON_CMD (
    python -c "import sys; assert sys.version_info[:2] == (3,14) and sys.maxsize > 2**32" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo ERROR: Could not find Python 3.14 64-bit via py or python.
    echo Try: py -0p
    echo Check Python installation and PATH / Python Launcher.
    pause
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    echo Creating a fresh Python 3.14 virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3,14) and sys.maxsize > 2**32" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Existing .venv is not Python 3.14 64-bit.
    echo Delete the .venv folder and run this file again.
    pause
    exit /b 1
)
echo Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
echo Installing required packages (first run needs internet)...
".venv\Scripts\python.exe" -m pip install --prefer-binary -r requirements.txt
if errorlevel 1 goto :fail
echo Launching FinSight AI at http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto :fail
pause
exit /b 0
:fail
echo.
echo SETUP FAILED. Read PYTHON314_SETUP.md and copy the error message.
pause
exit /b 1
