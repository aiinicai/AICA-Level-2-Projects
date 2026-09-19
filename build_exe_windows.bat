@echo off
setlocal
cd /d "%~dp0"
echo Optional Windows build. PyInstaller is an additional BUILD-ONLY tool.
echo This build recipe has NOT been executed or verified in this delivery.
python -m venv .build_venv
if errorlevel 1 goto failed
call .build_venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
python -m pip install "pyinstaller>=6.10,<7"
if errorlevel 1 goto failed
python -m PyInstaller --noconfirm --clean --onefile --windowed --name TrialBalanceAnalyzer --collect-all openpyxl app.py
if errorlevel 1 goto failed
echo.
echo Build completed. Test dist\TrialBalanceAnalyzer.exe on your Windows laptop.
echo Follow the manual UI checks in README.md before using this build.
pause
exit /b 0
:failed
echo Build failed. Review the error messages above.
echo Requires Windows, Python with Tcl/Tk, and internet for dependency installation.
echo You can run the source application with: python app.py
pause
exit /b 1
