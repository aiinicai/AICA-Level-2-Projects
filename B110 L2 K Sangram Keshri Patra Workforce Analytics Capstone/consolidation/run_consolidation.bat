@echo off
cd /d "%~dp0"
set /p PERIOD=Enter reporting month (e.g. Nov-2026): 
python consolidate.py --period %PERIOD% --input .\inbox --output .\output
echo.
echo Done. Open the output folder for the consolidated workbook.
pause
