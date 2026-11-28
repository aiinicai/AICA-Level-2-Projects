@echo off
REM Installs new packages after an update and runs the tests. Log: update_log.txt
cd /d %~dp0
(
  echo === IPT update %date% %time% ===
  call .venv\Scripts\activate.bat
  pip install --timeout 120 --retries 10 -r requirements.txt
  set QT_QPA_PLATFORM=offscreen
  python -m pytest -q
  echo === UPDATE FINISHED ===
) > update_log.txt 2>&1
type update_log.txt | findstr /C:"passed" /C:"failed" /C:"ERROR" /C:"FINISHED"
echo.
echo Update complete. Start IPT with run_ipt.bat
pause
