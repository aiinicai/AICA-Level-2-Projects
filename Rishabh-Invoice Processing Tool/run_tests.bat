@echo off
cd /d %~dp0
call .venv\Scripts\activate.bat
set QT_QPA_PLATFORM=offscreen
python -m pytest -q > test_log.txt 2>&1
type test_log.txt
pause
