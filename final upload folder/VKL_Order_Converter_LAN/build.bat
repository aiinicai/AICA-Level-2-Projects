@echo off
setlocal enabledelayedexpansion

echo ==================================================================
echo   VKL CUSTOMER ORDER TO ERP CONVERTER - WINDOWS 64-BIT BUILDER
echo ==================================================================
echo.

:: 1. Check if Go compiler is installed
where go >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Go compiler was not found on this computer.
    echo.
    echo Please download and install Go 1.22 or later from:
    echo https://go.dev/dl/
    echo.
    echo After installing, restart Command Prompt and run build.bat again.
    echo.
    pause
    exit /b 1
)

:: Display Go version
for /f "tokens=*" %%v in ('go version') do echo [INFO] Found %%v
echo.

:: 2. Set environment for pure, self-contained Windows amd64 executable
echo [BUILDING] Compiling standalone Windows 64-bit binary (offline, stdlib only)...
set CGO_ENABLED=0
set GOOS=windows
set GOARCH=amd64

go build -trimpath -ldflags "-s -w" -o VKL_Order_Converter.exe
if %errorlevel% neq 0 (
    echo.
    echo [BUILD FAILED] Compilation encountered an error. Please see details above.
    pause
    exit /b %errorlevel%
)

:: 3. Check output executable size
if exist VKL_Order_Converter.exe (
    for %%I in (VKL_Order_Converter.exe) do set "BYTES=%%~zI"
    set /a "KB=!BYTES! / 1024"
    set /a "MB=!KB! / 1024"
    echo.
    echo ==================================================================
    echo   BUILD SUCCESSFUL!
    echo ==================================================================
    echo   Output Binary : VKL_Order_Converter.exe
    echo   File Size     : !BYTES! bytes (~!MB! MB / !KB! KB)
    echo   Target Arch   : Windows 64-bit (x86_64 / amd64)
    echo   Dependencies  : None (100%% Self-Contained Native Executable)
    echo ==================================================================
    echo.
    echo Next Steps:
    echo   1. To test immediately: double-click VKL_Order_Converter.exe
    echo   2. To install as permanent Windows service: right-click install.bat
    echo      and select "Run as administrator".
    echo.
) else (
    echo [ERROR] Executable was not created.
)

pause
