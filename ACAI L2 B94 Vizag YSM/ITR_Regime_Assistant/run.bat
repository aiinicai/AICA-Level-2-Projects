@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe goto missing
.venv\Scripts\python.exe -c "import customtkinter,openpyxl"
if errorlevel 1 goto missing
.venv\Scripts\python.exe app.py
if errorlevel 1 pause
exit /b
:missing
echo Run install.bat first to create this project's environment and install dependencies.
pause
