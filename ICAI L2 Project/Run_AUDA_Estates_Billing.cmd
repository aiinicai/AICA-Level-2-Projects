@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if not errorlevel 1 (
    py -3 -m pip install --disable-pip-version-check reportlab >nul 2>&1
    py -3 "%~dp0auda_estates_billing.py"
) else (
    python -m pip install --disable-pip-version-check reportlab >nul 2>&1
    python "%~dp0auda_estates_billing.py"
)

if errorlevel 1 (
    echo.
    echo The billing application could not start.
    echo Please install Python 3 from https://www.python.org/downloads/
    pause
)
