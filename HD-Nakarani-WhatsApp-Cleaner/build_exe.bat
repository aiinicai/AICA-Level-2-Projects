@echo off
REM Build wa_cleaner.exe with PyInstaller and preserve the live session.
REM Run this from C:\wa-py\ (or just double-click it).
REM
REM Output: C:\wa-py\dist\wa_cleaner\wa_cleaner.exe
REM
REM PyInstaller wipes dist\wa_cleaner\ during COLLECT, so this script first
REM moves wa-profile\ / exports\ / audit.log / presets.json to a temp backup,
REM runs the build, then restores them. On the first build (nothing in dist yet)
REM it seeds those files from C:\wa-py\ instead.

cd /d "%~dp0"

set "BACKUP=%~dp0_build_backup"

echo.
echo === Backing up runtime files ===
if exist "%BACKUP%" rmdir /s /q "%BACKUP%"
mkdir "%BACKUP%"
if exist dist\wa_cleaner\wa-profile   xcopy /E /I /Q /Y dist\wa_cleaner\wa-profile   "%BACKUP%\wa-profile"   >nul
if exist dist\wa_cleaner\exports      xcopy /E /I /Q /Y dist\wa_cleaner\exports      "%BACKUP%\exports"      >nul
if exist dist\wa_cleaner\audit.log    copy  /Y          dist\wa_cleaner\audit.log    "%BACKUP%\audit.log"    >nul
if exist dist\wa_cleaner\presets.json copy  /Y          dist\wa_cleaner\presets.json "%BACKUP%\presets.json" >nul

echo.
echo === Cleaning previous build ===
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist wa_cleaner.spec del /q wa_cleaner.spec

echo.
echo === Running PyInstaller ===
python -m PyInstaller ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --name wa_cleaner ^
    --collect-all playwright ^
    --collect-all customtkinter ^
    --collect-all darkdetect ^
    wa_cleaner.py

if errorlevel 1 (
    echo.
    echo *** BUILD FAILED ***
    echo Backup preserved at: %BACKUP%
    pause
    exit /b 1
)

echo.
echo === Restoring runtime files ===
if exist "%BACKUP%\wa-profile" (
    xcopy /E /I /Q /Y "%BACKUP%\wa-profile" dist\wa_cleaner\wa-profile >nul
    echo    - restored wa-profile
) else if exist wa-profile (
    xcopy /E /I /Q /Y wa-profile dist\wa_cleaner\wa-profile >nul
    echo    - seeded wa-profile from source
)
if exist "%BACKUP%\exports" (
    xcopy /E /I /Q /Y "%BACKUP%\exports" dist\wa_cleaner\exports >nul
    echo    - restored exports
) else if exist exports (
    xcopy /E /I /Q /Y exports dist\wa_cleaner\exports >nul
    echo    - seeded exports from source
)
if exist "%BACKUP%\audit.log" (
    copy /Y "%BACKUP%\audit.log" dist\wa_cleaner\audit.log >nul
    echo    - restored audit.log
) else if exist audit.log (
    copy /Y audit.log dist\wa_cleaner\audit.log >nul
    echo    - seeded audit.log from source
)
if exist "%BACKUP%\presets.json" (
    copy /Y "%BACKUP%\presets.json" dist\wa_cleaner\presets.json >nul
    echo    - restored presets.json
)

rmdir /s /q "%BACKUP%"

echo.
echo === Build complete ===
echo EXE:      %~dp0dist\wa_cleaner\wa_cleaner.exe
echo Session:  preserved
echo.
pause
