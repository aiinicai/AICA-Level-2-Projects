@echo off
cd /d "%~dp0"
set QT_QPA_PLATFORM=offscreen
".venv\Scripts\python.exe" -m pytest -q tests/test_backup.py > test_backup_log.txt 2>&1
