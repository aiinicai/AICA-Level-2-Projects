@echo off
setlocal enabledelayedexpansion
title FinAudit AI Desktop Application
color 0A
echo ===============================================================================
echo        FINAUDIT AI - IND AS STATUTORY COMPLIANCE AUDITOR & VERIFIER
echo                       [ 100%% OFFLINE DESKTOP APPLICATION ]
echo ===============================================================================
echo.
echo Launching Standalone Desktop Application...
echo.

cd /d "%~dp0"

IF EXIST "%~dp0release\win-unpacked\FinAudit-AI-Auditor.exe" (
    start "" "%~dp0release\win-unpacked\FinAudit-AI-Auditor.exe"
    exit
)

IF EXIST "%~dp0release\win-unpacked\FinAudit AI - Ind AS Compliance Verifier.exe" (
    start "" "%~dp0release\win-unpacked\FinAudit AI - Ind AS Compliance Verifier.exe"
    exit
)

echo Starting fallback desktop container...
node "%~dp0node_modules\electron\cli.js" "%~dp0electron\main.cjs"
