@echo off
rem Double-click to start. Nothing to install - Python, Qt and the OCR engine are inside this folder.
cd /d "%~dp0program"
if not exist "%~dp0python\pythonw.exe" goto missing
start "" "%~dp0python\pythonw.exe" "%~dp0program\main_qt.py"
exit /b 0
:missing
echo.
echo  The folder "python" is missing next to this file.
echo  Right-click the downloaded zip ^> Extract All, then run this file from the EXTRACTED folder
echo  (do not run it from inside the zip).
echo.
pause
