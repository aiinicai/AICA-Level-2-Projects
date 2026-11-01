@echo off
cd /d "%~dp0python"
start "" pythonw ct_app.pyw
if errorlevel 1 python ct_app.pyw
