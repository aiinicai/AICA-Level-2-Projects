@echo off
rem ============================================================
rem  Builds  dist\GST Downloader\GST Downloader.exe
rem  and     dist\GST Downloader.zip   (give this zip to staff)
rem ============================================================
cd /d "%~dp0"

echo [1/4] Installing build tools...
python -m pip install --upgrade -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

echo [2/4] Building the app (takes 1-3 minutes)...
if exist "build" rmdir /s /q "build"
if exist "dist\GST Downloader" rmdir /s /q "dist\GST Downloader"
python -m PyInstaller --noconfirm --clean --windowed --name "GST Downloader" ^
  --add-data "ui;ui" ^
  --collect-submodules webview ^
  main.py
if errorlevel 1 goto :fail

echo [3/4] Copying your client list and settings...
set "OUT=dist\GST Downloader"
if exist "clients.xlsx" copy /Y "clients.xlsx" "%OUT%\clients.xlsx" >nul
if exist "config.json"  copy /Y "config.json"  "%OUT%\config.json"  >nul
if exist "blocked.json" copy /Y "blocked.json" "%OUT%\blocked.json" >nul
copy /Y "README.md" "%OUT%\README.md" >nul

echo [4/4] Making a zip to share...
if exist "dist\GST Downloader.zip" del /q "dist\GST Downloader.zip"
powershell -NoProfile -Command "Compress-Archive -Path 'dist\GST Downloader' -DestinationPath 'dist\GST Downloader.zip'"

echo.
echo ============================================================
echo  Done.
echo  App:      %OUT%\GST Downloader.exe
echo  To share: dist\GST Downloader.zip
echo ============================================================
start "" "dist"
pause
exit /b 0

:fail
echo.
echo Build failed. Take a screenshot of this window and send it.
pause
exit /b 1
