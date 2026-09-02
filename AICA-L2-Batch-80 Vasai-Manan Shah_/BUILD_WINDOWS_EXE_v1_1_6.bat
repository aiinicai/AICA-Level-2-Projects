@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ==============================================================
echo ICFR Testing AI Assistant v1.1.6 - LEAN Windows EXE Builder
echo ==============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python was not found on PATH.
  pause
  exit /b 1
)

set "TESSERACT_HOME="
set "TESSERACT_EXE="
for /f "delims=" %%I in ('where tesseract 2^>nul') do if not defined TESSERACT_EXE set "TESSERACT_EXE=%%I"
if defined TESSERACT_EXE for %%I in ("%TESSERACT_EXE%") do set "TESSERACT_HOME=%%~dpI"
if not defined TESSERACT_HOME if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set "TESSERACT_HOME=C:\Program Files\Tesseract-OCR"
if not defined TESSERACT_HOME if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" set "TESSERACT_HOME=C:\Program Files (x86)\Tesseract-OCR"

if not defined TESSERACT_HOME (
  echo ERROR: Tesseract OCR could not be located.
  echo Run: where tesseract
  pause
  exit /b 1
)
if not exist "%TESSERACT_HOME%\tessdata\eng.traineddata" (
  echo ERROR: English OCR data was not found at:
  echo %TESSERACT_HOME%\tessdata\eng.traineddata
  pause
  exit /b 1
)

echo Tesseract: %TESSERACT_HOME%
echo.

if not exist ".exe-build-venv\Scripts\python.exe" (
  echo [1/6] Creating isolated build environment...
  python -m venv ".exe-build-venv" || goto :fail
)

echo [2/6] Updating build tools...
call ".exe-build-venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel || goto :fail

echo [3/6] Installing only required runtime/build packages...
call ".exe-build-venv\Scripts\python.exe" -m pip install -r requirements-exe-v116.txt || goto :fail

echo [4/6] Cleaning previous build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [5/6] Building lean single-file EXE...
call ".exe-build-venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean ICFR_Testing_AI_Assistant_v1_1_6_LEAN.spec || goto :fail

echo [6/6] Verifying artifact...
set "EXE=dist\ICFR_Testing_AI_Assistant_v1_1_6.exe"
if not exist "%EXE%" (
  echo ERROR: Expected EXE was not created.
  goto :fail
)
for %%F in ("%EXE%") do (
  set /a SIZE_MB=%%~zF/1048576
  echo EXE size: %%~zF bytes
)
certutil -hashfile "%EXE%" SHA256

echo.
echo Build completed successfully:
echo %CD%\%EXE%
echo.
if defined SIZE_MB (
  if %SIZE_MB% GTR 100 (
    echo NOTE: The EXE is above 100 MB on this build. Review PyInstaller warn/build output.
    echo v1.1.6 already removes Matplotlib, Numpy and ReportLab and bundles only English OCR data.
  ) else (
    echo TARGET MET: EXE is approximately %SIZE_MB% MB and below 100 MB.
  )
)
echo.
echo IMPORTANT: The executable continues using:
echo %%LOCALAPPDATA%%\DigiLens_IFCR_Testing

echo Existing inquiry, response, evidence, testing and exception data are not packaged,
echo reset or migrated away; the new EXE opens the same local data workspace.
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. Review the error above.
pause
exit /b 1
