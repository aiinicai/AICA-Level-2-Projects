@echo off
python -c "import openpyxl, pdfplumber, docx, cv2, numpy, pytesseract, pypdfium2, PIL" 2>nul || (
  echo First run: installing required packages...
  python -m pip install -r requirements.txt
)
python main.py
