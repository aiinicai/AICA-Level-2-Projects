@echo off
title GS Stock Audit Tracker - Server Status
cd /d "%~dp0"
python check_status.py
pause
