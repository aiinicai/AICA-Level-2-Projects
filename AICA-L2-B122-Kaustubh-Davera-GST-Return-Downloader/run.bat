@echo off
cd /d "%~dp0"
if not exist ".installed" (
    echo Installing required packages, please wait...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Package install failed. Check that Python is installed and "Add to PATH" was ticked.
        pause
        exit /b 1
    )
    echo ok> .installed
)
python main.py %*
if errorlevel 1 pause
