@echo off
title AuditEye - AI Assisted Audit Red Flag Analyzer
cd /d "%~dp0"

echo ============================================================
echo AUDITEYE - AI Assisted Audit Red Flag Analyzer
echo ============================================================
echo.
echo Starting AuditEye...
echo.

python -m streamlit run AuditEye_No_License.py

echo.
echo If AuditEye did not open, please run INSTALL_REQUIREMENTS.bat first.
echo.
pause
