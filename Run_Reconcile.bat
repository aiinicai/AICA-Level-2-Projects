@echo off
title Free Zone Inbound-Outbound Reconciliation
cd /d "%~dp0"

rem  Usage:
rem    - Double-click this file  -> a window opens to pick the RAW DATA Excel file
rem    - Or drag the raw Excel file onto this file
rem  Output: "<raw file name> - Reconciled.xlsx" in the same folder as the raw file.

if not exist "%~dp0Reconcile.exe" goto python
"%~dp0Reconcile.exe" %*
rem  exit code 0 = done, 1 = reconciliation error (message already shown);
rem  anything else means Windows did not let the EXE start -> use Python instead
if errorlevel 2 (
    echo.
    echo Reconcile.exe could not start on this PC, trying Python instead...
    goto python
)
goto end

:python
where python >nul 2>nul
if errorlevel 1 (
    echo Reconcile.exe could not run and Python is not installed.
    echo Keep Reconcile.exe in the same folder as this BAT file.
    goto end
)
python "%~dp0reconcile.py" %*

:end
echo.
pause
