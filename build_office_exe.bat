@echo off
cd /d "%~dp0"
echo ====================================================================
echo  Testing and Building AutoBankStatementEntry.exe (Windows x64)
echo ====================================================================
echo.
where dotnet >nul 2>&1
if %errorlevel% neq 0 (
    echo .NET 8 SDK not found. Installing via winget...
    winget install -e --id Microsoft.DotNet.SDK.8 --accept-package-agreements --accept-source-agreements
    echo Please close and re-run build_office_exe.bat after .NET 8 SDK finishes installing.
    pause
    exit /b 1
)

echo [1/2] Running automated regression test suite (bank parsers, balance math, overlaps, isolation)...
dotnet test "Tests\AutoBankStatementEntry.Tests.csproj" -c Release --nologo --verbosity minimal
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Regression tests failed! Fix the failing test before publishing.
    pause
    exit /b 1
)

REM Never delete the whole publish folder: when no data_path.txt is used, the office database (ML learning,
REM bank details, posting history) lives in publish\data and must survive every rebuild / update.
if exist "publish" del /q "publish\*.*" >nul 2>&1

echo.
echo [2/2] Publishing single portable Windows x64 executable (English-only, 100%% offline)...
dotnet publish AutoBankStatementEntry.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:EnableCompressionInSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o publish
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed. Check the messages above.
    pause
    exit /b 1
)

echo.
echo ====================================================================
echo  ALL TESTS PASSED - BUILD COMPLETE!
echo  Your single portable Windows x64 executable is ready at:
echo    publish\AutoBankStatementEntry.exe
echo ====================================================================
explorer "publish"
pause
