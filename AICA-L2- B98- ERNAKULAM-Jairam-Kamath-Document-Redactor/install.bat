@echo off
title RedactIn60 - Installer
echo.
echo  Installing RedactIn60 ...
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo  Python is not installed. Opening the download page.
  echo  Install Python 3 ^(tick "Add Python to PATH"^), then run this file again.
  start https://www.python.org/downloads/
  pause
  exit /b 1
)

%PY% -m pip install --upgrade pymupdf "python-docx>=1.2" openpyxl tkinterdnd2
if errorlevel 1 (
  echo.
  echo  Package install failed. Check the internet connection and try again.
  pause
  exit /b 1
)

%PY% "%~dp0install_helper.py"
echo.
echo  Done. Double-click "RedactIn60" on your Desktop.
pause
