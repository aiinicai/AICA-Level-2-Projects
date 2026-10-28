@echo off
REM One-time setup for Windows: creates a virtual environment and installs the packages.
REM Requires Python 3.10 or newer from https://www.python.org (tick "Add python.exe to PATH" when installing).
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.10+ from https://www.python.org and run this file again.
  pause
  exit /b 1
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
  echo Python 3.10 or newer is required.
  pause
  exit /b 1
)
if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 ( echo Could not create the virtual environment. & pause & exit /b 1 )
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Package installation failed. Check your internet connection and read the message above.
  pause
  exit /b 1
)
echo.
echo Setup finished. OPTIONAL: to read scanned (image-only) PDFs install the Tesseract OCR program
echo (for example the UB Mannheim Windows build) and add it to PATH. Typed/text PDFs and Excel/CSV need nothing extra.
echo Start the tool by double-clicking run_app.bat
pause
