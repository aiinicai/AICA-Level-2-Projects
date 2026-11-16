@echo off
REM Builds the Windows desktop app on this PC. Needs Python 3.12 or newer from python.org.
cd /d "%~dp0"
echo.
echo  [1/3] Installing packages (first time takes a few minutes)...
python -m pip install --disable-pip-version-check -r requirements-desktop.txt
if errorlevel 1 goto failed
echo.
echo  [2/3] Building the app (takes 3-8 minutes)...
python -m PyInstaller --noconfirm --clean CAPracticeManager.spec
if errorlevel 1 goto failed
echo.
echo  [3/3] Making the installer...
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
  %ISCC% /Q installer.iss
  echo   Installer ready: dist\CAPracticeManager-Setup.exe  ^(share this one file with colleagues^)
) else (
  echo   Skipped: install the free Inno Setup 6 from jrsoftware.org to also get a Setup.exe installer.
)
echo.
echo  ============================================================
echo   DONE. The app is in dist\CAPracticeManager\CAPracticeManager.exe
echo  ============================================================
pause
exit /b 0
:failed
echo.
echo  Something went wrong. Scroll up to see the error message.
pause
exit /b 1
