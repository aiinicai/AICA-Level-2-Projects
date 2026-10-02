@echo off
setlocal
title LookThrough - reset a password
cd /d "%~dp0"
echo.
echo  LookThrough - reset a password on this PC
echo  -----------------------------------------
echo  Use this if a password is forgotten or an account is locked.
echo  It only works on this PC and every reset is written to the audit trail.
echo.
if not exist ".venv\Scripts\python.exe" (
  echo  The app has not been set up yet. Run Start_LookThrough.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" bridge\auth.py reset %*
echo.
pause
