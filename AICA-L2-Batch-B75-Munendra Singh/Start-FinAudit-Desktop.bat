@echo off
setlocal enabledelayedexpansion
title FinAudit AI Desktop Application
color 0A
echo ===============================================================================
echo        FINAUDIT AI - NATIVE DESKTOP STATUTORY AUDITOR (WINDOWS)
echo ===============================================================================
echo.
echo Launching Native Desktop Container...
echo.

cd /d "%~dp0"

IF NOT EXIST "dist\index.html" (
    echo Building local production assets...
    node "%~dp0node_modules\vite\bin\vite.js" build
)

echo Opening Desktop Window...
node "%~dp0node_modules\electron\cli.js" "%~dp0electron\main.cjs"
