@echo off
setlocal EnableExtensions
title Tally Financial Intelligence - V14 Builder

cd /d "%~dp0"

echo ============================================================
echo   TALLY FINANCIAL INTELLIGENCE - V14 EXE BUILDER
echo ============================================================
echo.
echo Working folder:
echo %CD%
echo.

echo [1/6] Checking Python...
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found in PATH.
    echo.
    echo Try:
    echo     C:\Python314\python.exe --version
    echo.
    pause
    exit /b 1
)

python --version
if errorlevel 1 (
    echo ERROR: Python could not be started.
    pause
    exit /b 1
)

echo.
echo [2/6] Checking source files...

if not exist "Tally_Financial_Intelligence_Client_V12.py" (
    echo ERROR: Client source file is missing.
    pause
    exit /b 1
)

if not exist "Tally_Accounting_Extractor_Full_Financial_Rev13.py" (
    echo ERROR: Tally extractor source file is missing.
    pause
    exit /b 1
)

if not exist "TallyFinancialIntelligence_V13.spec" (
    echo ERROR: PyInstaller SPEC file is missing.
    pause
    exit /b 1
)

if not exist "dashboard\Tally_Financial_Intelligence_Dashboard.html" (
    echo ERROR: Dashboard HTML is missing.
    pause
    exit /b 1
)

echo Source files OK.

echo.
echo [3/6] Checking required Python packages...

python -c "import pandas,openpyxl,pyodbc,PyInstaller; print('Required packages OK')"
if errorlevel 1 (
    echo.
    echo Required packages are missing.
    echo Installing them now...
    echo.

    python -m pip install pandas openpyxl pyodbc pyinstaller
    if errorlevel 1 (
        echo.
        echo ERROR: Package installation failed.
        echo.
        echo If the PC is offline, install the packages on the
        echo development PC before running this build.
        pause
        exit /b 1
    )
)

echo.
echo [4/6] Cleaning old build...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo [5/6] Building EXE...
echo.

python -m PyInstaller --clean --noconfirm "TallyFinancialIntelligence_V13.spec"

if errorlevel 1 (
    echo.
    echo ============================================================
    echo BUILD FAILED
    echo ============================================================
    echo.
    echo The PyInstaller error is shown above.
    echo.
    pause
    exit /b 1
)

echo.
echo [6/6] Verifying EXE...

if not exist "dist\TallyFinancialIntelligence\TallyFinancialIntelligence.exe" (
    echo ERROR: EXE was not created.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo BUILD SUCCESSFUL
echo ============================================================
echo.
echo EXE:
echo %CD%\dist\TallyFinancialIntelligence\TallyFinancialIntelligence.exe
echo.
echo Copy the COMPLETE folder:
echo %CD%\dist\TallyFinancialIntelligence
echo.
echo Do NOT copy only the EXE.
echo.
pause
endlocal
