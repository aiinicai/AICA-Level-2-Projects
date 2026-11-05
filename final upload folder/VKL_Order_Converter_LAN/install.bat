@echo off
setlocal enabledelayedexpansion

echo ==================================================================
echo   VKL CUSTOMER ORDER TO ERP CONVERTER - WINDOWS INSTALLER
echo ==================================================================
echo.

:: 1. Verify Administrator Privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Administrator privileges are required.
    echo Please right-click install.bat and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

:: 2. Verify VKL_Order_Converter.exe exists
if not exist "VKL_Order_Converter.exe" (
    echo [ERROR] VKL_Order_Converter.exe not found in this directory.
    echo Please run build.bat first to compile the executable.
    echo.
    pause
    exit /b 1
)

set "TARGET_DIR=C:\VKL_Order_Converter"
set "APP_PORT=8080"

:: 3. Read configured port if config.json exists
if exist "config.json" (
    for /f "tokens=2 delims=:, " %%p in ('findstr /i "port" config.json') do (
        set "APP_PORT=%%p"
    )
)

echo [1/5] Creating installation directory at %TARGET_DIR%...
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
if not exist "%TARGET_DIR%\data" mkdir "%TARGET_DIR%\data"
if not exist "%TARGET_DIR%\data\history" mkdir "%TARGET_DIR%\data\history"
if not exist "%TARGET_DIR%\logs" mkdir "%TARGET_DIR%\logs"

echo [2/5] Copying application files to %TARGET_DIR%...
schtasks /end /tn "VKL Order Converter" >nul 2>&1
taskkill /f /im "VKL_Order_Converter.exe" >nul 2>&1
timeout /t 2 >nul
copy /y "VKL_Order_Converter.exe" "%TARGET_DIR%\VKL_Order_Converter.exe" >nul
if exist "config.json" (
    if not exist "%TARGET_DIR%\config.json" (
        copy /y "config.json" "%TARGET_DIR%\config.json" >nul
    )
) else (
    echo {"port":8080,"pin":"","dataDir":"data"} > "%TARGET_DIR%\config.json"
)

echo [3/5] Configuring Windows Defender Firewall rule for Port %APP_PORT% (Private and Domain networks)...
netsh advfirewall firewall delete rule name="VKL Order Converter LAN Port" >nul 2>&1
netsh advfirewall firewall add rule name="VKL Order Converter LAN Port" dir=in action=allow protocol=TCP localport=%APP_PORT% profile=private,domain >nul
if %errorlevel% equ 0 (
    echo       Firewall rule added successfully.
) else (
    echo       [WARNING] Could not add firewall rule automatically. Colleagues might need port %APP_PORT% unblocked manually.
)

echo [4/5] Registering Auto-Start Scheduled Task as SYSTEM...
schtasks /delete /tn "VKL Order Converter" /f >nul 2>&1
schtasks /create /tn "VKL Order Converter" /tr "%TARGET_DIR%\VKL_Order_Converter.exe" /sc onstart /ru "SYSTEM" /rl HIGHEST /f >nul
if %errorlevel% equ 0 (
    echo       Scheduled task created successfully (runs automatically at computer startup).
) else (
    echo       [WARNING] Failed to register scheduled task.
)

echo [5/5] Starting service now...
schtasks /run /tn "VKL Order Converter" >nul 2>&1
timeout /t 2 >nul

:: Detect local IPv4 addresses to show user
echo.
echo ==================================================================
echo   INSTALLATION COMPLETED SUCCESSFULLY!
echo ==================================================================
echo.
echo  The server is running in the background and will restart
echo  automatically whenever this computer reboots.
echo.
echo  COLLEAGUE ACCESS URLS (Share with your office team):
for /f "tokens=4" %%a in ('route print ^| findstr 0.0.0.0.*0.0.0.0') do (
    if not "%%a"=="" (
        echo   -> http://%%a:%APP_PORT%
    )
)
echo.
echo  Local Dashboard / Admin:
echo   -> http://localhost:%APP_PORT%/admin
echo.
echo  Installation Directory: %TARGET_DIR%
echo  Data & Master Backups:  %TARGET_DIR%\data
echo  Activity Logs:          %TARGET_DIR%\logs\server.log
echo ==================================================================
echo.
pause
