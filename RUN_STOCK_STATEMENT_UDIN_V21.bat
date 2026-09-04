@echo off
setlocal
cd /d "%~dp0"
title Stock Statement + ICAI UDIN Assistant
echo ================================================================
echo  STOCK STATEMENT + ICAI UDIN ASSISTANT
echo ================================================================
echo  Official ICAI login: https://udin.icai.org/ICAI/login
echo.
echo  - Your data is saved in the StockStatementData folder next to
echo    this file. Move or copy the whole folder and the data goes
echo    with it.
echo  - The ICAI username and password come from the CA profile you
echo    pick inside the application.
echo  - The CAPTCHA is shown inside the application, so you do not
echo    need to look at the Edge window.
echo.
echo  Keep this black window open to see the debug log.
echo ================================================================
echo.

if not exist "Stock_Statement_Drawing_Power_UDIN_Integrated_v20.html" (
  echo ERROR: Stock_Statement_Drawing_Power_UDIN_Integrated_v20.html is missing.
  echo Keep it in the same folder as this file.
  pause
  exit /b 1
)

if not exist "RUN_STOCK_STATEMENT_UDIN_V21_FIXED.py" (
  echo ERROR: RUN_STOCK_STATEMENT_UDIN_V21_FIXED.py is missing.
  echo Keep it in the same folder as this file.
  pause
  exit /b 1
)

REM ---------------------------------------------------------------
REM Find Python. The "py" launcher is optional in the installer, so
REM fall back to "python" and then to the usual install folders.
REM ---------------------------------------------------------------
set "PYEXE="
call :tryCommand py
call :tryCommand python
call :tryCommand python3
if not defined PYEXE for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :tryPath "%%~D\python.exe"
if not defined PYEXE for /d %%D in ("%ProgramFiles%\Python3*") do call :tryPath "%%~D\python.exe"
if not defined PYEXE for /d %%D in ("%ProgramFiles(x86)%\Python3*") do call :tryPath "%%~D\python.exe"
if not defined PYEXE for /d %%D in ("C:\Python3*") do call :tryPath "%%~D\python.exe"

if not defined PYEXE (
  echo ERROR: Python 3 not found.
  echo.
  echo Looked for: py, python, python3 on the PATH, and inside
  echo   %LOCALAPPDATA%\Programs\Python\
  echo   %ProgramFiles%\
  echo   C:\Python3*
  echo.
  echo Install Python from https://www.python.org/ and tick
  echo "Add Python to PATH" during the installation.
  pause
  exit /b 1
)

echo Using Python: %PYEXE%

REM ---------------------------------------------------------------
REM Selenium. Only install when it is actually missing, so a slow or
REM offline connection cannot stop an already-working setup.
REM ---------------------------------------------------------------
"%PYEXE%" -c "import selenium" >nul 2>&1
if errorlevel 1 (
  echo Selenium is not installed. Installing it now...
  "%PYEXE%" -m pip install --upgrade selenium
  "%PYEXE%" -c "import selenium" >nul 2>&1
  if errorlevel 1 (
    echo.
    echo ERROR: Selenium could not be installed.
    echo Open Command Prompt as Administrator and run:
    echo     "%PYEXE%" -m pip install --upgrade selenium
    pause
    exit /b 1
  )
) else (
  echo Selenium found. Checking for an update...
  "%PYEXE%" -m pip install --quiet --upgrade selenium >nul 2>&1
)

echo.
echo Starting the assistant...
echo ================================================================
"%PYEXE%" RUN_STOCK_STATEMENT_UDIN_V21_FIXED.py
echo.
echo The assistant has stopped.
echo If auto-fill misbehaved, check udin_autofill_debug.png in this folder.
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
