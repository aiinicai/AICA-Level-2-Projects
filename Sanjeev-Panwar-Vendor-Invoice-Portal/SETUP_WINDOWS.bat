@echo off
setlocal
cd /d "%~dp0"
set "DJANGO_SETTINGS_MODULE=portal.settings"
if not exist .venv\Scripts\python.exe (
    py -3.13 -m venv .venv
    if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe manage.py check
if errorlevel 1 goto fail
.venv\Scripts\python.exe manage.py migrate --noinput
if errorlevel 1 goto fail
.venv\Scripts\python.exe manage.py seed_demo
if errorlevel 1 goto fail
.venv\Scripts\python.exe manage.py collectstatic --noinput
if errorlevel 1 goto fail
.venv\Scripts\python.exe scripts\create_demo_pdf.py
if errorlevel 1 goto fail
echo Setup complete. Run CREATE_FINANCE_ADMIN.bat once, then START_PORTAL.bat.
pause
exit /b 0
:fail
echo Setup stopped. Read the error above. The original portal has not been changed.
pause
exit /b 1
