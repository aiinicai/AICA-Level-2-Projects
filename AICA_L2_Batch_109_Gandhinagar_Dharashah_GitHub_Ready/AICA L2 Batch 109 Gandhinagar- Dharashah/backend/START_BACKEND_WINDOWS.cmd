@echo off
cd /d "%~dp0"
echo Installing compatible Python dependencies...
python -m pip install --upgrade pip
python -m pip install --prefer-binary -r requirements.txt
if errorlevel 1 (
  echo Installation failed. Please copy the FIRST package error shown above.
  pause
  exit /b 1
)
echo Starting SmartHire API on port 8000...
python -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
