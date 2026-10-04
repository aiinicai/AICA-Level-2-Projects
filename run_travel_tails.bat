@echo off
title Travel Tails - Smart Travel Itinerary & Package Downloader
echo ========================================================
echo   Launching Travel Tails Desktop Application...
echo ========================================================
python travel_tails.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with an error or Python is not in PATH.
    pause
)
