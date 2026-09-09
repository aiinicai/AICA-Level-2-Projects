@echo off
echo ========================================================
echo        AI Auditor V8 - Windows Standalone EXE Builder
echo ========================================================
echo.

echo [1/3] Verifying Python and PyInstaller environment...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not available in PATH.
    pause
    exit /b 1
)

echo [2/3] Building Standalone Executable using PyInstaller...
pyinstaller --noconfirm --onedir --windowed ^
    --name "AI Auditor V8" ^
    --add-data "config;config" ^
    --add-data "core;core" ^
    --add-data "extraction;extraction" ^
    --add-data "analysis;analysis" ^
    --add-data "reports;reports" ^
    --add-data "gui;gui" ^
    --add-data "samples;samples" ^
    --hidden-import "openpyxl" ^
    --hidden-import "xlsxwriter" ^
    --hidden-import "docx" ^
    --hidden-import "pymupdf" ^
    --hidden-import "fitz" ^
    --hidden-import "pdfplumber" ^
    --hidden-import "pytesseract" ^
    --hidden-import "PIL" ^
    --hidden-import "rapidfuzz" ^
    --hidden-import "matplotlib" ^
    --hidden-import "pandas" ^
    --hidden-import "numpy" ^
    main.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller build failed. Check logs above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Build completed successfully!
echo Executable location: dist\AI Auditor V8\AI Auditor V8.exe
echo ========================================================
pause
