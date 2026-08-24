@echo off
title DocDeskew AI - Test Verification
cd /d "%~dp0"
echo ============================================================
echo Generating Sample Test Documents...
echo ============================================================
python create_test_docs.py
echo.
echo ============================================================
echo Running Automated Verification Test Suite...
echo ============================================================
python verify_engine.py
echo.
pause
