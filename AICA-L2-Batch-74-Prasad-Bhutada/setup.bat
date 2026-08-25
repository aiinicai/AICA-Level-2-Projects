@echo off
setlocal enabledelayedexpansion
echo ============================================
echo  CA Docs - First-Time Setup
echo ============================================
echo.
echo This will take a few minutes. Please don't close this window.
echo.

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js was not found on this computer.
    echo.
    echo Please install Node.js first:
    echo   1. Go to https://nodejs.org
    echo   2. Download the "LTS" version for Windows
    echo   3. Run the installer with default options
    echo   4. Restart this computer
    echo   5. Run this setup.bat again
    echo.
    pause
    exit /b 1
)

for /f "tokens=1 delims=v." %%v in ('node -v') do set NODE_MAJOR=%%v
node -e "process.exit(process.versions.node.split('.')[0] >= 18 ? 0 : 1)"
if errorlevel 1 (
    echo [ERROR] Your Node.js version is too old for CA Docs.
    echo Please install the current LTS version from https://nodejs.org and try again.
    pause
    exit /b 1
)
echo [OK] Node.js found.
echo.

echo Step 1 of 6: Installing backend components...
cd /d "%~dp0backend"
call npm install
if errorlevel 1 goto :error

echo.
echo Step 2 of 6: Installing frontend components...
cd /d "%~dp0frontend"
call npm install
if errorlevel 1 goto :error

echo.
echo Step 3 of 6: Setting up configuration (first time only)...
cd /d "%~dp0backend"
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [OK] Created backend\.env with default settings.
    echo      You can change the Manage Formats password later from within the app.
) else (
    echo [OK] backend\.env already exists, keeping your existing settings.
)

echo.
echo Step 4 of 6: Setting up the database...
call npx prisma db push --skip-generate
if errorlevel 1 goto :error
call npx prisma generate
if errorlevel 1 goto :error
call npm run seed
if errorlevel 1 goto :error
echo [OK] Database ready.

echo.
echo Step 5 of 6: Building the application...
call npm run build
if errorlevel 1 goto :error

cd /d "%~dp0frontend"
call npm run build
if errorlevel 1 goto :error

echo.
echo Step 6 of 6: Finishing up...
if exist "%~dp0backend\public" rmdir /s /q "%~dp0backend\public"
xcopy /e /i /y "%~dp0frontend\dist" "%~dp0backend\public" >nul
echo [OK] Done.

echo.
echo ============================================
echo  Setup complete!
echo ============================================
echo.
echo To start CA Docs, double-click start.bat
echo (You only need to run setup.bat again if you update the application.)
echo.
pause
exit /b 0

:error
echo.
echo ============================================
echo  Setup did not finish - see the error above.
echo ============================================
echo If you're stuck, check docs\INSTALLATION.md or share this
echo window's full text with whoever is helping you set this up.
echo.
pause
exit /b 1
