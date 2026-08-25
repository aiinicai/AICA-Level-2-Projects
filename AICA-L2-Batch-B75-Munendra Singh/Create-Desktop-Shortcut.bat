@echo off
setlocal
title Create FinAudit AI Desktop Shortcut
color 0A
echo Creating Shortcut on your Windows Desktop...

set "TARGET_EXE=%~dp0release\win-unpacked\FinAudit-AI-Auditor.exe"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\FinAudit AI - Ind AS Auditor.lnk"
set "WORKING_DIR=%~dp0release\win-unpacked"

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%TARGET_EXE%'; $Shortcut.WorkingDirectory = '%WORKING_DIR%'; $Shortcut.Description = 'FinAudit AI - Offline Ind AS Financial Statement Auditor'; $Shortcut.Save()"

echo.
echo ===============================================================================
echo  SUCCESS! Shortcut "FinAudit AI - Ind AS Auditor" created on your Desktop!
echo ===============================================================================
echo.
pause
