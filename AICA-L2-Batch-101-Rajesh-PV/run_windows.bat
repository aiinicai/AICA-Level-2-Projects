@echo off
REM ======================================================================
REM  Judgement Insights Analyser - Windows launcher
REM
REM  The Python environment lives in your user profile
REM  (%USERPROFILE%\.JudgmentInsightAnalyzer\venv), NOT in this folder, so it
REM  survives replacing this folder with a newer version. It is deliberately
REM  NOT under AppData: Microsoft Store Python silently redirects AppData
REM  writes into its own private package folder. Packages are
REM  installed only when they are actually missing or requirements.txt has
REM  changed - normally just once.
REM ======================================================================
setlocal
cd /d "%~dp0"
title Judgement Insights Analyser

REM --- 0. Refuse to run from inside a ZIP (Windows runs it from a temp folder)
echo "%~dp0" | find /i "\AppData\Local\Temp\" >nul
if not errorlevel 1 (
    echo.
    echo It looks like this was started from inside the ZIP file.
    echo Please right-click the ZIP, choose "Extract All...", open the extracted
    echo folder and run run_windows.bat from there.
    goto :fail
)

set "VENV_DIR=%USERPROFILE%\.JudgmentInsightAnalyzer\venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "MARKER=%VENV_DIR%\requirements-installed.txt"
set "CHECK=import customtkinter, pymupdf, google.genai, docx, reportlab, PIL, keyring, pytesseract, dotenv, openpyxl, win32com.client"

REM --- 1. Create the environment once ----------------------------------------
if not exist "%VENV_PY%" (
    echo First-time setup: creating the Python environment...
    if not exist "%USERPROFILE%\.JudgmentInsightAnalyzer" mkdir "%USERPROFILE%\.JudgmentInsightAnalyzer"
    where py >nul 2>nul && (py -3 -m venv "%VENV_DIR%") || (python -m venv "%VENV_DIR%")
)
REM Fallback: if the profile location could not be used, keep the environment in this folder.
if not exist "%VENV_PY%" (
    echo Using a local environment inside the app folder instead...
    set "VENV_DIR=%~dp0.venv"
    set "VENV_PY=%~dp0.venv\Scripts\python.exe"
    set "MARKER=%~dp0.venv\requirements-installed.txt"
    if not exist "%~dp0.venv\Scripts\python.exe" (
        where py >nul 2>nul && (py -3 -m venv "%~dp0.venv") || (python -m venv "%~dp0.venv")
    )
    if not exist "%~dp0.venv\Scripts\python.exe" (
        echo.
        echo ERROR: Could not create the Python environment.
        echo Install Python 3.10 or newer from https://www.python.org/downloads/
        echo and tick "Add python.exe to PATH" during installation.
        goto :fail
    )
)

REM --- 2. Install packages only if something is missing or requirements changed
set "NEED_INSTALL=0"
fc /b requirements.txt "%MARKER%" >nul 2>nul || set "NEED_INSTALL=1"
"%VENV_PY%" -c "%CHECK%" >nul 2>nul || set "NEED_INSTALL=1"
if "%NEED_INSTALL%"=="1" (
    echo Installing required packages - needed only once, please wait...
    "%VENV_PY%" -m pip install --disable-pip-version-check -q --upgrade pip
    "%VENV_PY%" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Package installation failed - see the messages above.
        echo If you are on a corporate network, a proxy or firewall may be blocking pypi.org.
        goto :fail
    )
    copy /y requirements.txt "%MARKER%" >nul
) else (
    echo Packages already installed.
)

REM --- 3. Start the application (pythonw = no console window kept busy) ----------
echo Starting Judgement Insights Analyser...
if exist "%VENV_DIR%\Scripts\pythonw.exe" (
    start "" "%VENV_DIR%\Scripts\pythonw.exe" main.py
) else (
    "%VENV_PY%" main.py
    if errorlevel 1 goto :fail
)
exit /b 0

:fail
echo.
echo Press any key to close this window.
pause >nul
exit /b 1
