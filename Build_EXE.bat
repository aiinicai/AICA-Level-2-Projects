@echo off
setlocal EnableExtensions
title Vendor Name Matching - Build EXE
cd /d "%~dp0"

rem ==========================================================
rem  Build_EXE.bat   (version 2)
rem  Turns Vendor_Name_Matching.py into a single Windows EXE.
rem  Keep this file and Vendor_Name_Matching.py in the same folder,
rem  then double-click this file. Needs Python 3.8+ and internet (first run only).
rem
rem  The build itself runs in a SHORT local folder (not OneDrive), because
rem  PyQt5 has very long internal file names and a long OneDrive path can
rem  break the installation. Only the finished EXE is copied back here.
rem ==========================================================

set "APP_NAME=Vendor Name Matching"
set "SRC_SCRIPT="
set "OUTDIR=%~dp0Vendor_Name_Matching_EXE"

if defined LOCALAPPDATA (set "BASE=%LOCALAPPDATA%\VNM_Build") else (set "BASE=C:\VNM_Build")
set "SRCDIR=%BASE%\src"
set "ENVDIR=%BASE%\env"
set "WORKDIR=%BASE%\work"
set "DISTDIR=%BASE%\dist"

echo ==========================================================
echo   %APP_NAME% - EXE builder
echo ==========================================================
echo.

rem Find the tool. Order: a file dragged onto this bat, the exact name, then any
rem Python file in this folder whose name contains Vendor and Match (newest first),
rem so names like "Vendor_Name_Matching (1).py" or "Vendor Name Matching.py" also work.
if not "%~1"=="" if exist "%~1" set "SRC_SCRIPT=%~f1"
if not defined SRC_SCRIPT if exist "%~dp0Vendor_Name_Matching.py" set "SRC_SCRIPT=%~dp0Vendor_Name_Matching.py"
if not defined SRC_SCRIPT (
    for /f "delims=" %%F in ('dir /b /a-d /o-d "%~dp0*Vendor*Match*.py" 2^>nul') do if not defined SRC_SCRIPT set "SRC_SCRIPT=%~dp0%%F"
)
if not defined SRC_SCRIPT (
    echo ERROR: The tool's Python file was not found in the folder of this bat file:
    echo "%~dp0"
    echo.
    echo Files in this folder with Vendor in the name:
    dir /b "%~dp0*Vendor*" 2>nul
    echo.
    echo What to do:
    echo   1. Copy Vendor_Name_Matching.py into the same folder as this bat file, or
    echo   2. Drag your Python file and drop it onto this bat file.
    echo If the name above ends with .py.txt, rename it to end with .py only.
    goto :fail
)
echo Using the tool file:
echo "%SRC_SCRIPT%"
echo.

echo [1/5] Looking for Python...
set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo ERROR: Python was not found on this computer.
    echo Install Python 3.8 or newer from https://www.python.org/downloads/
    echo During setup, tick "Add python.exe to PATH", then run this file again.
    goto :fail
)
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.8 or newer is needed. Please install a newer version.
    goto :fail
)
%PY% --version
echo Build folder: "%BASE%"

echo.
echo [2/5] Preparing a clean build environment (first run takes a few minutes)...
if not exist "%BASE%" mkdir "%BASE%"
if not exist "%SRCDIR%" mkdir "%SRCDIR%"
copy /y "%SRC_SCRIPT%" "%SRCDIR%\Vendor_Name_Matching.py" >nul
if errorlevel 1 (
    echo ERROR: Could not copy the tool into the build folder.
    goto :fail
)
rem Remove the environment an earlier version of this file may have left next to the script
if exist "%~dp0build_env" rmdir /s /q "%~dp0build_env" >nul 2>&1
if not exist "%ENVDIR%\Scripts\python.exe" (
    %PY% -m venv "%ENVDIR%"
    if errorlevel 1 (
        echo ERROR: Could not create the build environment.
        goto :fail
    )
)
set "VPY=%ENVDIR%\Scripts\python.exe"
"%VPY%" -m pip install --upgrade pip >nul 2>&1

echo.
echo [3/5] Installing the libraries the tool needs...
echo       (the tool's own Python code installs them; if that fails, the details are shown)
cd /d "%SRCDIR%"
"%VPY%" -c "import Vendor_Name_Matching" >nul 2>&1
if errorlevel 1 (
    echo.
    echo The quiet install did not finish. Trying again and showing every detail...
    "%VPY%" -m pip install PyQt5 openpyxl reportlab
    if errorlevel 1 (
        echo.
        echo Retrying for company networks that inspect secure connections...
        "%VPY%" -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org PyQt5 openpyxl reportlab
        if errorlevel 1 (
            echo.
            echo ERROR: The libraries could not be installed. Read the message above.
            echo   - "Could not find a version" or "connection" or "SSL": internet, proxy or firewall.
            echo     Ask IT to allow pypi.org and files.pythonhosted.org, or try another network.
            echo   - Any other message: send a screenshot of this window.
            goto :fail
        )
    )
    "%VPY%" -c "import Vendor_Name_Matching"
    if errorlevel 1 (
        echo ERROR: The libraries installed but the tool still could not load them.
        goto :fail
    )
)
echo Libraries are ready.

echo.
echo [4/5] Installing the EXE builder (PyInstaller)...
"%VPY%" -m pip install pyinstaller
if errorlevel 1 (
    echo.
    echo Retrying for company networks that inspect secure connections...
    "%VPY%" -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org pyinstaller
    if errorlevel 1 (
        echo ERROR: PyInstaller could not be installed. Read the message above.
        goto :fail
    )
)

echo.
echo [5/5] Building the EXE (this can take 2 to 5 minutes)...
if exist "%DISTDIR%" rmdir /s /q "%DISTDIR%"
if exist "%WORKDIR%" rmdir /s /q "%WORKDIR%"
"%VPY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "%APP_NAME%" ^
    --collect-submodules reportlab ^
    --distpath "%DISTDIR%" --workpath "%WORKDIR%" --specpath "%WORKDIR%" ^
    "%SRCDIR%\Vendor_Name_Matching.py"
if errorlevel 1 (
    echo ERROR: The EXE could not be built. Scroll up to read the reason.
    goto :fail
)
if not exist "%DISTDIR%\%APP_NAME%.exe" (
    echo ERROR: The EXE was not created.
    goto :fail
)

if not exist "%OUTDIR%" mkdir "%OUTDIR%"
copy /y "%DISTDIR%\%APP_NAME%.exe" "%OUTDIR%\" >nul
if errorlevel 1 (
    echo ERROR: Could not copy the EXE. If it is running, close it and try again.
    goto :fail
)
if exist "%~dp0Third_Party_Licenses.txt" copy /y "%~dp0Third_Party_Licenses.txt" "%OUTDIR%\" >nul

rmdir /s /q "%DISTDIR%" >nul 2>&1
rmdir /s /q "%WORKDIR%" >nul 2>&1

echo.
echo ==========================================================
echo   DONE
echo   EXE saved in this folder:
echo   "%OUTDIR%"
echo   Share the file "%APP_NAME%.exe" with your team. No Python or library
echo   installation is needed on their computers.
echo   The build folder "%BASE%" can be kept for faster rebuilds or deleted.
echo ==========================================================
explorer "%OUTDIR%"
echo.
pause
exit /b 0

:fail
echo.
echo Build stopped. No EXE was created.
echo.
pause
exit /b 1
