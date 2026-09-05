@echo off
setlocal EnableDelayedExpansion
title AccuSheet Pro - Build Setup

echo.
echo  ============================================================
echo   AccuSheet Pro - Installer and Builder
echo   Non-Corporate Balance Sheet and Working Papers
echo  ============================================================
echo.

:: ── Navigate to the script's own directory (handles spaces and special chars) ──
pushd "%~dp0"
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] Could not navigate to project directory.
    pause
    exit /b 1
)

:: ── Step 0: Check Node.js ─────────────────────────────────────────────────────
echo [1/5] Checking Node.js installation...
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Node.js is NOT installed or not in PATH.
    echo.
    echo  Please install Node.js from: https://nodejs.org/
    echo  Download the LTS version (recommended).
    echo.
    echo  After installing, re-run this script.
    echo.
    pause
    popd
    exit /b 1
)

for /f "tokens=*" %%v in ('node --version') do set NODE_VER=%%v
echo  [OK] Node.js %NODE_VER% found.

where npm >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] npm is not found. Please reinstall Node.js.
    pause
    popd
    exit /b 1
)

for /f "tokens=*" %%v in ('npm --version') do set NPM_VER=%%v
echo  [OK] npm v%NPM_VER% found.
echo.

:: ── Step 1: Install dependencies ─────────────────────────────────────────────
echo [2/5] Installing dependencies (this may take a few minutes)...
echo       (Electron binaries ~100MB will be downloaded if not cached)
echo.
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] npm install failed. Check your internet connection and try again.
    pause
    popd
    exit /b 1
)

call npm approve-scripts electron esbuild >nul 2>&1
call npm install >nul 2>&1

echo.
echo  [OK] Dependencies installed.
echo.

:: ── Step 2: Build Vite frontend ───────────────────────────────────────────────
echo [3/5] Building frontend and server bundle...
echo.
call node "node_modules\vite\bin\vite.js" build
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Vite build failed. Check the errors above and try again.
    pause
    popd
    exit /b 1
)

:: Build Express server bundle
call node "node_modules\esbuild\bin\esbuild" server.ts --bundle --platform=node --format=cjs --external:vite --sourcemap --outfile=dist/server.cjs
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Server bundle failed. Check the errors above.
    pause
    popd
    exit /b 1
)
echo.
echo  [OK] Build complete.
echo.

:: ── Step 4: Close any running AccuSheet Pro (so EXE is not locked) ────────────
echo  Closing any running AccuSheet Pro instances...
taskkill /f /im "AccuSheet Pro.exe" >nul 2>&1
taskkill /f /im "electron.exe" >nul 2>&1
timeout /t 2 /nobreak >nul

:: ── Step 5: Package into Windows EXE (unpacked) ───────────────────────────────
echo [4/5] Packaging Electron app...
echo       (This may take 3-5 minutes. Do NOT close this window.)
echo.

:: Clear ALL code-signing variables so electron-builder skips signing entirely
set "WIN_CSC_LINK="
set "WIN_CSC_KEY_PASSWORD="
set "CSC_LINK="
set "CSC_KEY_PASSWORD="
set "CSC_NAME="
set "CSC_IDENTITY_AUTO_DISCOVERY=false"

call node "node_modules\electron-builder\cli.js" --win --x64 --dir
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Electron packaging failed. Check the errors above.
    echo.
    echo  Common fixes:
    echo    - Close AccuSheet Pro if it is open, then try again
    echo    - Try running this bat file as Administrator (right-click, Run as admin)
    echo    - Delete the release\ folder and run this script again
    echo.    - Delete node_modules\ and run this script again
    echo.
    pause
    popd
    exit /b 1
)
echo.
echo  [OK] Electron packaged successfully!
echo.

:: ── Step 5: Create ZIP distribution ──────────────────────────────────────────
echo [5/5] Creating distributable ZIP package...
if exist "release\AccuSheet-Pro-win-x64.zip" del /f /q "release\AccuSheet-Pro-win-x64.zip"
powershell -NoProfile -Command "Compress-Archive -Path 'release\win-unpacked\*' -DestinationPath 'release\AccuSheet-Pro-win-x64.zip' -Force"
if %ERRORLEVEL% NEQ 0 (
    echo  [WARN] Could not create ZIP. The unpacked EXE in release\win-unpacked\ still works!
) else (
    copy /y "release\AccuSheet-Pro-win-x64.zip" "release\AccuSheet-Pro-1.0.0-win-x64.zip" >nul 2>&1
    echo  [OK] ZIP created: release\AccuSheet-Pro-win-x64.zip
    echo  [OK] ZIP created: release\AccuSheet-Pro-1.0.0-win-x64.zip
)

if exist "config.env.example" (
    copy /y "config.env.example" "release\win-unpacked\config.env.example" >nul 2>&1
)
echo.

:: ── Done! ─────────────────────────────────────────────────────────────────────
echo  ============================================================
echo   BUILD COMPLETE!
echo  ============================================================
echo.
echo   Your app is ready in TWO formats:
echo.
echo   1. PORTABLE FOLDER (run immediately, no install needed):
echo      release\win-unpacked\AccuSheet Pro.exe
echo.
echo   2. DISTRIBUTABLE ZIP (share with others):
echo      release\AccuSheet-Pro-win-x64.zip
echo.
echo   No API key or internet required.
echo   Runs fully offline with built-in Indian GAAP rule engine.
echo.

:: Open the release folder
if exist "release\win-unpacked" (
    echo  Opening release folder...
    explorer "release\win-unpacked"
)

echo.
pause
popd
endlocal
