@echo off
REM ============================================================
REM  DISCOM Audit Data Compiler — Build Standalone EXE
REM  Produces dist\DISCOM_Audit_Compiler.exe — a single file
REM  that runs on any Windows machine with NO Python required.
REM  Requires setup_first_time.bat to have been run at least once.
REM ============================================================

setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo  Building DISCOM Audit Data Compiler.exe
echo ============================================================
echo.

if not exist venv\Scripts\activate.bat (
    echo ERROR: Virtual environment not found.
    echo Please run setup_first_time.bat first.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.

echo Running PyInstaller (this can take several minutes)...
echo.
python -m PyInstaller DISCOM_Audit_Compiler.spec --noconfirm

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  BUILD FAILED. See the error messages above.
    echo  Common fixes:
    echo   - Make sure setup_first_time.bat completed successfully
    echo   - Try deleting the venv folder and running setup again
    echo ============================================================
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  BUILD SUCCESSFUL!
echo.
echo  Your standalone app is at:
echo    dist\DISCOM_Audit_Compiler.exe
echo.
echo  This single file can be copied to any Windows machine and
echo  run directly - no Python installation needed on that machine.
echo ============================================================
echo.
pause
