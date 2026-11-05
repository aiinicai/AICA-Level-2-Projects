@echo off
TITLE LexSecure India Pro - Enterprise Legal & Regulatory Intelligence
cd /d "%~dp0"
echo ==============================================================================
echo             LEXSECURE INDIA PRO - ENTERPRISE LEGALTECH SUITE
echo       Statutory & Regulatory Intelligence for Indian Operating Entities
echo ==============================================================================
echo.
echo Launching LexSecure India Pro Desktop Application...
echo.
python main.py
if errorlevel 1 (
    echo.
    echo An error occurred while running LexSecure India Pro.
    pause
)
