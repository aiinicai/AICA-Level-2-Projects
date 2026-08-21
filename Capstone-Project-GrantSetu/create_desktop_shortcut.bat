@echo off
title Create Desktop Shortcut for GrantSetu
cls
echo [INFO] Creating Desktop Shortcut for GrantSetu...

set SCRIPT="%TEMP%\%RANDOM%-%RANDOM%-%RANDOM%-%RANDOM%.vbs"
set TARGET=%~dp0GrantSetu.bat

echo Set oWS = WScript.CreateObject("WScript.Shell") >> %SCRIPT%
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\GrantSetu NGO ERP.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%TARGET%" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "Launch GrantSetu Indian NGO ERP" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%

cscript /nologo %SCRIPT%
del %SCRIPT%

echo.
echo [SUCCESS] Desktop Shortcut 'GrantSetu NGO ERP' created successfully on your Desktop!
echo.
pause
