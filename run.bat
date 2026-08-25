@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"
if errorlevel 1 (
    echo [ERROR] Could not open the application folder.
    pause
    exit /b 1
)

echo =======================================================================
echo      HARSH RESTRORECO
echo =======================================================================
echo.

set "VPY=%CD%\venv\Scripts\python.exe"
if not exist "%VPY%" (
    echo [INFO] Virtual environment not found. Installing now...
    call "%~dp0install.bat" /quiet
    if errorlevel 1 (
        echo [ERROR] Installation failed.
        pause
        exit /b 1
    )
)

"%VPY%" -c "import uvicorn, fastapi" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Required packages are missing. Updating dependencies...
    call "%~dp0install.bat" /quiet
    if errorlevel 1 (
        echo [ERROR] Could not install dependencies.
        pause
        exit /b 1
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0register_startup.ps1" >nul 2>&1

set HOST=127.0.0.1
set PORT=8001

for /L %%P in (8001,1,8010) do (
    netstat -ano | findstr /R /C:":%%P .*LISTENING" >nul
    if !errorlevel! neq 0 (
        set PORT=%%P
        goto :port_ready
    )
)

echo [ERROR] Ports 8001-8010 are all in use. Close the other local app and try again.
pause
exit /b 1

:port_ready
echo [INFO] Folder: %CD%
echo [INFO] Opening http://%HOST%:!PORT! when the server is ready.
echo [INFO] Leave this window open. Press Ctrl+C to stop.
echo.

start "" cmd /c "timeout /t 5 /nobreak >nul & start http://%HOST%:!PORT!"

"%VPY%" -m uvicorn app.main:app --host %HOST% --port !PORT!
set "ERR=!errorlevel!"
if not "!ERR!"=="0" (
    echo.
    echo [ERROR] The application stopped with code !ERR!.
    echo Run install.bat if packages are missing, then try run.bat again.
    pause
    exit /b !ERR!
)
exit /b 0
