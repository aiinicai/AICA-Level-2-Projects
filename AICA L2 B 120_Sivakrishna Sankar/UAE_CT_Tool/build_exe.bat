@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Activating virtual environment...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo Virtual environment not found in .venv!
    exit /b 1
)

echo [2/3] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist\UAE_CT_Tool rmdir /s /q dist\UAE_CT_Tool

echo [3/3] Running PyInstaller...
pyinstaller UAE_CT_Tool.spec --noconfirm --clean

if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller build failed!
    exit /b %ERRORLEVEL%
)

echo.
echo ============================================================
echo Build completed successfully!
echo Executable directory: dist\UAE_CT_Tool
echo Executable file:      dist\UAE_CT_Tool\UAE_CT_Tool.exe
echo ============================================================
endlocal
