@echo off
title Bank Advice to SAP Uploader
cd /d "%~dp0"
REM Processes every new advice in "Bank advice\Statements" automatically:
REM   Posted / Already posted -> Bank advice\Posted ,  Not posted -> Bank advice\Not Posted
REM Close Bank Uploader.xlsx and Uploader -Posted.xlsx in Excel before running.
where python >nul 2>nul
if %errorlevel%==0 (
    python bank_advice_processor.py %*
) else (
    py bank_advice_processor.py %*
)
echo.
echo Press any key to close this window.
pause >nul
