@echo off
REM Builds dist\GXVAN\GXVAN.exe. Needs Python 3.12 or 3.13 from python.org (tick "Add to PATH" / py launcher).
cd /d "%~dp0"
py -3.12 -m venv .buildenv || py -3.13 -m venv .buildenv || (echo Install Python 3.12 from python.org first & pause & exit /b 1)
.buildenv\Scripts\python -m pip install --upgrade pip
.buildenv\Scripts\python -m pip install -r requirements.txt pyinstaller
.buildenv\Scripts\python -m pip uninstall -y opencv-python
.buildenv\Scripts\python -m pip install opencv-python-headless
.buildenv\Scripts\python -m PyInstaller GXVAN.spec --noconfirm
echo.
echo Done. Your app is in: %~dp0dist\GXVAN\GXVAN.exe
pause
