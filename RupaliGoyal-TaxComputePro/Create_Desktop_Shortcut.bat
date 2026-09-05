@echo off
title Create Desktop Shortcut for TaxCompute Pro
color 0A
cd /d "%~dp0"

echo =====================================================================
echo       CREATING DESKTOP SHORTCUT FOR TAXCOMPUTE PRO
echo =====================================================================
echo.

set SCRIPT="%TEMP%\CreateTaxComputeShortcut.vbs"

echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\TaxCompute Pro.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%~dp0Launch_TaxCompute_Pro.bat" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "TaxCompute Pro - Indian Direct Tax Computation Suite" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%

cscript /nologo %SCRIPT%
del %SCRIPT%

echo [OK] Shortcut created successfully on your Desktop!
echo You can now launch TaxCompute Pro with 1-click directly from your Desktop.
echo.
pause
