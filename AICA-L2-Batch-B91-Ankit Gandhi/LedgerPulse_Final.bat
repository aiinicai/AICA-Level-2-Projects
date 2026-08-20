@echo off
title LedgerPulse Launcher
:: 1. Clear any stuck processes
taskkill /F /IM node.exe >nul 2>&1

:: 2. Go to the new folder and start the server (the brain)
cd /d "C:\Users\ankit\Desktop\AICA-L2-Batch-91-Ankit-Gandhi\LP"
start /min cmd /c "npx tsx server.ts"

:: 3. Give the server 5 seconds to wake up
echo Starting LedgerPulse Server...
timeout /t 5 /nobreak >nul

:: 4. Start the EXE (the face)
echo Launching App...
start "" "C:\Users\ankit\Desktop\AICA-L2-Batch-91-Ankit-Gandhi\LP\LedgerPulse-win32-x64\LedgerPulse.exe"
exit