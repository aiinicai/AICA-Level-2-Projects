@echo off
REM ==================================================================
REM  Builds dist\MSME_Verification_System.exe
REM  The build environment is kept in %LOCALAPPDATA% (outside OneDrive)
REM  so that hundreds of MB of libraries are not synced to the cloud.
REM ==================================================================
setlocal
cd /d "%~dp0"

set "BUILD_HOME=%LOCALAPPDATA%\MSMEVerificationSystem"
set "VENV=%BUILD_HOME%\venv"
set "PY=%VENV%\Scripts\python.exe"

echo.
echo === 1/4  Checking Python ===
if not exist "%PY%" (
    where py >nul 2>nul
    if errorlevel 1 (
        echo Python launcher "py" not found. Install Python 3.10 or newer from
        echo https://www.python.org/downloads/windows/  and tick "Add python.exe to PATH".
        goto :fail
    )
    echo Creating build environment in %VENV%
    py -3 -m venv "%VENV%"
    if errorlevel 1 goto :fail
)

echo.
echo === 2/4  Installing libraries (needs internet the first time) ===
"%PY%" -m pip install --upgrade pip --quiet
"%PY%" -m pip install --retries 10 --timeout 60 -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo === 3/4  Creating icon ===
"%PY%" make_icon.py
if errorlevel 1 goto :fail

echo.
echo === 4/4  Building the .exe (takes a few minutes) ===
"%PY%" -m PyInstaller --noconfirm --clean ^
    --workpath "%BUILD_HOME%\build" ^
    --distpath "%~dp0dist" ^
    msme_app.spec
if errorlevel 1 goto :fail

echo.
echo ==================================================================
echo  Done:  %~dp0dist\MSME_Verification_System.exe
echo ==================================================================
pause
exit /b 0

:fail
echo.
echo *** Build failed - see the messages above and README.md (Troubleshooting).
pause
exit /b 1
