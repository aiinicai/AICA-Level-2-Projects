@echo off
rem Run once on EACH PC that uses classic Outlook. No administrator rights needed.
cd /d "%~dp0"
if not exist "VKL_Outlook_Helper.exe" (echo VKL_Outlook_Helper.exe not found next to this file. & pause & exit /b 1)
"VKL_Outlook_Helper.exe" --install
