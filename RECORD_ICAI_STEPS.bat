@echo off
setlocal
cd /d "%~dp0"
title Record ICAI UDIN Steps
echo ================================================================
echo  RECORD YOUR ICAI UDIN STEPS
echo ================================================================
echo.
echo  Edge will open on the ICAI login page.
echo.
echo  Do the whole job BY HAND, exactly the way it should happen:
echo    log in, open Generate UDIN, pick the FRN, the document type,
echo    the certificate type, the date, the figures, the denominations,
echo    the description and the remarks.
echo.
echo  Every click and value is written down as you go, together with
echo  the exact element behind it. Passwords, CAPTCHA and OTP values
echo  are NOT recorded.
echo.
echo  When you are done, just close the Edge window.
echo  The recording is saved in:
echo    StockStatementData\recordings\
echo ================================================================
echo.

if not exist "RUN_STOCK_STATEMENT_UDIN_V21_FIXED.py" (
  echo ERROR: RUN_STOCK_STATEMENT_UDIN_V21_FIXED.py is missing.
  pause
  exit /b 1
)

set "PYEXE="
call :tryCommand py
call :tryCommand python
call :tryCommand python3
if not defined PYEXE for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :tryPath "%%~D\python.exe"
if not defined PYEXE for /d %%D in ("%ProgramFiles%\Python3*") do call :tryPath "%%~D\python.exe"
if not defined PYEXE for /d %%D in ("%ProgramFiles(x86)%\Python3*") do call :tryPath "%%~D\python.exe"
if not defined PYEXE for /d %%D in ("C:\Python3*") do call :tryPath "%%~D\python.exe"

if not defined PYEXE (
  echo ERROR: Python 3 not found. Install it from https://www.python.org/
  echo and tick "Add Python to PATH" during the installation.
  pause
  exit /b 1
)

"%PYEXE%" -c "import selenium" >nul 2>&1
if errorlevel 1 (
  echo Installing Selenium...
  "%PYEXE%" -m pip install --upgrade selenium
)

echo Using Python: %PYEXE%
echo.
echo Starting the recorder...
echo ================================================================
"%PYEXE%" RUN_STOCK_STATEMENT_UDIN_V21_FIXED.py --record
echo.
pause
exit /b 0

REM ---------------------------------------------------------------
:tryCommand
if defined PYEXE goto :eof
where %~1 >nul 2>&1
if errorlevel 1 goto :eof
%~1 -c "import sys; sys.exit(0 if sys.version_info[0]==3 else 1)" >nul 2>&1
if errorlevel 1 goto :eof
set "PYEXE=%~1"
goto :eof

:tryPath
if defined PYEXE goto :eof
if not exist "%~1" goto :eof
"%~1" -c "import sys; sys.exit(0 if sys.version_info[0]==3 else 1)" >nul 2>&1
if errorlevel 1 goto :eof
set "PYEXE=%~1"
goto :eof
