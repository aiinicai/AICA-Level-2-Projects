@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 main.py
) else (
    python main.py
)
echo.
echo If you saw an error above, verify that Python 3.9+ is installed.
pause
