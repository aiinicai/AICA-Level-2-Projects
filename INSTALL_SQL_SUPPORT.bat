@echo off
setlocal
cd /d "%~dp0"
echo Installing SQL Server support (pyodbc) - needs internet, one time only...
py -3 -m pip install pyodbc
if errorlevel 1 python -m pip install pyodbc
echo.
echo Done. Now start CertifyFlow again with START_CERTIFYFLOW.bat
pause
