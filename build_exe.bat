@echo off
title IPO_Tracker - build standalone EXE (target under 25 MB)
echo ============================================================
echo  Building IPO_Tracker.exe  (takes a few minutes)
echo ============================================================
python -m pip install --upgrade pyinstaller PyQt5 requests beautifulsoup4
if errorlevel 1 goto fail

rem ---- optional: UPX compressor makes the EXE much smaller (skipped if download fails)
if not exist upx\upx.exe (
  echo Downloading UPX compressor ...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing 'https://github.com/upx/upx/releases/download/v4.2.4/upx-4.2.4-win64.zip' -OutFile upx.zip; Expand-Archive -Path upx.zip -DestinationPath upx_tmp -Force; New-Item -ItemType Directory -Force -Path upx | Out-Null; Copy-Item 'upx_tmp\upx-4.2.4-win64\upx.exe' 'upx\upx.exe' -Force } catch { Write-Host 'UPX download skipped.' }"
  if exist upx.zip del upx.zip
  if exist upx_tmp rmdir /s /q upx_tmp
)

if exist upx\upx.exe (
  python -m PyInstaller IPO_Tracker.spec --noconfirm --clean --upx-dir upx
) else (
  python -m PyInstaller IPO_Tracker.spec --noconfirm --clean
)
if errorlevel 1 goto fail

if not exist dist\IPO_Tracker.exe goto fail
for %%A in (dist\IPO_Tracker.exe) do set SIZE=%%~zA
echo.
echo SUCCESS - your program is: dist\IPO_Tracker.exe
echo Size in bytes: %SIZE%   (25 MB limit = 26214400)
if %SIZE% GTR 26214400 (
  echo WARNING: the EXE is larger than 25 MB. Try Python 3.10 or 3.11 instead of a newer version, then run this file again.
) else (
  echo Size is within the 25 MB limit.
)
pause
exit /b 0

:fail
echo.
echo Build failed - please read the messages above.
pause
exit /b 1
