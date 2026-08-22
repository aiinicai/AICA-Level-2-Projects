@echo off
title Non Ind AS Schedule III Financial Statements Builder
cd /d "%~dp0"
echo.
echo ============================================================
echo  Non Ind AS Schedule III Financial Statements Builder
echo ============================================================
echo  Starting server... please wait.
echo  Local URL    : http://127.0.0.1:5000
echo  Network URL  : (displayed in console after startup)
echo ============================================================
echo.
python src/app.py
pause
