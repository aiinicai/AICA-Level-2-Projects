@echo off
title CBSE Exam Generator - EXE Builder
color 0A

echo ============================================================
echo          CBSE EXAM GENERATOR - EXE BUILDER
echo ============================================================
echo.

REM ------------------------------------------------------------
REM Check Python
REM ------------------------------------------------------------

echo [1/6] Checking Python installation...
python --version

if errorlevel 1 (
    echo.
    echo ERROR: Python was not found.
    echo Please install Python and select "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo.
echo Python found successfully.
echo.

REM ------------------------------------------------------------
REM Upgrade pip
REM ------------------------------------------------------------

echo [2/6] Preparing pip...
python -m ensurepip --upgrade

if errorlevel 1 (
    echo.
    echo ERROR: Could not install/repair pip.
    echo Please repair your Python installation first.
    echo.
    pause
    exit /b 1
)

python -m pip install --upgrade pip

if errorlevel 1 (
    echo.
    echo ERROR: pip upgrade failed.
    echo.
    pause
    exit /b 1
)

echo.
echo pip is ready.
echo.

REM ------------------------------------------------------------
REM Install required packages
REM ------------------------------------------------------------

echo [3/6] Installing required libraries...
echo.

python -m pip install --upgrade reportlab python-docx pyinstaller

if errorlevel 1 (
    echo.
    echo ERROR: Required libraries could not be installed.
    echo.
    pause
    exit /b 1
)

echo.
echo Required libraries installed successfully.
echo.

REM ------------------------------------------------------------
REM Check application file
REM ------------------------------------------------------------

echo [4/6] Checking application file...

if not exist "cbse_exam_generator_desktop.py" (
    echo.
    echo ERROR:
    echo cbse_exam_generator_desktop.py was not found.
    echo.
    echo Make sure this BAT file is in the same folder
    echo as cbse_exam_generator_desktop.py
    echo.
    pause
    exit /b 1
)

echo Application file found.
echo.

REM ------------------------------------------------------------
REM Remove old build files
REM ------------------------------------------------------------

echo [5/6] Removing previous build files...

if exist "build" (
    rmdir /s /q "build"
)

if exist "dist" (
    rmdir /s /q "dist"
)

if exist "CBSE_Exam_Generator.spec" (
    del /q "CBSE_Exam_Generator.spec"
)

echo Old build files removed.
echo.

REM ------------------------------------------------------------
REM Build EXE
REM ------------------------------------------------------------

echo [6/6] Creating CBSE_Exam_Generator.exe...
echo.
echo This may take a few minutes.
echo Please wait...
echo.

python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --clean ^
    --name "CBSE_Exam_Generator" ^
    "cbse_exam_generator_desktop.py"

if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: EXE CREATION FAILED
    echo ============================================================
    echo.
    echo Please copy the error shown above and send it to ChatGPT.
    echo.
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM Check EXE
REM ------------------------------------------------------------

if not exist "dist\CBSE_Exam_Generator.exe" (
    echo.
    echo ERROR: EXE was not created.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo              BUILD COMPLETED SUCCESSFULLY
echo ============================================================
echo.
echo Your application is here:
echo.
echo %CD%\dist\CBSE_Exam_Generator.exe
echo.
echo ============================================================
echo.

REM ------------------------------------------------------------
REM Open the dist folder
REM ------------------------------------------------------------

echo Opening the EXE folder...
start "" "%CD%\dist"

echo.
echo You can now double-click:
echo.
echo CBSE_Exam_Generator.exe
echo.
pause