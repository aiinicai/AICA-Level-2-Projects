@echo off
title What's cooking today? - AI Meal Planner
echo ====================================================================
echo   Starting What's cooking today? (AI Zero-Waste Meal Planner)...
echo ====================================================================
echo.
echo   * LAPTOP / PC ACCESS:   http://127.0.0.1:8000/
echo   * MOBILE PHONE ACCESS:  http://192.168.31.85:8000/
echo.
echo ====================================================================
echo Opening http://127.0.0.1:8000 on your laptop...
start http://127.0.0.1:8000/
python manage.py runserver 0.0.0.0:8000
if %errorlevel% neq 0 (
    echo.
    echo Trying py launcher...
    py manage.py runserver 0.0.0.0:8000
)
pause
