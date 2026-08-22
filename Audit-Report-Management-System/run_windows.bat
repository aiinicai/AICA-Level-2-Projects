@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo Audit Report Generator - Stage 3
echo DOCX ONLY - NO LXML / NO PYTHON-DOCX
echo ============================================================
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python launcher ^(py^) was not found.
    echo Please install Python 3.11+ from python.org.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo ERROR: Could not create the virtual environment.
        pause
        exit /b 1
    )
)

echo.
echo Upgrading pip/setuptools/wheel...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo ERROR: Could not upgrade pip.
    pause
    exit /b 1
)

echo.
echo Installing application dependencies...
echo.
echo This version deliberately does NOT install:
echo   lxml
echo   python-docx
echo.
echo DOCX files are handled directly as WordprocessingML ZIP/XML
echo using Python's standard library. This preserves the original
echo template package and removes the lxml installation problem.
echo.

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ============================================================
    echo DEPENDENCY INSTALLATION FAILED
    echo ============================================================
    echo.
    echo Please send the complete console output to ChatGPT.
    pause
    exit /b 1
)

echo.
echo Verifying packages...
".venv\Scripts\python.exe" -c "import flask, openpyxl, sys; print('Python:', sys.version); print('Flask:', flask.__version__); print('openpyxl:', openpyxl.__version__)"
if errorlevel 1 (
    echo ERROR: Package verification failed.
    pause
    exit /b 1
)

echo.
echo Initialising Stage 3 database...
".venv\Scripts\python.exe" -c "from master_data import ensure_master; from register import ensure_register; ensure_master(); ensure_register(); print('Database initialisation: OK')"
if errorlevel 1 (
    echo ERROR: Application initialisation failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Installation completed successfully.
echo ============================================================
echo.
echo Starting Audit Report Generator...
echo Open http://127.0.0.1:5000 in Chrome.
echo Press Ctrl+C in this window to stop the application.
echo.
".venv\Scripts\python.exe" app.py

echo.
echo Application stopped.
pause
