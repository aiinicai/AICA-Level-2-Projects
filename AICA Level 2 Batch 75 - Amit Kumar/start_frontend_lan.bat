@echo off
echo Starting FS Builder Lite Frontend on LAN...
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
