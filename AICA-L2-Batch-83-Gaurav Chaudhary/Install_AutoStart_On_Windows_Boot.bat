@echo off
title Install GS Stock Audit Tracker AutoStart
cd /d "%~dp0"
echo ==================================================================
echo   INSTALL AUTO-START ON WINDOWS BOOT (GS STOCK AUDIT TRACKER)
echo ==================================================================
echo.

set VBS_PATH=%~dp0Start_Silent_Server.vbs

schtasks /create /tn "GS_Stock_Audit_Tracker" /tr "wscript.exe \"%VBS_PATH%\"" /sc onlogon /rl highest /f

echo.
if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] GS Stock Audit Tracker is now configured to start automatically in the background on Windows startup!
) else (
    echo [NOTE] If required, please run this batch file as Administrator.
)
echo.
pause
