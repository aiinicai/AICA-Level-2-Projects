@echo off
REM One-time setup: creates a virtual environment with Python 3.13 and installs dependencies.
cd /d %~dp0
echo Setting up IPT... (log: setup_log.txt)
(
  echo === IPT setup %date% %time% ===
  py -3.13 -m venv .venv || py -3.12 -m venv .venv || py -3.11 -m venv .venv || python -m venv .venv
  call .venv\Scripts\activate.bat
  python --version
  python -m pip install --timeout 120 --retries 10 --upgrade pip
  pip install --timeout 120 --retries 10 -r requirements.txt
  set QT_QPA_PLATFORM=offscreen
  python -m pytest -q
  echo === SETUP FINISHED ===
) > setup_log.txt 2>&1
type setup_log.txt | findstr /C:"passed" /C:"failed" /C:"ERROR" /C:"FINISHED"
echo.
echo Setup complete. You can close this window and start IPT with run_ipt.bat
pause
