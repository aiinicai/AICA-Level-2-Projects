@echo off
echo Installing everything the converter needs (one time)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
python -c "import openpyxl, pdfplumber, docx, cv2, numpy, pytesseract, pypdfium2, PIL; print('All packages are installed.')" || echo SOMETHING FAILED - please send this window to your developer.
pause
