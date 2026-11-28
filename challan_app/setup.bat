@echo off
REM One-time setup. Run by double-clicking. Requires Python 3.10+ installed ("Add python to PATH" ticked).
cd /d "%~dp0"
python -m venv venv || (echo Python not found. Install Python 3.10+ first. & pause & exit /b 1)
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt || (echo Package install failed - check internet/proxy. & pause & exit /b 1)
set FLASK_APP=app:create_app
flask init-db
echo.
echo Setup complete. Start the server with start_server.bat
echo First login: admin / admin123  (you will be forced to change it)
pause
