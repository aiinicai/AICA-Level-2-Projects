@echo off
title Capital Gains Tax Comparison Calculator (12.5% vs 20%)
echo ==============================================================================
echo  CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
echo  Income-tax Act, 1961 - Finance (No. 2) Act, 2024 Regime
echo ==============================================================================
echo.
echo Starting application...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found in PATH. Please install Python 3.11+ and try again.
    pause
    exit /b 1
)

python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
