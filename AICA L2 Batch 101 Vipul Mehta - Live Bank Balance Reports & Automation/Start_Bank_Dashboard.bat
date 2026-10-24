@echo off
title Bank Dashboard Launcher
cd /d "%~dp0"

set PYTHONDONTWRITEBYTECODE=1
start "" pythonw -B bank_dashboard.py
exit
