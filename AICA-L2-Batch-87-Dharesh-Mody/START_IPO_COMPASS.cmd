@echo off
setlocal
cd /d "%~dp0"
title CA IPO Compass

rem ---- Windows "downloaded from the internet" flag (SmartScreen) ----------
rem Windows marks every file extracted from a downloaded ZIP with a hidden
rem Zone.Identifier flag, and SmartScreen asks "Run?" for a flagged .cmd.
rem That question is asked BEFORE this file starts, so it cannot be skipped
rem the first time a fresh download is opened (see README.md, "SmartScreen").
rem What this section does is clear the flag from every file in this folder,
rem so that the NEXT launch of the same folder does not ask again. It changes
rem nothing about what the app does.
set "IPO_DIR=%~dp0"
set "FLAGGED="
set "STILL="
if exist "%~f0:Zone.Identifier" set "FLAGGED=1"
if not defined FLAGGED goto flag_done
rem 1) PowerShell (path is passed through an environment variable, so folder
rem    names containing apostrophes or spaces are safe).
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath $env:IPO_DIR -Recurse -File -Force -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue" >nul 2>nul
rem 2) Fallback for PCs where PowerShell is restricted: empty the flag itself.
for /r "%~dp0" %%F in (*) do if exist "%%F:Zone.Identifier" 2>nul type nul > "%%F:Zone.Identifier"
rem 3) Check the result instead of assuming it worked.
2>nul more < "%~f0:Zone.Identifier" | findstr /i "ZoneId" >nul 2>nul && set "STILL=1"
if defined STILL goto flag_failed
echo Windows internet-download flag cleared. SmartScreen should not ask again for this folder.
goto flag_done
:flag_failed
echo.
echo NOTE: Windows still marks these files as downloaded from the internet,
echo so SmartScreen may ask again. One-time fix: close this window, right-click
echo the original ZIP, choose Properties, tick Unblock, click OK, then extract
echo it again. See README.md, SmartScreen.
echo.
:flag_done

if exist "%~dp0app\webapp.py" goto files_ready
echo.
echo CA IPO Compass cannot run from inside the ZIP preview.
echo.
echo 1. Close this window.
echo 2. Right-click the downloaded ZIP and choose Extract All.
echo 3. Open the extracted ca_ipo_compass folder.
echo 4. Double-click START_IPO_COMPASS.cmd again.
echo.
pause
exit /b 2
:files_ready
rem Only turn on headless-browser fetching (used for GMP/subscription pages
rem that need JavaScript to render) when Playwright is actually importable.
rem The default build needs no pip installs at all; forcing this on
rem regardless used to make every JS-rendered source fail on every refresh
rem with a "Playwright is not installed" error instead of the normal
rem "Research needed" fallback. Install Playwright yourself first
rem (pip install playwright && python -m playwright install chromium) to
rem get live rendering; this just detects that choice automatically.
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 -c "import playwright" >nul 2>nul
if not errorlevel 1 set IPO_COMPASS_BROWSER=1
py -3 main.py
goto finished
:use_python
python -c "import playwright" >nul 2>nul
if not errorlevel 1 set IPO_COMPASS_BROWSER=1
python main.py
:finished
if not errorlevel 1 exit /b 0
echo.
echo The application could not start. Please run CHECK_SETUP.cmd
echo and send IPO_Compass_Diagnostics.txt with a screenshot of this error.
pause
