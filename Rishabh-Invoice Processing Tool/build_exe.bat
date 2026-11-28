@echo off
REM Builds dist\IPT (PyInstaller) and, if Inno Setup 6 is installed, dist\IPT_Setup_<version>.exe
REM Log: build_log.txt
cd /d "%~dp0"
echo Building IPT... (log: build_log.txt)
(
  echo === IPT build %date% %time% ===
  ".venv\Scripts\python.exe" -m pip install --timeout 120 "pyinstaller>=6,<7"
  set QT_QPA_PLATFORM=offscreen
  ".venv\Scripts\python.exe" -m pytest -q
  ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean installer\ipt.spec
  if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo Copying Tesseract into the build
    xcopy /E /I /Y "C:\Program Files\Tesseract-OCR" "dist\IPT\tesseract" >nul
  ) else (
    echo Tesseract not found - the build will need Tesseract installed separately for scanned bills
  )
  for /f %%v in ('".venv\Scripts\python.exe" -c "import ipt; print(ipt.__version__)"') do set IPT_VERSION=%%v
  if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\ipt.iss
  ) else (
    echo Inno Setup 6 not installed - only the dist\IPT folder was built
  )
  echo === BUILD FINISHED ===
) > build_log.txt 2>&1
type build_log.txt | findstr /C:"passed" /C:"failed" /C:"ERROR" /C:"Successful" /C:"FINISHED" /C:"not installed" /C:"not found"
pause
