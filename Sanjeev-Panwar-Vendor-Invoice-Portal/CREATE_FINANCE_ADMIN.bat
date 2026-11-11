@echo off
setlocal
cd /d "%~dp0"
set "DJANGO_SETTINGS_MODULE=portal.settings"
.venv\Scripts\python.exe manage.py createsuperuser
pause
