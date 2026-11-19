@echo off
setlocal
set "NW_SETUP=%~dp0Setup Net Worth Office.ps1"
powershell.exe -NoProfile -Command "Start-Process powershell.exe -Verb RunAs -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File ' + [char]34 + $env:NW_SETUP + [char]34)"
