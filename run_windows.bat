@echo off
if not exist .venv ( py -3 -m venv .venv && .venv\Scripts\pip install -r requirements.txt )
.venv\Scripts\python Band_Baaja_Baraati.py
pause
