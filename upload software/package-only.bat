@echo off
setlocal EnableDelayedExpansion

:: This helper script runs electron-builder from within the project directory.
:: It is called by install-and-run.bat and also works standalone.

:: Navigate to project directory using the script's own location
pushd "%~dp0"

echo  Closing any running AccuSheet Pro instances...
taskkill /f /im "AccuSheet Pro.exe" >nul 2>&1
taskkill /f /im "electron.exe" >nul 2>&1
timeout /t 2 /nobreak >nul

:: Clear ALL code-signing environment variables
set "WIN_CSC_LINK="
set "WIN_CSC_KEY_PASSWORD="
set "CSC_LINK="
set "CSC_KEY_PASSWORD="
set "CSC_NAME="
set "CSC_IDENTITY_AUTO_DISCOVERY=false"

echo  Packaging Electron app (3-5 minutes)...
echo.

node "node_modules\electron-builder\cli.js" --win --x64 --dir
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Packaging failed! See errors above.
    echo.
    echo  Try:
    echo    1. Close AccuSheet Pro app if open
    echo    2. Delete the release\ folder manually, then run again
    echo    3. Right-click this bat file, Run as Administrator
    echo.
    pause
    popd
    exit /b 1
)

echo.
echo  [OK] EXE packaged: release\win-unpacked\AccuSheet Pro.exe
echo.

:: Create ZIP
if exist "release\AccuSheet-Pro-win-x64.zip" del /f /q "release\AccuSheet-Pro-win-x64.zip"
powershell -NoProfile -Command "Compress-Archive -Path 'release\win-unpacked\*' -DestinationPath 'release\AccuSheet-Pro-win-x64.zip' -Force"
copy /y "release\AccuSheet-Pro-win-x64.zip" "release\AccuSheet-Pro-1.0.0-win-x64.zip" >nul 2>&1
echo  [OK] ZIP created: release\AccuSheet-Pro-win-x64.zip
echo  [OK] ZIP created: release\AccuSheet-Pro-1.0.0-win-x64.zip
echo.

echo  Opening release folder...
explorer "release\win-unpacked"

pause
popd
endlocal
