@echo off
setlocal enabledelayedexpansion

echo ==================================================================
echo   VKL CUSTOMER ORDER TO ERP CONVERTER - UNINSTALLER
echo ==================================================================
echo.

:: Verify Administrator Privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Administrator privileges are required.
    echo Please right-click uninstall.bat and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

set "TARGET_DIR=C:\VKL_Order_Converter"

echo [1/4] Stopping background service and scheduled task...
schtasks /end /tn "VKL Order Converter" >nul 2>&1
taskkill /f /im "VKL_Order_Converter.exe" >nul 2>&1

echo [2/4] Removing auto-start scheduled task...
schtasks /delete /tn "VKL Order Converter" /f >nul 2>&1

echo [3/4] Removing Windows Firewall rule...
netsh advfirewall firewall delete rule name="VKL Order Converter LAN Port" >nul 2>&1

echo [4/4] Cleaning program files from %TARGET_DIR%...
if exist "%TARGET_DIR%\VKL_Order_Converter.exe" del /f /q "%TARGET_DIR%\VKL_Order_Converter.exe"
if exist "%TARGET_DIR%\logs" rd /s /q "%TARGET_DIR%\logs" >nul 2>&1

echo.
echo ==================================================================
echo   UNINSTALLATION COMPLETE
echo ==================================================================
echo   The scheduled task and firewall rules have been removed.
echo   NOTE: Your data folder has been safely PRESERVED at:
echo   %TARGET_DIR%\data
echo   (Contains your master.json, history snapshots, and audit.csv)
echo.
echo   To completely remove all data, you may manually delete %TARGET_DIR%.
echo ==================================================================
echo.
pause
