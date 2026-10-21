"""Application configuration, paths and constants."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_NAME = "CA GST Filing Assistant"


def resource_dir() -> Path:
    """Folder that holds bundled resources (works with PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


DATA_ROOT = Path(os.environ.get("CAGST_DATA", Path.home() / "CA_GST_Filing_Assistant"))
DB_PATH = DATA_ROOT / "app_data.db"
LOG_DIR = DATA_ROOT / "logs"
BACKUP_DIR = DATA_ROOT / "backups"
CLIENTS_DIR = DATA_ROOT / "clients"
SCHEMA_PATH = resource_dir() / "schemas" / "offline_tool_schema.json"          # bundled, read-only
USER_SCHEMA_PATH = DATA_ROOT / "offline_tool_schema.json"                          # editable copy (preferred if present)

STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
    "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
    "24": "Gujarat", "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra", "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
    "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh",
    "38": "Ladakh", "97": "Other Territory", "96": "Other Countries",
}

# Rate slabs used only for sanity checks / snapping. Editable in Settings.
DEFAULT_RATES = "0,0.1,0.25,1,1.5,3,5,6,7.5,12,18,28,40"

DEFAULT_SETTINGS = {
    "rounding_tolerance": "1.00",
    "b2cl_threshold": "100000",
    "valid_rates": DEFAULT_RATES,
    "ocr_enabled": "1",
    "tesseract_path": "",
    "operator": "",
    "hsn_min_digits": "4",
    "auto_tax": "1",          # IGST/CGST/SGST = taxable value x rate
    "auto_pos": "1",          # place of supply from the recipient GSTIN (blank cells only)
}

REG_TYPES = ["Regular", "Composition", "SEZ Unit", "SEZ Developer", "Other"]
RETURN_TYPES = ["Monthly", "Quarterly (QRMP)"]
INVOICE_TYPES = [
    "Regular", "SEZ supplies with payment", "SEZ supplies without payment",
    "Deemed Exp", "Intra-State supplies attracting IGST", "Export",
]
SECTIONS = {
    "B2B": ("B2B - Registered recipient (Table 4)", True),
    "B2CL": ("B2C Large (Table 5)", True),
    "B2CS": ("B2C Others (Table 7)", True),
    "CDNR": ("Credit/Debit Notes - Registered (Table 9B)", True),
    "CDNUR": ("Credit/Debit Notes - Unregistered (Table 9B)", True),
    "EXP": ("Exports (Table 6A)", True),
    "NIL": ("Nil / Exempt / Non-GST (Table 8)", True),
    "AT": ("Advances received (Table 11A)", True),
    "ATADJ": ("Advances adjusted (Table 11B)", True),
    "AMEND": ("Amendments - enter via Master Template (Tables 9A/9C/10)", False),
}


# Allowed values for "Nature of Document" (GSTR-1 Table 13). Used for the Documents template and its validation.
DOC_NATURES = [
    "Invoices for outward supply",
    "Invoices for inward supply from unregistered person",
    "Revised Invoice",
    "Debit Note",
    "Credit Note",
    "Receipt voucher",
    "Payment Voucher",
    "Refund voucher",
    "Delivery Challan for job work",
    "Delivery Challan for supply on approval",
    "Delivery Challan in case of liquid gas",
    "Delivery Challan in cases other than by way of supply (excluding at S no. 9 to 11)",
]


def ensure_dirs() -> None:
    for d in (DATA_ROOT, LOG_DIR, BACKUP_DIR, CLIENTS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def setup_logging() -> None:
    """Log file never contains invoice-level details - only events and counts."""
    ensure_dirs()
    handler = RotatingFileHandler(LOG_DIR / "app.log", maxBytes=1_000_000, backupCount=3,
                                  encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(handler)
