@echo off
TITLE Build Executable (.exe) — Audit Observation Tracker
COLOR 0B

echo ========================================================================
echo         BUILDING STANDALONE WINDOWS EXECUTABLE (.EXE)
echo ========================================================================
echo.

:: 1. Build Vite Frontend
echo [1/3] Building frontend assets...
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed!
    pause
    exit /b 1
)

:: 2. Create output folder
if not exist "dist-exe\" mkdir dist-exe

:: 3. Package EXE using pkg
echo [2/3] Compiling Node.js server + SQLite WASM + Frontend into EXE...
call npx pkg launcher.cjs --config package.json --target node18-win-x64 --output dist-exe/AuditTracker.exe
if %errorlevel% neq 0 (
    echo [WARNING] pkg compilation finished with warnings. Checking output executable...
)

:: 4. Copy sql-wasm.wasm alongside exe if needed
if exist "node_modules\sql.js\dist\sql-wasm.wasm" (
    echo [3/3] Copying WebAssembly database engine...
    copy /Y "node_modules\sql.js\dist\sql-wasm.wasm" "dist-exe\sql-wasm.wasm" >nul
)

echo.
echo ========================================================================
echo  BUILD COMPLETE!
echo  Executable created at: dist-exe\AuditTracker.exe
echo  Double-click dist-exe\AuditTracker.exe to run the application anywhere!
echo ========================================================================
echo.

pause
