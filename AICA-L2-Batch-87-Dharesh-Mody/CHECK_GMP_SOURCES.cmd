@echo off
setlocal
cd /d "%~dp0"
set /p COMPANY=Company to look for (press Enter for "SS Retail"): 
if "%COMPANY%"=="" set COMPANY=SS Retail
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 check_gmp_sources.py "%COMPANY%" > IPO_Compass_GMP_Check.txt 2>&1
goto show_result
:use_python
python check_gmp_sources.py "%COMPANY%" > IPO_Compass_GMP_Check.txt 2>&1
:show_result
type IPO_Compass_GMP_Check.txt
echo.
echo Output saved to IPO_Compass_GMP_Check.txt - send it if the RESULT line does not solve it.
pause
