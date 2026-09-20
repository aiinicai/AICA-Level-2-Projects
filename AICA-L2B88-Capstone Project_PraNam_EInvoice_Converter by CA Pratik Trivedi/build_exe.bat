@echo off
REM Builds "PraNam E-Invoice Converter.exe" (Windows). Run from this folder.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --onefile --name "PraNam E-Invoice Converter" ^
  --collect-all pdfplumber --collect-all pdfminer --collect-all docx --collect-all openpyxl ^
  --collect-all cv2 --collect-all pytesseract --collect-all pypdfium2 main.py
echo.
echo Done. The EXE is in the "dist" folder.
echo Copy the Template folder next to the EXE in dist.
pause
