@echo off
setlocal enabledelayedexpansion
title FinAudit AI - Build Windows Desktop Application
color 0A
echo ===============================================================================
echo        FINAUDIT AI - BUILDING WINDOWS INSTALLER & EXECUTABLE
echo ===============================================================================
echo.
echo Packaging Desktop Application into release/ directory...
echo.

cd /d "%~dp0"

echo [1/2] Building React production bundle...
node "%~dp0node_modules\vite\bin\vite.js" build

echo.
echo [2/2] Packaging Windows Desktop Installer (.exe)...
node "%~dp0node_modules\electron-builder\cli.js" --win

echo.
echo ===============================================================================
echo  SUCCESS! Application installer created in folder: "release"
echo ===============================================================================
pause
