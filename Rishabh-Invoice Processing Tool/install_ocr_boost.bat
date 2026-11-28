@echo off
REM Installs OpenCV + numpy (better OCR: background cleaning, table-line removal, deskew)
REM from the wheels folder - no internet needed. Log: ocr_boost_log.txt
cd /d "%~dp0"
echo Installing OCR image tools... > ocr_boost_log.txt
".venv\Scripts\python.exe" -m pip install --no-index --find-links wheels "numpy>=2,<3" "opencv-python-headless>=4.10,<6" >> ocr_boost_log.txt 2>&1
".venv\Scripts\python.exe" -c "import cv2, numpy; print('OK opencv', cv2.__version__, 'numpy', numpy.__version__)" >> ocr_boost_log.txt 2>&1
type ocr_boost_log.txt
pause
