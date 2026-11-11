@echo off
setlocal
cd /d "%~dp0"
set "DJANGO_SETTINGS_MODULE=portal.settings"
echo Open http://127.0.0.1:8002 in your browser. Press Ctrl+C here to stop.
.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8002 portal.wsgi:application
pause
