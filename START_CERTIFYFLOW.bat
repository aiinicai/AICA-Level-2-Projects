@echo off
setlocal
title CertifyFlow and Saral Bridge
cd /d "%~dp0"

set PYCMD=
py -3 -c "import tkinter, sys; assert sys.version_info >= (3, 8)" >nul 2>nul
if not errorlevel 1 set PYCMD=py -3
if defined PYCMD goto run
python -c "import tkinter, sys; assert sys.version_info >= (3, 8)" >nul 2>nul
if not errorlevel 1 set PYCMD=python
if defined PYCMD goto run
goto nopython

:run
echo Starting CertifyFlow... keep this small window open while using the app.
%PYCMD% certifyflow.py
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo [ERROR] CertifyFlow stopped with an error. Please send me the message above.
pause
exit /b 1

:nopython
echo [ERROR] Python 3.8 or newer with Tkinter was not found.
echo.
echo 1. Download Python from https://www.python.org/downloads/windows/
echo 2. In the installer TICK "Add python.exe to PATH" and keep "tcl/tk and IDLE" selected.
echo 3. Finish the install, then double-click this file again.
echo.
pause
exit /b 1
