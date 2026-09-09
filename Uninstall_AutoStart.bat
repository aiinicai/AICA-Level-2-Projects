@echo off
title Uninstall GS Stock Audit Tracker AutoStart
echo ==================================================================
echo   UNINSTALL AUTO-START (GS STOCK AUDIT TRACKER)
echo ==================================================================
echo.

schtasks /delete /tn "GS_Stock_Audit_Tracker" /f

echo.
echo [DONE] Auto-start task removed.
pause
