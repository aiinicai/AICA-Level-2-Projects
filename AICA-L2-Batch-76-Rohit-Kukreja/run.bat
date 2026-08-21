@echo off
REM AuditCraft startup (Windows). Build Prompt v2 §1.
setlocal

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

if not exist ".env" (
    echo Creating .env from .env.example ...
    copy /Y .env.example .env >nul
)

python -m alembic upgrade head
if errorlevel 1 goto :failed

python run.py
goto :eof

:failed
echo.
echo Database migration failed. Application not started.
exit /b 1
