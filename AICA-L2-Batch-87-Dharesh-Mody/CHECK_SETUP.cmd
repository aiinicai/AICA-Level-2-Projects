@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 diagnostics.py > IPO_Compass_Diagnostics.txt 2>&1
goto show_result
:use_python
python diagnostics.py > IPO_Compass_Diagnostics.txt 2>&1
:show_result
type IPO_Compass_Diagnostics.txt
echo.
echo Please send IPO_Compass_Diagnostics.txt if startup fails.
pause
