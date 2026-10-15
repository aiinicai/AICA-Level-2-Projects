BANK STATEMENT ANALYZER - OFFLINE DESKTOP APP
==============================================

START
  Double-click  BankStatementAnalyzer.exe  (or the "Bank Statement Analyzer" shortcut).
  A small black window opens and the app appears in your web browser after a few seconds
  (the very first start can take up to a minute). If the browser does not open, go to:
      http://127.0.0.1:8765/

FIRST TIME
  The app asks you to create the administrator account (name, email, password).
  Keep the password safe - it cannot be recovered. You can add more users later
  under "Users".

STOP
  Close the black "Bank Statement Analyzer" window.

WORKS OFFLINE
  No internet connection is needed. Everything runs on this computer and is reachable
  only from this computer. The whole app is one file of under 20 MB.

SCANNED STATEMENTS (OCR)
  Digital PDFs (including password-protected ones), Excel, CSV and MT940 files need
  nothing else. Scanned PDFs and photos (PNG/JPEG/TIFF) are read with the free
  Tesseract OCR program installed on this PC. If it is missing, install it once:
      winget install UB-Mannheim.TesseractOCR
  (or the installer from https://github.com/UB-Mannheim/tesseract/wiki). The black
  window shows "OCR : Tesseract found" when it is ready.

YOUR DATA
  Everything is stored in the  data  folder next to this program:
    data\bsa.db             the database (accounts, transactions, users, audit log)
    data\files\             uploaded statements, encrypted
    data\dev_secrets.json   the encryption and sign-in keys
  BACK UP THE WHOLE data FOLDER regularly (close the app first). Without
  dev_secrets.json the stored statements cannot be decrypted.

TRY IT
  The samples folder contains synthetic test statements (not real data).
  Add an account first (Accounts > Add account), or upload a statement and
  create the account from it.

UPDATE / UNINSTALL
  To update, replace BankStatementAnalyzer.exe (keep the data folder).
  To uninstall, close the app and delete this folder (this deletes your data too).

Third-party components: Python, FastAPI, SQLAlchemy, pdfplumber/pdfminer, pdfium, openpyxl,
reportlab, Next.js, React and Recharts, under their respective licences. Tesseract OCR
(Apache License 2.0) is a separate program installed on the PC.
