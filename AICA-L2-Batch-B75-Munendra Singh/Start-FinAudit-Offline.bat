@echo off
setlocal enabledelayedexpansion
title FinAudit AI - Offline Ind AS Financial Statement Auditor
color 0A
echo ===============================================================================
echo          FINAUDIT AI - IND AS STATUTORY DISCLOSURE AUDITOR & VERIFIER
echo                       [ 100%% OFFLINE ON-DEVICE EDITION ]
echo ===============================================================================
echo.
echo Starting Offline Financial Audit Engine...
echo Privacy Guarantee: 100%% On-Device Execution. No cloud connection required.
echo.

cd /d "%~dp0"

IF NOT EXIST "node_modules\vite\bin\vite.js" (
    echo [!] Installing required dependencies...
    call npm install
)

echo Starting FinAudit Application on http://localhost:3000 ...
start "" http://localhost:3000
node "%~dp0node_modules\vite\bin\vite.js" --port 3000

pause
