@echo off
title IPO_Tracker - install libraries
echo Installing libraries for IPO_Tracker ...
python -m pip install --upgrade pip
python -m pip install PyQt5 requests beautifulsoup4 pyinstaller
echo.
echo Done. You can now run:  python ipo_tracker.py
echo Or build the EXE with:  build_exe.bat
pause
