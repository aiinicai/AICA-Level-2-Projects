@echo off
title GST Notice Analyser - CA Desktop Workstation
echo ============================================================
echo   GST Notice Analyser  -  CA Desktop Workstation
echo   Local offline workstation for Chartered Accountants
echo ------------------------------------------------------------
echo   First run only:  npm install
echo ============================================================
echo.
start "" http://localhost:5180
npm.cmd run dev
pause
