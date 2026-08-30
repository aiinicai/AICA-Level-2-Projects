@echo off
setlocal
cd /d "%~dp0"
title Red Flag Engine - Forensic Accounting

REM This file does one thing: find a Python that starts, and hand over to
REM scripts\launch.py, which handles everything else. All the conditional
REM logic lives there, where the error messages can be useful.

python -c "import sys" >nul 2>&1
if not errorlevel 1 goto USE_PYTHON

py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 goto USE_PY3

python3 -c "import sys" >nul 2>&1
if not errorlevel 1 goto USE_PYTHON3

echo.
echo ===============================================================
echo   No Python installation was found on this computer.
echo ===============================================================
echo.
echo   Install Python from https://www.python.org/downloads/
echo   During setup, TICK the box "Add python.exe to PATH".
echo   Then run this file again.
echo.
goto END

:USE_PYTHON
python "scripts\launch.py"
goto END

:USE_PY3
py -3 "scripts\launch.py"
goto END

:USE_PYTHON3
python3 "scripts\launch.py"
goto END

:END
echo.
pause
endlocal
