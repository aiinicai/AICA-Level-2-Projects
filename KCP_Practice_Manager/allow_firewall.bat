@echo off
REM ==========================================================================
REM  KCP Practice Manager - open Windows Firewall for the office server
REM  Run ONCE on the SERVER PC:  right-click > Run as administrator
REM ==========================================================================
net session >nul 2>&1
if errorlevel 1 (
    echo.
    echo Please right-click this file and choose "Run as administrator".
    echo.
    pause
    exit /b 1
)
echo Adding firewall rules for the office (private / domain) network only ...
netsh advfirewall firewall delete rule name="KCP Practice Manager server (TCP 8765)" >nul 2>&1
netsh advfirewall firewall delete rule name="KCP Practice Manager discovery (UDP 8766)" >nul 2>&1
netsh advfirewall firewall add rule name="KCP Practice Manager server (TCP 8765)" dir=in action=allow protocol=TCP localport=8765 profile=private,domain
netsh advfirewall firewall add rule name="KCP Practice Manager discovery (UDP 8766)" dir=in action=allow protocol=UDP localport=8766 profile=private,domain
echo.
echo Done. Make sure this PC's network is set to "Private" (Settings > Network ^& Internet).
echo.
pause
