@echo off
REM ============================================================
REM  DISCOM Audit Data Compiler — First-Time Setup
REM  Run this ONCE before build_exe.bat.
REM  Creates a virtual environment and installs all dependencies,
REM  including PyInstaller (needed to build the .exe).
REM ============================================================

setlocal

echo.
echo ============================================================
echo  DISCOM Audit Data Compiler - First-Time Setup
echo ============================================================
echo.

REM --- Find a working Python launcher ---
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=py
    goto :found_python
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python
    goto :found_python
)

echo ERROR: Python was not found on this machine.
echo.
echo Please install Python 3.10 or newer from https://www.python.org/downloads/
echo During install, make sure to check "Add python.exe to PATH".
echo.
pause
exit /b 1

:found_python
echo Using Python command: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

REM --- Create virtual environment if it doesn't already exist ---
if exist venv\ (
    echo Virtual environment already exists - skipping creation.
) else (
    echo Creating virtual environment in .\venv ...
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)
echo.

REM --- Activate venv and install dependencies ---
echo Installing dependencies (this can take a few minutes)...
call venv\Scripts\activate.bat

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install PyQt6 pyinstaller

if errorlevel 1 (
    echo.
    echo ERROR: Dependency installation failed. See the messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Setup complete!
echo.
echo  Next steps:
echo    - To run the app directly:      run_app.bat
echo    - To build the standalone exe:  build_exe.bat
echo ============================================================
echo.
pause
