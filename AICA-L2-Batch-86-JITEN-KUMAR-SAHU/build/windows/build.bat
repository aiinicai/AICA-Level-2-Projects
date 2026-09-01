@echo off
setlocal enabledelayedexpansion

REM =============================================================
REM  ClientLedger India - Windows build script
REM  Run this ON A WINDOWS MACHINE with Python 3.11+ installed.
REM  Produces: build\windows\dist\ClientLedgerIndia\  (the app folder)
REM  Then run Inno Setup on installer.iss to get the single .exe installer.
REM
REM  INCREMENTAL BY DEFAULT: after the first successful run, the
REM  virtual environment (build_venv) and the downloaded Chromium
REM  browser are BOTH reused automatically on every later run - only
REM  the actual app is rebuilt from your current source files. Nothing
REM  is re-downloaded. Do not manually delete build_venv, dist, or
REM  work between rebuilds; there is no need to, and doing so throws
REM  away the downloaded Chromium (~150-300MB) and everything pip
REM  installed, forcing a slow, data-hungry re-download next time.
REM
REM  Only if you genuinely suspect the environment itself is broken
REM  (not just your app code), run:   build.bat clean
REM  which wipes build_venv and re-downloads everything from scratch.
REM
REM  This window stays open no matter what happens - if a step fails
REM  you will see an [ERROR] message and a "Press any key" prompt
REM  instead of the window just closing.
REM =============================================================

set "APP_DIR=%~dp0..\..\app"

echo ================================================================
echo   ClientLedger India - Windows Build
echo ================================================================
echo.

cd /d "%APP_DIR%"
if errorlevel 1 (
    echo [ERROR] Could not find the app folder at: %APP_DIR%
    goto :fail
)
echo Working in: %cd%
echo.

if /i "%~1"=="clean" (
    echo Clean build requested - removing existing environment...
    if exist "build_venv" rmdir /s /q "build_venv"
    echo Done. This run will re-download Chromium and reinstall dependencies.
    echo.
)

REM -- Locate a working Python -------------------------------------
set "PYEXE="
python --version >nul 2>&1
if not errorlevel 1 set "PYEXE=python"
if not defined PYEXE (
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "PYEXE=py -3"
)
if not defined PYEXE (
    echo [ERROR] Could not find a working Python 3 install on this machine.
    echo         Install Python 3.11+ from https://python.org/downloads
    echo         and make sure to tick "Add python.exe to PATH" during setup,
    echo         then close this window and run build.bat again.
    goto :fail
)
echo Using Python: !PYEXE!
!PYEXE! --version
echo.

if exist "build_venv\Scripts\activate.bat" (
    echo [1/4] Reusing existing virtual environment ^(build_venv already exists^)...
    echo       Run "build.bat clean" instead if you want a fresh one.
) else (
    echo [1/4] Creating virtual environment ^(first run, or after "build.bat clean"^)...
    !PYEXE! -m venv build_venv
    if not exist "build_venv\Scripts\activate.bat" (
        echo [ERROR] Virtual environment was not created.
        echo         ^(build_venv\Scripts\activate.bat is missing^)
        echo         This usually means the Python install found above is
        echo         broken, incomplete, or the "venv" module was excluded.
        goto :fail
    )
)
call build_venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Could not activate the virtual environment.
    goto :fail
)
echo Done.
echo.

echo [2/4] Checking Python dependencies...
echo       ^(pip skips anything already installed that satisfies
echo       requirements.txt - this will not re-download packages
echo       you already have^)
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] "pip install --upgrade pip" failed. Check your internet
    echo         connection and try again.
    goto :fail
)
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] "pip install -r requirements.txt" failed.
    echo         Scroll up for the exact pip error.
    goto :fail
)
echo Done.
echo.

if exist "build_venv\Lib\site-packages\playwright\driver\package\.local-browsers\chromium-*" (
    echo [3/4] Chromium already downloaded - skipping ^(no internet used^).
) else (
    echo [3/4] Downloading Chromium ^(first run, or after "build.bat clean"^) -
    echo       this is the only step that uses significant data
    echo       ^(~150-300MB^), and only happens once...
    set "PLAYWRIGHT_BROWSERS_PATH=0"
    python -m playwright install chromium
    if errorlevel 1 (
        echo [ERROR] "playwright install chromium" failed.
        echo         Common cause: no internet access, or a firewall/proxy
        echo         blocking playwright.download.prss.microsoft.com
        goto :fail
    )
)
if not exist "build_venv\Lib\site-packages\playwright\driver\package\.local-browsers" (
    echo [ERROR] Chromium install did not land where expected:
    echo         build_venv\Lib\site-packages\playwright\driver\package\.local-browsers
    goto :fail
)
echo Done.
echo.

REM Remove the "chromium_headless_shell" variant if present. Newer
REM Playwright versions download this automatically alongside regular
REM Chromium (it's used only for headless-mode performance) even though
REM this app always launches with headless=False and never touches it.
REM Its own official PyInstaller hook tries to bundle every browser
REM folder it finds under .local-browsers, and on some Chromium/headless
REM -shell revisions that fails with "Unable to find ...gdocs_script.js"
REM because a file the hook expects isn't actually present in that
REM particular shell build. Since the app never needs the shell at all,
REM the simplest fix is to delete it before PyInstaller ever sees it.
for /d %%D in ("build_venv\Lib\site-packages\playwright\driver\package\.local-browsers\chromium_headless_shell-*") do (
    echo Removing unused chromium_headless_shell variant: %%~nxD
    rmdir /s /q "%%D"
)

echo [4/4] Building ClientLedgerIndia.exe with PyInstaller...
echo       ^(this only repackages your current source files - no
echo       internet access needed for this step^)
pyinstaller ..\build\windows\ClientLedgerIndia.spec --distpath ..\build\windows\dist --workpath ..\build\windows\work --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed. Scroll up for the exact error.
    goto :fail
)
if not exist "..\build\windows\dist\ClientLedgerIndia\ClientLedgerIndia.exe" (
    echo [ERROR] Build reported success but ClientLedgerIndia.exe was not
    echo         found at build\windows\dist\ClientLedgerIndia\
    goto :fail
)

echo.
echo ================================================================
echo  BUILD SUCCEEDED
echo  App folder: build\windows\dist\ClientLedgerIndia\
echo  Next step:  open build\windows\installer.iss in Inno Setup and
echo              click Build ^(or run: iscc build\windows\installer.iss^)
echo              to produce the single ClientLedgerIndia-Setup.exe
echo.
echo  For future rebuilds after code changes: just run build.bat again
echo  ^(plain, no arguments^) - it will NOT re-download anything.
echo ================================================================
echo.
pause
exit /b 0

:fail
echo.
echo ================================================================
echo  BUILD FAILED - see the [ERROR] message above for the reason.
echo  Fix that and run build.bat again.
echo ================================================================
echo.
pause
exit /b 1
