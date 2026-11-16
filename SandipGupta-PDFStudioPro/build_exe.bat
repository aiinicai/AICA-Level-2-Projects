@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title PDF Studio Pro - build the Windows program
set "SRC=%~dp0"
set "WORK=%LOCALAPPDATA%\PDFStudioProBuild"
set "PYTHONWARNINGS=ignore"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
echo ============================================================
echo   PDF Studio Pro - build the Windows program (about 10-20 min)
echo   Needs: Python 3.9 - 3.13 for Windows, and internet (once).
echo.
echo   Tips: do NOT click inside this window while it runs (a click
echo   pauses it - press Enter if it looks frozen). Some steps print
echo   nothing for several minutes; that is normal.
echo ============================================================
echo.

if not exist "pdf_studio_pro.py" (
  echo ERROR: pdf_studio_pro.py must be in the same folder as this file.
  goto :fail
)

rem ---------- 0. work on the LOCAL disk (network drives make the build hang) ----------
if /i "%SRC%"=="%WORK%\" goto :worklocal
echo Preparing a local build folder: %WORK%
if not exist "%WORK%" mkdir "%WORK%"
robocopy "%~dp0." "%WORK%" pdf_studio_pro.py admin_settings.json /NJH /NJS /NDL /NFL /NP >nul
if exist "%SRC%fonts" robocopy "%SRC%fonts" "%WORK%\fonts" /E /NJH /NJS /NDL /NFL /NP >nul
if exist "%SRC%tesseract\tesseract.exe" robocopy "%SRC%tesseract" "%WORK%\tesseract" /E /NJH /NJS /NDL /NFL /NP >nul
if not exist "%WORK%\pdf_studio_pro.py" (
  echo ERROR: could not copy the files to !WORK!
  goto :fail
)
:worklocal
cd /d "%WORK%"
if errorlevel 1 (
  echo ERROR: could not open !WORK!
  goto :fail
)
if exist dist rmdir /s /q dist
if exist PDFStudioPro_Windows.zip del PDFStudioPro_Windows.zip

rem ---------- 1. find a suitable Python (3.12 preferred) ----------
set "PY="
for %%V in (3.12 3.11 3.13 3.10 3.9) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
  )
)
if not defined PY (
  python -c "import sys; assert (3,9) <= sys.version_info[:2] <= (3,13)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo ERROR: Python 3.9 - 3.13 was not found.
  echo Install it from https://www.python.org/downloads/windows/  and tick "Add python.exe to PATH", then run this file again.
  goto :fail
)
echo Using Python: %PY%
%PY% --version

rem ---------- 2. clean private build environment ----------
if not exist "build_venv\Scripts\python.exe" (
  echo Creating build environment...
  %PY% -m venv build_venv
  if errorlevel 1 goto :fail
)
set "VP=%WORK%\build_venv\Scripts\python.exe"
if exist build_warnings.txt del build_warnings.txt

echo.
echo Installing build tools and required libraries...
"%VP%" -m pip install --upgrade pip
"%VP%" -m pip install pyinstaller "PyQt5>=5.15,<5.16" "PyMuPDF>=1.25,<3"
if errorlevel 1 (
  echo ERROR: the required libraries could not be installed. Check the internet connection and try again.
  goto :fail
)

echo.
echo Installing feature libraries (a failure only switches off that feature)...
call :opt "Pillow>=10,<13"
call :opt "numpy>=1.24,<3"
call :opt "opencv-python-headless>=4.8,<6"
call :opt "pytesseract>=0.3.10,<0.4"
call :opt "openpyxl>=3.1,<4"
call :opt "python-docx>=1.1,<2"
call :opt "python-pptx>=1.0,<2"
call :opt "pdf2docx>=0.5.8,<0.6"
call :opt "qrcode>=7.4,<9"
call :opt "python-barcode>=0.15,<0.17"
call :opt "pyhanko>=0.25,<1"
call :opt "requests"
call :opt "xsdata"
call :opt "python-pkcs11>=0.7,<1"
call :opt "tzdata"

