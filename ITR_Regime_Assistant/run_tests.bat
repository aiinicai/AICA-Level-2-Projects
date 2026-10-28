@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe goto missing
.venv\Scripts\python.exe -m unittest discover -v
pause
exit /b
:missing
echo Run install.bat first.
pause
