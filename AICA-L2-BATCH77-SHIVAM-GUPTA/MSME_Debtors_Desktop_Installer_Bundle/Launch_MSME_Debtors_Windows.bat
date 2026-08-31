@echo off
title Launching MSME Debtors Management System
echo =====================================================================
echo           MSME DEBTORS MANAGEMENT & INTEREST CALCULATOR
echo =====================================================================
echo.
echo Launching application in standalone app mode...
echo.

:: Try to launch with Microsoft Edge in App Mode (Borderless Desktop Window)
start msedge --app="https://msme-debtors-manager.ai.studio" 2>nul
if %errorlevel% equ 0 goto done

:: Try Google Chrome in App Mode
start chrome --app="https://msme-debtors-manager.ai.studio" 2>nul
if %errorlevel% equ 0 goto done

:: Fallback to default system browser
start "" "https://msme-debtors-manager.ai.studio"

:done
echo.
echo Application opened successfully!
echo Tip: Click 'Install App' in the top header to pin to your Desktop/Taskbar.
timeout /t 3 >nul
exit
