"""Run from the project folder:  python tools/check_env.py
Checks every dependency and the offline OCR engines; reports anything Smart App Control blocks."""
import os
import sys

sys.path.insert(0, ".")
import app  # noqa: F401  pure-Python SQLAlchemy hook

print("Python", sys.version.split()[0], sys.executable)
checks = [
    ("sqlalchemy", "import sqlalchemy; from sqlalchemy import create_engine; create_engine('sqlite://').connect().close()"),
    ("sqlite3 (stdlib)", "import sqlite3; sqlite3.connect(':memory:')"),
    ("xml parser (stdlib)", "import xml.etree.ElementTree as E; E.fromstring('<a/>')"),
    ("requests", "import requests"),
    ("keyring", "import keyring; keyring.get_keyring()"),
    ("PyQt6.QtCore", "from PyQt6 import QtCore"),
    ("PyQt6.QtWidgets", "from PyQt6 import QtWidgets"),
    ("pg8000 (LAN DB driver)", "import pg8000"),
    ("pypdf (PDF text)", "import pypdf"),
    ("openpyxl (Excel)", "import openpyxl"),
    ("xlrd (old .xls bank statements)", "import xlrd"),
]
optional = [
    ("pypdfium2 (optional: PDF page images)", "import pypdfium2"),
    ("zxing-cpp (optional: e-invoice QR)", "import zxingcpp"),
]
bad = 0
for name, code in checks + optional:
    try:
        exec(code, {})
        print(f"  OK       {name}")
    except Exception as e:
        is_opt = (name, code) in optional
        bad += 0 if is_opt else 1
        blocked = "Application Control policy" in str(e) or "Device Guard" in str(e)
        tag = "BLOCKED" if blocked else ("absent " if is_opt else "FAILED ")
        print(f"  {tag}  {name}: {str(e).splitlines()[0][:120]}")

print("\nOffline OCR (for scanned invoices):")
from PyQt6.QtWidgets import QApplication
qa = QApplication.instance() or QApplication([])
from PyQt6.QtCore import QBuffer, QIODevice, Qt
from PyQt6.QtGui import QColor, QFont, QImage, QPainter
img = QImage(1400, 300, QImage.Format.Format_RGB32)
img.fill(QColor("white"))
p = QPainter(img)
f = QFont("Arial")
f.setPointSize(36)
p.setFont(f)
p.setPen(QColor("black"))
p.drawText(40, 150, "Invoice No INV-2026-123 Total 11800.00")
p.end()
buf = QBuffer()
buf.open(QIODevice.OpenModeFlag.WriteOnly)
img.save(buf, "PNG")
from app.extract import ocr
if os.name == "nt":
    import subprocess
    mode = subprocess.run(["powershell.exe", "-NoProfile", "-Command", "$ExecutionContext.SessionState.LanguageMode"],
                          capture_output=True, text=True).stdout.strip()
    print(f"  PowerShell language mode: {mode} (needs FullLanguage for Windows OCR)")
for fn in (ocr.windows_ocr, ocr.tesseract_ocr):
    r = fn(bytes(buf.data()))
    ok = "INV-2026-123" in r.text.replace(" ", "") or "11800" in r.text
    print(f"  {'OK     ' if ok else 'NOT OK '}  {fn.__name__}: {r.text.strip()[:60] or r.error[:160]}")
if os.name == "nt":
    from app.extract.ocr import windows_render_pdf
    tmp_pdf = os.path.join(os.environ.get("TEMP", "."), "aa_check.pdf")
    from PyQt6.QtGui import QPdfWriter
    w = QPdfWriter(tmp_pdf)
    pp = QPainter(w)
    pp.drawText(100, 100, "check")
    pp.end()
    pages = windows_render_pdf(__import__("pathlib").Path(tmp_pdf), 1)
    print(f"  {'OK     ' if pages else 'NOT OK '}  windows_render_pdf (page images of PDFs)")

print("\nGemini:")
from app.config import Settings, get_secret
key = get_secret("gemini_api_key")
if not key:
    print("  not set   (add the key in Settings)")
else:
    from app.extract import gemini
    s = Settings.load()
    try:
        inv = gemini.extract(key, s.gemini_model, text="TAX INVOICE\nInvoice No: T-1  Date: 01-11-2026\n"
                             "GSTIN 24AAACL1234F1Z5\nTaxable 100.00 CGST 9.00 SGST 9.00 Total 118.00", file_name="check")
        print(f"  OK       model {inv.model}: read invoice {inv.invoice_no}, total {inv.grand_total}")
    except Exception as e:
        print(f"  NOT OK   model {s.gemini_model}: {str(e)[:300]}")

print("\nAll required parts OK - run: python -m app.main" if not bad else "\nPaste this output back to Claude.")
