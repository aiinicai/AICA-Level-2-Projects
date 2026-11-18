@echo off
cd /d "%~dp0"
if exist dist\GSTLookup.exe (
 dist\GSTLookup.exe %*
) else (
 call run.bat %*
)
if errorlevel 1 pause
