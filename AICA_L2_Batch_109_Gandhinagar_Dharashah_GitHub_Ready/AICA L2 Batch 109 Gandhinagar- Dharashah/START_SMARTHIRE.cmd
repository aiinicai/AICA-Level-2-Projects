@echo off
cd /d "%~dp0"
echo Starting SmartHire AI...
start "SmartHire Backend" cmd /k "cd /d ""%~dp0backend"" && python -m uvicorn main:app --host 127.0.0.1 --port 8000"
start "SmartHire Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"
timeout /t 6 /nobreak >nul
start "" "http://127.0.0.1:5173"
echo Keep the backend and frontend windows open while using SmartHire AI.
