@echo off
title GST 2B to Munim Template - IJR ^& Co.
color 1F
echo.
echo  ============================================================
echo       GST 2B to Munim Template Populator - IJR ^& Co.
echo  ============================================================
echo.

REM ── Find Python ──
set "PYTHON_CMD="

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :found
)
py --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto :found
)
python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python3"
    goto :found
)

echo  ERROR: Python not found. Install from https://www.python.org
echo  Check "Add Python to PATH" during installation.
pause
exit /b 1

:found
echo  Python: %PYTHON_CMD%
echo.
echo  Installing packages (pandas, openpyxl) ...
%PYTHON_CMD% -m pip install pandas openpyxl --quiet --disable-pip-version-check 2>nul
if errorlevel 1 (
    %PYTHON_CMD% -m pip install pandas openpyxl --user --quiet --disable-pip-version-check 2>nul
)
echo  Ready.
echo.
echo  Starting tool ...
echo  ============================================================
echo.

%PYTHON_CMD% "%~dp0gst_2b_to_munim.py"

if errorlevel 1 (
    echo.
    echo  Error occurred. Ensure gst_2b_to_munim.py is in the same folder.
    pause
)
