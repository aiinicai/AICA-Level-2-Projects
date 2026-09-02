@echo off
setlocal enabledelayedexpansion
echo ============================================================
echo  Tally Converter - Windows Build Script
echo ============================================================
echo.

REM --- 0. Sanity checks --------------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found on PATH. Install Python 3.12 from
    echo        https://www.python.org/downloads/ and check "Add to PATH".
    pause
    exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
    echo ERROR: Node.js was not found on PATH. Install Node.js LTS from
    echo        https://nodejs.org/
    pause
    exit /b 1
)

REM --- 1. Build the React frontend -----------------------------------
echo [1/7] Building frontend...
cd frontend
call npm install
if errorlevel 1 goto :error
call npm run build
if errorlevel 1 goto :error
cd ..
echo Frontend build complete.
echo.

REM --- 2. Create/activate a clean virtual environment for the build --
echo [2/7] Setting up Python build environment...
cd backend
if not exist build_venv (
    python -m venv build_venv
)
call build_venv\Scripts\activate.bat
python -m pip install --upgrade pip
echo.

REM --- 3. Install Python requirements ---------------------------------
echo [3/7] Installing Python requirements...
pip install -r requirements.txt
if errorlevel 1 goto :error
pip install pyinstaller
echo.

REM --- 4. Run tests - build stops if tests fail -----------------------
echo [4/7] Running test suite...
pytest tests -v
if errorlevel 1 (
    echo.
    echo ERROR: Tests failed. Fix failing tests before packaging a release.
    goto :error
)
echo.

REM --- 5. Build the PyInstaller package --------------------------------
echo [5/7] Building executable with PyInstaller...
cd ..
pyinstaller TallyConverter.spec --noconfirm --clean
if errorlevel 1 goto :error
echo.

REM --- 6. Verify Tesseract was bundled (warn, don't fail, if missing) --
echo [6/7] Checking bundled Tesseract...
if exist "dist\TallyConverter\tesseract\tesseract.exe" (
    echo Tesseract bundled successfully.
) else (
    echo WARNING: Tesseract was not bundled. Either:
    echo   a^) install Tesseract at C:\Program Files\Tesseract-OCR before
    echo      running this script so it gets bundled automatically, or
    echo   b^) instruct customers to install Tesseract separately from
    echo      https://github.com/UB-Mannheim/tesseract/wiki - the app will
    echo      auto-detect a system install at first launch.
)
echo.

REM --- 7. Build the Windows installer with Inno Setup -----------------
echo [7/7] Building installer...
where iscc >nul 2>nul
if errorlevel 1 (
    echo WARNING: Inno Setup Compiler ^(iscc^) not found on PATH.
    echo Install Inno Setup from https://jrsoftware.org/isdl.php and either
    echo add its folder to PATH or run manually:
    echo   "C:\Program Files ^(x86^)\Inno Setup 6\iscc.exe" installer\installer.iss
) else (
    iscc installer\installer.iss
    if errorlevel 1 goto :error
    echo.
    echo ============================================================
    echo  BUILD COMPLETE
    echo  Installer created at: installer\output\TallyConverterSetup.exe
    echo ============================================================
)

goto :end

:error
echo.
echo ============================================================
echo  BUILD FAILED - see errors above
echo ============================================================
pause
exit /b 1

:end
echo.
echo (Press any key to close this window.)
pause >nul
endlocal