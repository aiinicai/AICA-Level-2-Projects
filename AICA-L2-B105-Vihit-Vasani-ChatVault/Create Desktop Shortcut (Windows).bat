@echo off
title ChatVault - create desktop shortcut
echo Creating the ChatVault shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0assets\create-shortcut.ps1"
echo.
pause
