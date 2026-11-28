@echo off
REM Installs packages from the local wheels folder (no internet needed) and runs the tests.
cd /d %~dp0
(
  echo === IPT offline update %date% %time% ===
  call .venv\Scripts\activate.bat
  pip install --no-index --find-links wheels "PyMuPDF>=1.24,<2.0" "Pillow>=10" "pytesseract>=0.3.10" "openpyxl>=3.1"
  set QT_QPA_PLATFORM=offscreen
  python -m pytest -q
  echo === UPDATE FINISHED ===
) > update_offline_log.txt 2>&1
type update_offline_log.txt | findstr /C:"passed" /C:"failed" /C:"ERROR" /C:"FINISHED"
echo.
echo Update complete. Start IPT with run_ipt.bat
pause
