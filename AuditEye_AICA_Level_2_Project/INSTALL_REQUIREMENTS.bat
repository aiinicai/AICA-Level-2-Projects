@echo off
title AuditEye - Install Requirements
cd /d "%~dp0"

echo ============================================================
echo AUDITEYE - ONE-TIME REQUIREMENTS INSTALLATION
echo ============================================================
echo.
echo This will install the Python libraries required by AuditEye.
echo.

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

echo.
echo ============================================================
echo Installation completed.
echo Now double-click START_AUDITEYE.bat
echo ============================================================
echo.
pause
