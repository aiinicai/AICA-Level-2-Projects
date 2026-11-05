@echo off
TITLE LexSecure India Pro - Enterprise LegalTech Web App
cd /d "%~dp0"
echo ==============================================================================
echo             LEXSECURE INDIA PRO - ENTERPRISE LEGALTECH WEB APP
echo       Statutory & Regulatory Intelligence for Indian Operating Entities
echo ==============================================================================
echo.
echo Launching LexSecure India Pro Web Server...
echo.
python run_web.py
if errorlevel 1 (
    echo.
    echo An error occurred while running LexSecure India Pro.
    pause
)
