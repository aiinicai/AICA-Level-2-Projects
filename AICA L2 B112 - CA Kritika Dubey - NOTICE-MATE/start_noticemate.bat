@echo off
rem Kept for compatibility. NOTICE-MATE now opens in its own window without Command Prompt windows.
cd /d "%~dp0"
start "" wscript "%~dp0NOTICE-MATE.vbs"
