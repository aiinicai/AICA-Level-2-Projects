@echo off
cd /d "%~dp0"
echo Installing libraries (first time only, please wait)...
python -m pip install -r requirements.txt
echo.
echo Starting the app. A browser window will open. Close this window to stop the app.
python -m streamlit run app.py
pause
