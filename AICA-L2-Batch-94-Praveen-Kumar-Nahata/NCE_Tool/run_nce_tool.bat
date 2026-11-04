@echo off
title NCE Tool
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo Python is not installed. Install it once from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^), then run this file again.
    pause
    exit /b
  )
  set PY=py
) else (
  set PY=python
)
%PY% -c "import openpyxl" >nul 2>nul
if errorlevel 1 (
  echo Installing the Excel library ^(one-time, needs internet^)...
  %PY% -m pip install --disable-pip-version-check openpyxl
)
%PY% -c "import pypdf" >nul 2>nul
if errorlevel 1 %PY% -m pip install --disable-pip-version-check pypdf
%PY% -c "import pyodbc" >nul 2>nul
if errorlevel 1 %PY% -m pip install --disable-pip-version-check pyodbc
%PY% nce_tool.py
if errorlevel 1 pause
