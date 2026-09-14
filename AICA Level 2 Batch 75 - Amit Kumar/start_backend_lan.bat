@echo off
echo Starting FS Builder Lite Backend on LAN...
cd backend
venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
