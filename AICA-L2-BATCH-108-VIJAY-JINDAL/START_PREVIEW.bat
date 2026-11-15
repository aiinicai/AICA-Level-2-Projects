@echo off
title CollectSaarthi - Portal Local Preview
echo ==============================================================
echo    COLLECTSAARTHI - INDIA'S COLLECTION CAREERS & TRAINING
echo ==============================================================
echo.
echo Starting local web server...
echo Your web browser will open automatically at http://localhost:5173
echo.
echo Press Ctrl + C anytime in this window to stop the server.
echo ==============================================================
echo.
start http://localhost:5173
npm --workspace web run dev
pause
