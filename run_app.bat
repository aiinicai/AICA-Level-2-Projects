@echo off
REM One-click launcher (Windows). Uses Python 3.12 / 3.11 / 3.13 if installed (Python 3.14+ lacks packages for some libraries).
cd /d "%~dp0"
set PYV=
for %%V in (3.12 3.11 3.13 3.10) do (
  if not defined PYV (
    py -%%V -c "import sys" >nul 2>&1 && set PYV=%%V
  )
)
if not defined PYV (
  echo.
  echo No supported Python found. Please install Python 3.12 from https://www.python.org/downloads/release/python-3128/
  echo Tick "Add python.exe to PATH" during installation, then run this file again.
  pause
  exit /b 1
)
echo Using Python %PYV%
if not exist .venv\Scripts\activate.bat (
  echo Creating virtual environment and installing packages - first run only, takes a few minutes ...
  py -%PYV% -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  if errorlevel 1 (
    echo Installation failed - see the message above.
    pause
    exit /b 1
  )
) else (
  call .venv\Scripts\activate.bat
)
streamlit run app.py
pause
