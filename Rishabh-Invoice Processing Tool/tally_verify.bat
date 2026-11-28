@echo off
cd /d %~dp0
call .venv\Scripts\activate.bat
python -m ipt.tools.tally_verify "Majisa Lime Product" 20261021 21-Oct-2026 > tally_verify_log.txt 2>&1
type tally_verify_log.txt
