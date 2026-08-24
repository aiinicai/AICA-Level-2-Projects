@echo off
REM ============================================================
REM  Builds PDF Studio Pro.exe  -- run this ONCE on ONE Windows PC
REM  that has Python installed. The resulting .exe (in the "dist"
REM  folder) can then be copied to any teammate's PC -- they do
REM  NOT need Python installed to run it.
REM ============================================================

echo Creating a clean build environment...
python -m venv build_env
call build_env\Scripts\activate.bat

echo Installing dependencies (this can take a few minutes)...
pip install --upgrade pip
pip install -r requirements-build.txt

echo Building the .exe...
pyinstaller pdf_studio_pro.spec

echo.
echo ============================================================
echo   DONE. Your .exe is at:  dist\PDF Studio Pro.exe
echo   Copy that single file to teammates' PCs to run it there.
echo ============================================================
pause
