@echo off
setlocal
title Build AI Resume Screener EXE
cd /d "%~dp0"

echo ==========================================================
echo   AI Resume Screener - EXE builder
echo   Makes Resume_Screener.exe (with offline OCR for scans)
echo ==========================================================
if not exist "resume_screener.py" (
    echo [ERROR] Put this file in the same folder as resume_screener.py, then run it again.
    pause
    exit /b 1
)
echo.

REM ---- 1. Find Python (prefer 3.12, then 3.11, 3.13, 3.10) ----
set "PY="
for %%V in (3.12 3.11 3.13 3.10) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [ERROR] Python 3.10 - 3.13 was not found.
    echo Install Python 3.12 from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" on the first screen. Then run this file again.
    pause
    exit /b 1
)
echo Using: %PY%
%PY% --version
echo.

REM ---- 2. Make a clean private environment for the build ----
if not exist "build_env\Scripts\python.exe" (
    echo [1/4] Creating build environment...
    %PY% -m venv build_env || goto :fail
)
set "VPY=build_env\Scripts\python.exe"

REM ---- 3. Install the libraries ----
echo [2/4] Installing libraries (first time takes a few minutes)...
"%VPY%" -m pip install --upgrade pip >nul
"%VPY%" -m pip install -r requirements.txt pyinstaller || goto :fail

REM ---- 4. Build the EXE ----
echo [3/4] Building the EXE (takes 1 to 3 minutes)...
"%VPY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name Resume_Screener ^
    --collect-all rapidocr_onnxruntime ^
    --collect-all pypdfium2 ^
    --collect-all docx ^
    --collect-binaries onnxruntime ^
    --add-data "english_words.txt.gz;." ^
    resume_screener.py || goto :fail

REM ---- 5. Put the EXE next to this file ----
echo [4/4] Copying the EXE...
copy /y "dist\Resume_Screener.exe" "Resume_Screener.exe" >nul || goto :fail

echo.
echo ==========================================================
echo   DONE!  Your app is: %CD%\Resume_Screener.exe
echo   Double-click it to run. It works on any Windows PC,
echo   no Python needed. (First start takes ~10 seconds.)
echo ==========================================================
pause
exit /b 0

:fail
echo.
echo [ERROR] The build stopped. Check the messages above.
echo Tip: make sure you are connected to the internet for the first build.
pause
exit /b 1
