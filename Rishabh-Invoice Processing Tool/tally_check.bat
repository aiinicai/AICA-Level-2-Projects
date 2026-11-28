@echo off
REM Read-only Tally diagnostic. Output: tally_check_log.txt and tally_check_output\
cd /d %~dp0
call .venv\Scripts\activate.bat
python -m ipt.tools.tally_check "Manakpur Lime Product" > tally_check_log.txt 2>&1
type tally_check_log.txt
pause
