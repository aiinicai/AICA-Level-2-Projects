@echo off
title BizCard UAE - Backend Engine & API Server
echo ========================================================
echo        BizCard UAE - Backend & Vision API Server
echo ========================================================
echo.
cd /d "%~dp0"
echo Starting FastAPI REST Server on http://127.0.0.1:8000 ...
echo Mobile App available at:   http://127.0.0.1:8000/mobile/
echo Desktop Portal at:         http://127.0.0.1:8000/desktop/
echo Swagger API Docs at:       http://127.0.0.1:8000/docs
echo.
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
pause
