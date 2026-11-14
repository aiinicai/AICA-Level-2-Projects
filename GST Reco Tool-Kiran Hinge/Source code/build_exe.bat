@echo off
REM ---------------------------------------------------------------------------
REM  Builds "GST Reco Tool.exe" from source. Only needed when the code changes.
REM  Needs Python 3.11+ on THIS (build) PC. Staff PCs need nothing - just the exe.
REM ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

if not exist ".build_venv\Scripts\python.exe" (
    echo Creating build environment...
    python -m venv .build_venv || goto :fail
)
echo Installing build requirements...
".build_venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".build_venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt pyinstaller || goto :fail

echo Building exe (takes 1-3 minutes)...
".build_venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "GST Reco Tool" --icon app.ico --add-data "app.ico;." ^
    --collect-data customtkinter ^
    --exclude-module streamlit --exclude-module pandas --exclude-module numpy ^
    gst_reco_app.py || goto :fail

echo.
echo Done:  dist\GST Reco Tool.exe
pause
exit /b 0

:fail
echo.
echo BUILD FAILED - see the messages above.
pause
exit /b 1
