@echo off
setlocal
title Mock Tally (synthetic data) - for demos and testing
cd /d "%~dp0"

set "PY=python"
%PY% --version >nul 2>&1
if errorlevel 1 set "PY=py"

echo ============================================================
echo  MOCK Tally server with SYNTHETIC data on localhost:9000
echo  Use this to demo the "Pull bank books" button without Tally.
echo  Close real Tally first (it uses the same port). Ctrl+C to stop.
echo ============================================================
%PY% mock_tally.py
pause
endlocal
