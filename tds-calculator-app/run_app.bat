@echo off
REM ============================================================
REM  Salary TDS Calculator & Advisor - Launcher
REM  Double-click this file to install dependencies (first run
REM  only) and start the app in your browser.
REM ============================================================

REM Move to the folder this .bat file is sitting in, so it works
REM no matter where the project folder is located on your PC.
cd /d "%~dp0"

echo ============================================
echo  Salary TDS Calculator and Advisor
echo ============================================
echo.
echo Working folder: %cd%
echo.

REM Check that app.py actually exists here, to give a clear
REM error instead of a confusing crash if the file was moved.
if not exist "app.py" (
    echo ERROR: app.py was not found in this folder.
    echo Make sure this .bat file is placed directly inside
    echo your tds-calculator-app folder, next to app.py.
    echo.
    pause
    exit /b 1
)

echo Installing/updating required packages...
echo (This may take a minute the first time you run it.)
echo.
pip install -r requirements.txt

echo.
echo Starting the app... a browser window will open automatically.
echo To stop the app, come back to this window and press CTRL+C.
echo.
streamlit run app.py

pause
