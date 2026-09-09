@echo off
REM Opens port 8080 in Windows Firewall so other PCs on the LAN can use the app.
REM Needs to run as Administrator (right-click -> Run as administrator).
echo Adding firewall rule for CMA Pro Builder (port 8080)...
netsh advfirewall firewall delete rule name="CMA Pro Builder 8080" >nul 2>&1
netsh advfirewall firewall add rule name="CMA Pro Builder 8080" dir=in action=allow protocol=TCP localport=8080
if errorlevel 1 (
  echo.
  echo FAILED - please right-click this file and choose "Run as administrator".
) else (
  echo Done. Other PCs can now open http://^<this-pc-ip^>:8080
)
echo.
pause
