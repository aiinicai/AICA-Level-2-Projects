@echo off
REM Builds CA-Task-Mitra.exe  (needs Python 3.10+ on this PC and internet once, for PyInstaller)
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --name CA-Task-Mitra --add-data "web;web" --collect-submodules modules --collect-submodules core run.py
echo.
echo Done. Your program is dist\CA-Task-Mitra.exe  - double-click it. Data is kept in a "data" folder beside the EXE.
pause
