@echo off
title Stop GS Stock Audit Tracker
cd /d "%~dp0"
python stop_server.py
pause
