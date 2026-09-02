@echo off
setlocal
cd /d "%~dp0"

call BUILD_WINDOWS_EXE_v1_1_6.bat
if errorlevel 1 exit /b 1

if not exist "dist\ICFR_Testing_AI_Assistant_v1_1_6.exe" (
    echo ERROR: Final EXE was not found.
    pause
    exit /b 1
)

copy /Y "dist\ICFR_Testing_AI_Assistant_v1_1_6.exe" "ICFR_Testing_AI_Assistant_v1_1_6.exe" >nul

echo.
echo ============================================================
echo FINAL PROJECT EXE READY
echo ============================================================
echo %CD%\ICFR_Testing_AI_Assistant_v1_1_6.exe
echo.
for %%F in ("ICFR_Testing_AI_Assistant_v1_1_6.exe") do echo Size: %%~zF bytes
certutil -hashfile "ICFR_Testing_AI_Assistant_v1_1_6.exe" SHA256
echo.
echo You can now upload/distribute the EXE shown above.
pause
