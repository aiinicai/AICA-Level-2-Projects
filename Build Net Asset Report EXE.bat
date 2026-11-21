@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Run Install Dependencies.bat first.
 pause
 exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pytest -q tests
if errorlevel 1 goto failed
.venv\Scripts\python.exe build_net_asset_exe.py
if errorlevel 1 goto failed
echo Build finished. Test dist\NetAssetReport.exe on a clean Windows PC before delivery.
pause
exit /b 0
:failed
echo Build or tests failed; do not distribute an earlier EXE as this version.
pause
exit /b 1