rem ---------- 3. choose what to collect (only packages that really installed) ----------
rem NOTE: pymupdf is NOT collected with --collect-all: newer PyMuPDF drags in an
rem unused AI layout add-on (onnxruntime) that can hang or crash the build.
set "EXTRA="
for %%M in (pyhanko pyhanko_certvalidator pkcs11 pdf2docx docx pptx openpyxl cv2 barcode qrcode pytesseract PIL tzdata tzlocal) do (
  "%VP%" -c "import %%M" >nul 2>&1 && set "EXTRA=!EXTRA! --collect-all %%M"
)

rem ---------- 4. build ----------
echo.
echo Building PDFStudioPro (this is the long step - lines keep appearing, please wait)...
"%VP%" -m PyInstaller --noconfirm --clean --windowed --name PDFStudioPro !EXTRA! --hidden-import PIL --hidden-import pytesseract --hidden-import qrcode --hidden-import barcode --exclude-module pymupdf.layout --exclude-module pymupdf_layout --exclude-module pymupdf4llm --exclude-module onnxruntime --exclude-module networkx --exclude-module tkinter pdf_studio_pro.py
if errorlevel 1 goto :fail
if not exist "dist\PDFStudioPro\PDFStudioPro.exe" (
  echo ERROR: the build finished but PDFStudioPro.exe was not created.
  goto :fail
)
rem remove the unused AI layout add-on data (about 50 MB)
if exist "dist\PDFStudioPro\_internal\pymupdf\layout" rmdir /s /q "dist\PDFStudioPro\_internal\pymupdf\layout"

rem ---------- 5. add the external parts next to the exe ----------
echo.
echo Adding fonts, settings and Tesseract OCR (if available)...
if exist "fonts" xcopy /e /i /y "fonts" "dist\PDFStudioPro\fonts" >nul
if exist "admin_settings.json" copy /y "admin_settings.json" "dist\PDFStudioPro\" >nul

set "TESS="
if exist "tesseract\tesseract.exe" set "TESS=%WORK%\tesseract"
if not defined TESS if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set "TESS=C:\Program Files\Tesseract-OCR"
if not defined TESS if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" set "TESS=C:\Program Files (x86)\Tesseract-OCR"
if not defined TESS if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" set "TESS=%LOCALAPPDATA%\Programs\Tesseract-OCR"
if defined TESS (
  echo Bundling Tesseract from: !TESS!
  xcopy /e /i /y "!TESS!" "dist\PDFStudioPro\tesseract" >nul
) else (
  echo NOTE: Tesseract OCR was not found, so OCR will NOT be bundled.
  echo       Install it ^(UB-Mannheim build, with Hindi/Marathi etc. language packs^) and run this file again.
)

rem ---------- 6. zip for sharing ----------
echo.
echo Creating the zip for your team...
tar -a -c -f PDFStudioPro_Windows.zip -C dist PDFStudioPro
if errorlevel 1 (
  echo WARNING: zip could not be created automatically. Zip the folder dist\PDFStudioPro yourself.
)

rem ---------- 7. copy the results back next to this file ----------
if /i not "%SRC%"=="%WORK%\" (
  echo.
  echo Copying the finished program back to !SRC! ...
  if exist PDFStudioPro_Windows.zip copy /y PDFStudioPro_Windows.zip "!SRC!" >nul
  robocopy "dist\PDFStudioPro" "!SRC!dist\PDFStudioPro" /E /NJH /NJS /NDL /NFL /NP >nul
)

echo.
echo ============================================================
echo   DONE
echo   Program folder : %SRC%dist\PDFStudioPro   (run PDFStudioPro.exe)
echo   To share       : %SRC%PDFStudioPro_Windows.zip
echo   (a copy also stays in %WORK%)
if exist build_warnings.txt (
  echo.
  echo   These optional libraries did NOT install, so their features are OFF:
  type build_warnings.txt
)
echo ============================================================
echo.
choice /m "Start the program now to test it"
if not errorlevel 2 start "" "%WORK%\dist\PDFStudioPro\PDFStudioPro.exe"
pause
exit /b 0

:opt
"%VP%" -m pip install %1
if errorlevel 1 (
  echo   FAILED: "%~1"
  echo   "%~1">>build_warnings.txt
)
exit /b 0

:fail
echo.
echo *** BUILD STOPPED - see the messages above. ***
pause
exit /b 1
