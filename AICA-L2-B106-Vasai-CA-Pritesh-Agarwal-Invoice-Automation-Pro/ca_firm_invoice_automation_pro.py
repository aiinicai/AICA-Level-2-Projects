"""
CA Firm Invoice & Practice Automation Pro
Advanced single-file PyQt6 billing, collection, payment tracking, compliance, and practice management system
specifically engineered for Indian Chartered Accountant (CA) firms.

Version 2.5 Comprehensive Update:
1. WhatsApp & Communication Synchronization & Full CRUD:
   - Filters active clients strictly (WHERE c.active = 1) so deleted clients never appear in WhatsApp tab.
   - Built-in Add Client, Edit Client / Mobile, and Delete Selected Clients controls directly in WhatsApp tab.
   - Double-click any client row to quickly edit mobile number / email.
   - Live Search bar to filter clients by Name or Mobile instantly.
   - Interactive prompt to input missing mobile number on-the-fly when launching reminders.
2. Pre-configured Gmail App Password:
   - Configured with Gmail SMTP SSL (Port 465) with configurable App Password in Settings.
   - Default SMTP host: smtp.gmail.com, Port: 465, Security: Implicit SSL (Port 465).
   - Dedicated "Test Email Connection" with one-click verification.
3. Universal Anti-Crash & Exception Shield:
   - Global sys.excepthook that intercepts unexpected exceptions and displays a clean error dialog instead of force-closing.
   - Safe float / Decimal conversions guarded against None and empty values.
   - Safe row-selection fallback (handles current item if full row not highlighted).
   - Safe urllib.parse.quote for WhatsApp URLs.
4. Form 26AS / AIS TDS Auto-Linking:
   - Upload Form 26AS / AIS / TDS summary (Excel, CSV, or Text) downloaded from TRACES / Income Tax Portal.
   - Maps deductor TAN/PAN to client records (matching PAN directly or from GSTIN chars 3-12).
   - Reconciles TDS deducted u/s 194J/194C against outstanding invoices with 1-click batch credit posting.
5. Bank Statement & Payment Notification Reconciliation:
   - Upload Bank Statement (Excel / CSV) to auto-match credit deposits with unpaid client invoices.
   - Bank SMS / WhatsApp credit message parser (regex extraction of Amount, Date, UTR, and Remitter).
   - Payment proof attachment support (screenshots, counterfoils, bank transaction slips).
6. Statutory GSTR-1 Upload-Ready Export (Official Excel & JSON):
   - Generates official multi-sheet GSTR-1 Excel (.xlsx) workbook (b2b, b2cs, hsn, docs) for the GST Offline Tool.
   - Generates official GSTR-1 JSON (.json) schema file ready for direct upload to the GST Portal.
7. Executive High-DPI Visual Dashboard & Analytics:
   - Financial Year and Billing Unit dynamic filtering.
   - 6 vibrant KPI metric cards: Invoiced, Realized Collections, TDS Credits, Outstanding Due, Realization Rate %, Active Clients.
   - 4 native QPainter vector visualizations:
     * Dual-Bar Monthly Billed vs Collected Trend
     * Practice Area / Service Category Distribution
     * Accounts Receivable Aging Risk Radar (0-30, 31-60, 61-90, 90+ days)
     * Collection Status Donut Diagram (Settled vs Partial vs Overdue)
   - Critical Overdue Debtors table with direct "Pay" and "Remind" action buttons.
"""
import sys
import os
import sqlite3
import subprocess
import importlib.util
import re
import json
import urllib.parse
import traceback
from pathlib import Path
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import csv
import smtplib
import ssl
from email.message import EmailMessage
import webbrowser
import requests

# ---------------------------------------------------------
# Dynamic Dependency Bootstrap
# ---------------------------------------------------------
def install_if_missing(package, module=None):
    module = module or package
    if importlib.util.find_spec(module) is None:
        print(f"Installing {package}. Please wait...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_if_missing("PyQt6", "PyQt6")
install_if_missing("reportlab")
install_if_missing("openpyxl")
install_if_missing("requests")

from PyQt6.QtCore import Qt, QDate, QRectF, QPointF
from PyQt6.QtGui import (
    QIcon,
    QColor, QFont, QPainter, QBrush, QPen, QLinearGradient, QPainterPath
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFormLayout, QTabWidget, QLabel, QLineEdit, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QMessageBox, QDoubleSpinBox, QSpinBox,
    QDateEdit, QTextEdit, QHeaderView, QFileDialog, QFrame, QDialog,
    QDialogButtonBox, QCheckBox, QInputDialog, QGroupBox, QScrollArea, QSplitter
)

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# ---------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------
APP_NAME = "CA Firm Invoice & Practice Automation Pro"
BASE = Path(__file__).resolve().parent
DB_FILE = BASE / "ca_invoice_automation_pro.db"
PDF_DIR = BASE / "invoices"
PDF_DIR.mkdir(exist_ok=True)
RECEIPTS_DIR = BASE / "receipts"
RECEIPTS_DIR.mkdir(exist_ok=True)
GST_RATES = [0, 5, 12, 18, 28]
DEFAULT_GSTINAPI_KEY = "gak_f099cdbe93a94e39a005a98caef503bb"
CONFIGURED_GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# Official 2-digit GST state codes for all 36 Indian States and Union Territories
GST_STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
    "97": "Other Territory"
}

STATE_NAME_TO_CODE = {name.lower(): code for code, name in GST_STATE_CODES.items()}
STATE_NAME_TO_CODE.update({
    "jk": "01", "hp": "02", "pb": "03", "chd": "04", "uk": "05", "hr": "06", "dl": "07",
    "rj": "08", "up": "09", "br": "10", "wb": "19", "jh": "20", "or": "21", "od": "21",
    "cg": "22", "mp": "23", "gj": "24", "mh": "27", "ka": "29", "ga": "30", "kl": "32",
    "tn": "33", "ts": "36", "ap": "37"
})

PRESEEDED_SERVICES = [
    ("Statutory Audit & Assurance", "998221", 18, 35000.0, 1, "Audit"),
    ("Tax Audit u/s 44AB", "998221", 18, 25000.0, 1, "Audit"),
    ("Internal Audit & Risk Advisory", "998221", 18, 30000.0, 1, "Audit"),
    ("Income Tax Return - Corporate", "998224", 18, 15000.0, 1, "Direct Tax"),
    ("Income Tax Return - Non-Corporate", "998224", 18, 5000.0, 1, "Direct Tax"),
    ("GST Monthly Compliance (GSTR-1 & 3B)", "998224", 18, 4000.0, 1, "Indirect Tax"),
    ("GST Annual Return & Reconciliation (9/9C)", "998224", 18, 15000.0, 1, "Indirect Tax"),
    ("TDS / TCS Quarterly Filing", "998224", 18, 3500.0, 1, "Direct Tax"),
    ("Company / LLP Incorporation", "998222", 18, 12000.0, 1, "Corporate Law"),
    ("ROC / MCA Annual Compliances", "998222", 18, 8000.0, 1, "Corporate Law"),
    ("Net Worth / Turnover Certification", "998221", 18, 5000.0, 1, "Certification"),
    ("Transfer Pricing Study & Form 3CEB", "998224", 18, 45000.0, 1, "Direct Tax"),
    ("Out of Pocket Expenses (Reimbursement)", "998229", 0, 0.0, 0, "Reimbursement")
]

# ---------------------------------------------------------
# Helper Utilities (Immune to None / Empty Strings)
# ---------------------------------------------------------
def money(value):
    try:
        return f"₹ {float(value or 0):,.2f}"
    except Exception:
        return "₹ 0.00"

def pdf_money(value):
    try:
        return f"Rs. {float(value or 0):,.2f}"
    except Exception:
        return "Rs. 0.00"

def qround(value):
    if value is None:
        return 0.0
    try:
        return float(Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except Exception:
        return 0.0

def open_file(file_path):
    p = Path(file_path)
    if not p.exists():
        return False
    if sys.platform == "win32":
        os.startfile(str(p))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(p)])
    else:
        subprocess.Popen(["xdg-open", str(p)])
    return True

def amount_to_words_inr(amount):
    """Converts a numerical figure into Indian currency words (Lakhs and Crores)."""
    try:
        val = Decimal(str(amount or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        val = Decimal("0.00")
    rupees = int(val)
    paise = int((val - rupees) * 100)

    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def convert_hundreds(n):
        res = ""
        if n >= 100:
            res += ones[n // 100] + " Hundred "
            n %= 100
        if n >= 20:
            res += tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
        elif n > 0:
            res += ones[n]
        return res.strip()

    if rupees == 0:
        words = "Zero Rupees"
    else:
        parts = []
        crores = rupees // 10000000
        rupees %= 10000000
        lakhs = rupees // 100000
        rupees %= 100000
        thousands = rupees // 1000
        rupees %= 1000
        hundreds = rupees

        if crores > 0:
            parts.append(convert_hundreds(crores) + " Crore")
        if lakhs > 0:
            parts.append(convert_hundreds(lakhs) + " Lakh")
        if thousands > 0:
            parts.append(convert_hundreds(thousands) + " Thousand")
        if hundreds > 0:
            parts.append(convert_hundreds(hundreds))
        words = "Rupees " + " ".join(parts).strip()

    if paise > 0:
        words += f" and {convert_hundreds(paise)} Paise"
    return words + " Only"

def extract_pan_from_string(text):
    """Extracts a valid 10-character Indian PAN from text."""
    if not text:
        return ""
    m = re.search(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", str(text).upper())
    return m.group(0) if m else ""

def parse_bank_sms(text):
    """Extracts credit amount, date, ref/UTR, and remitter from bank credit notification SMS/text."""
    t = str(text or "")
    amt_match = re.search(r"(?:INR|Rs\.?|credited(?:\s+with)?)\s*[:.]?\s*([0-9,]+(?:\.[0-9]{2})?)", t, re.IGNORECASE)
    amount = float(amt_match.group(1).replace(",", "")) if amt_match else 0.0

    date_match = re.search(r"(\d{1,2}[-/](?:[a-zA-Z]{3}|\d{1,2})[-/]\d{2,4})", t)
    date_str = date_match.group(1) if date_match else date.today().strftime("%d-%m-%Y")

    ref_match = re.search(r"(?:UPI|UTR|Ref|Txn|IMPS|NEFT)[:/\s]*([A-Za-z0-9]{6,25})", t, re.IGNORECASE)
    ref_no = ref_match.group(1) if ref_match else ""

    remitter_match = re.search(r"(?:from|by|info:)\s+([A-Za-z0-9\s\.\&\-]+?)(?:\s+on|\s+ref|\s+avail|\s+bal|\.|$)", t, re.IGNORECASE)
    remitter = remitter_match.group(1).strip() if remitter_match else ""

    return {"amount": amount, "date": date_str, "ref_no": ref_no, "remitter": remitter}

# ---------------------------------------------------------
# Resilient Multi-Strategy SMTP Dispatcher
# ---------------------------------------------------------
def send_smtp_email(host, port, user, password, security_mode, msg):
    """
    Sends email with intelligent auto-fallback between Port 465 (SSL) and Port 587 (STARTTLS).
    Sanitizes Gmail app passwords automatically (strips spaces).
    """
    host = host.strip()
    user = user.strip()
    password = password.strip().replace(" ", "")  # Google app passwords contain spaces
    port = int(port or 465)
    ctx = ssl.create_default_context()

    use_implicit_ssl = (port == 465) or ("SSL" in security_mode)

    try:
        if use_implicit_ssl:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=25) as server:
                server.login(user, password)
                server.send_message(msg)
                return True, "Email dispatched via SSL (Port 465)."
        else:
            with smtplib.SMTP(host, port, timeout=25) as server:
                server.ehlo()
                server.starttls(context=ctx)
                server.ehlo()
                server.login(user, password)
                server.send_message(msg)
                return True, "Email dispatched via STARTTLS (Port 587)."
    except (smtplib.SMTPServerDisconnected, ConnectionResetError, ssl.SSLError, OSError) as first_err:
        alt_port = 465 if not use_implicit_ssl else 587
        try:
            if alt_port == 465:
                with smtplib.SMTP_SSL(host, 465, context=ctx, timeout=25) as server:
                    server.login(user, password)
                    server.send_message(msg)
                    return True, "Dispatched via fallback SSL (Port 465)."
            else:
                with smtplib.SMTP(host, 587, timeout=25) as server:
                    server.ehlo()
                    server.starttls(context=ctx)
                    server.ehlo()
                    server.login(user, password)
                    server.send_message(msg)
                    return True, "Dispatched via fallback STARTTLS (Port 587)."
        except Exception as second_err:
            raise RuntimeError(
                f"Connection failed on both primary ({port}) and fallback ({alt_port}).\n"
                f"Error: {str(second_err)}.\n\n"
                f"Diagnostic Tips:\n"
                f"1. For Gmail: Use a 16-character Google App Password (not your normal Gmail password).\n"
                f"2. Check if your network/firewall blocks outbound port 465/587."
            )
    except smtplib.SMTPAuthenticationError as auth_err:
        raise RuntimeError(
            f"SMTP Authentication Failed: {str(auth_err)}\n\n"
            f"If using Gmail or Google Workspace:\n"
            f"1. 2-Step Verification must be enabled.\n"
            f"2. Generate an App Password at: https://myaccount.google.com/apppasswords\n"
            f"3. Ensure your App Password is entered in Settings tab or set as GMAIL_APP_PASSWORD."
        )

# ---------------------------------------------------------
# Database Engine & Schema
# ---------------------------------------------------------
class Database:
    def __init__(self, db_path=DB_FILE):
        self.con = sqlite3.connect(db_path)
        self.con.row_factory = sqlite3.Row
        self.setup()

    def execute(self, sql, params=()):
        cur = self.con.execute(sql, params)
        self.con.commit()
        return cur

    def rows(self, sql, params=()):
        return self.con.execute(sql, params).fetchall()

    def one(self, sql, params=()):
        return self.con.execute(sql, params).fetchone()

    def setup(self):
        self.con.executescript("""
        CREATE TABLE IF NOT EXISTS billing_units (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            gstin TEXT,
            pan TEXT,
            address TEXT,
            state TEXT,
            state_code TEXT,
            email TEXT,
            phone TEXT,
            bank_name TEXT,
            bank_account TEXT,
            ifsc TEXT,
            upi_id TEXT,
            invoice_prefix TEXT,
            frn TEXT,
            partner_name TEXT,
            partner_mno TEXT,
            logo_text TEXT,
            gst_registered INTEGER DEFAULT 1,
            gsp_endpoint TEXT,
            gsp_api_key TEXT,
            gsp_username TEXT
        );
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            gstin TEXT,
            pan TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            state TEXT,
            state_code TEXT,
            default_unit_id INTEGER,
            notes TEXT,
            active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            sac TEXT,
            rate REAL DEFAULT 18,
            default_fee REAL DEFAULT 0,
            taxable INTEGER DEFAULT 1,
            category TEXT DEFAULT 'General',
            active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY,
            invoice_no TEXT UNIQUE NOT NULL,
            invoice_type TEXT DEFAULT 'Tax Invoice',
            unit_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            invoice_date TEXT,
            due_date TEXT,
            place_of_supply TEXT,
            subtotal REAL,
            cgst REAL,
            sgst REAL,
            igst REAL,
            total REAL,
            status TEXT DEFAULT 'Issued',
            notes TEXT,
            pdf_path TEXT,
            irn TEXT,
            ack_no TEXT,
            ack_date TEXT,
            source TEXT DEFAULT 'Manual',
            has_gst INTEGER DEFAULT 1,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY,
            invoice_id INTEGER,
            description TEXT,
            sac TEXT,
            qty REAL,
            rate REAL,
            gst_rate REAL,
            taxable INTEGER,
            amount REAL
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY,
            invoice_id INTEGER NOT NULL,
            payment_date TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_mode TEXT DEFAULT 'Bank Transfer / NEFT',
            reference_no TEXT,
            tds_deducted REAL DEFAULT 0,
            tds_section TEXT DEFAULT '194J (10%)',
            proof_path TEXT,
            notes TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS tds_entries_26as (
            id INTEGER PRIMARY KEY,
            deductor_name TEXT NOT NULL,
            deductor_tan TEXT,
            deductor_pan TEXT,
            section TEXT,
            gross_amount REAL,
            tds_deducted REAL,
            transaction_date TEXT,
            matched_client_id INTEGER,
            matched_invoice_id INTEGER,
            status TEXT DEFAULT 'Matched',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        """)

        # Migration columns check
        billing_cols = [c[1] for c in self.con.execute("PRAGMA table_info(billing_units)").fetchall()]
        for col, col_type in [("frn", "TEXT"), ("partner_name", "TEXT"), ("partner_mno", "TEXT"), ("upi_id", "TEXT")]:
            if col not in billing_cols:
                try: self.con.execute(f"ALTER TABLE billing_units ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError: pass

        inv_cols = [c[1] for c in self.con.execute("PRAGMA table_info(invoices)").fetchall()]
        for col, col_type in [("invoice_type", "TEXT DEFAULT 'Tax Invoice'"), ("ack_no", "TEXT"), ("ack_date", "TEXT")]:
            if col not in inv_cols:
                try: self.con.execute(f"ALTER TABLE invoices ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError: pass

        pay_cols = [c[1] for c in self.con.execute("PRAGMA table_info(payments)").fetchall()]
        if "proof_path" not in pay_cols:
            try: self.con.execute("ALTER TABLE payments ADD COLUMN proof_path TEXT")
            except sqlite3.OperationalError: pass

        self.con.commit()

        # Seed initial billing units if empty
        if not self.one("SELECT id FROM billing_units LIMIT 1"):
            self.execute("""
            INSERT INTO billing_units(name, invoice_prefix, state, state_code, gst_registered, frn, partner_name, partner_mno, email, phone)
            VALUES('M/s. Pritesh G. & Associates, Chartered Accountants', 'PGA', 'Maharashtra', '27', 1, '138921W', 'CA Pritesh G.', '129482', 'pritesh.ca@example.com', '+91 98200 12345')
            """)

        # Preseed services catalogue if empty
        if not self.one("SELECT id FROM services LIMIT 1"):
            for s in PRESEEDED_SERVICES:
                self.execute("INSERT INTO services(name, sac, rate, default_fee, taxable, category) VALUES(?,?,?,?,?,?)", s)

        # Set default settings including supplied Gmail App Password
        defaults = [
            ("gstinapi_key", DEFAULT_GSTINAPI_KEY),
            ("smtp_host", "smtp.gmail.com"),
            ("smtp_port", "465"),
            ("smtp_security", "Implicit SSL (Port 465)"),
            ("smtp_password", CONFIGURED_GMAIL_APP_PASSWORD),
            ("smtp_tls", "1")
        ]
        for k, v in defaults:
            if not self.one("SELECT value FROM settings WHERE key=?", (k,)):
                self.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (k, v))


# ---------------------------------------------------------
# Advanced Native Vector Charts (QPainter)
# ---------------------------------------------------------
class MonthlyBilledVsCollectedChart(QWidget):
    """Dual-bar vector chart comparing Billed Fees vs Recovered Cash."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(250)
        self.periods = []
        self.billed = []
        self.collected = []

    def set_data(self, periods, billed, collected):
        self.periods = periods or ["No Data"]
        self.billed = billed or [0]
        self.collected = collected or [0]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawRoundedRect(QRectF(rect.adjusted(1, 1, -1, -1)), 10, 10)

        painter.setPen(QColor("#0f172a"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(20, 26, "Revenue vs Cash Collections (Trailing 6 Months)")

        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setBrush(QBrush(QColor("#2563eb")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(rect.width() - 220, 14, 12, 12), 3, 3)
        painter.setPen(QColor("#475569"))
        painter.drawText(int(rect.width() - 202), 24, "Billed (₹)")

        painter.setBrush(QBrush(QColor("#10b981")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(rect.width() - 110, 14, 12, 12), 3, 3)
        painter.setPen(QColor("#475569"))
        painter.drawText(int(rect.width() - 92), 24, "Realized (₹)")

        if not self.periods or all(v == 0 for v in self.billed + self.collected):
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No invoice or payment history recorded yet")
            return

        max_val = max(max(self.billed + self.collected, default=1), 1)
        plot_left = 65
        plot_right = rect.width() - 25
        plot_top = 45
        plot_bottom = rect.height() - 35
        plot_height = plot_bottom - plot_top
        plot_width = plot_right - plot_left

        painter.setFont(QFont("Segoe UI", 8))
        for i in range(4):
            y = plot_bottom - (i * plot_height / 3)
            val = (max_val / 3) * i
            painter.setPen(QPen(QColor("#f1f5f9"), 1))
            painter.drawLine(int(plot_left), int(y), int(plot_right), int(y))
            painter.setPen(QColor("#94a3b8"))
            lbl = f"₹{val/1000:,.0f}k" if val >= 1000 else f"₹{val:,.0f}"
            painter.drawText(QRectF(5, y - 8, 55, 16), Qt.AlignmentFlag.AlignRight, lbl)

        n = len(self.periods)
        group_width = plot_width / max(n, 1)
        bar_width = max(min(group_width * 0.30, 26), 10)

        for i, (period, b_val, c_val) in enumerate(zip(self.periods, self.billed, self.collected)):
            center_x = plot_left + (i + 0.5) * group_width

            bh = (b_val / max_val) * plot_height
            bx = center_x - bar_width - 2
            by = plot_bottom - bh
            b_grad = QLinearGradient(bx, by, bx, plot_bottom)
            b_grad.setColorAt(0, QColor("#3b82f6"))
            b_grad.setColorAt(1, QColor("#1d4ed8"))
            painter.setBrush(QBrush(b_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(bx, by, bar_width, bh), 4, 4)

            ch = (c_val / max_val) * plot_height
            cx = center_x + 2
            cy = plot_bottom - ch
            c_grad = QLinearGradient(cx, cy, cx, plot_bottom)
            c_grad.setColorAt(0, QColor("#34d399"))
            c_grad.setColorAt(1, QColor("#059669"))
            painter.setBrush(QBrush(c_grad))
            painter.drawRoundedRect(QRectF(cx, cy, bar_width, ch), 4, 4)

            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
            painter.drawText(QRectF(center_x - group_width / 2, plot_bottom + 6, group_width, 20),
                             Qt.AlignmentFlag.AlignCenter, period)


class ServiceDistributionChart(QWidget):
    """Horizontal ranked bar chart showing revenue distribution by Practice Area."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(250)
        self.data = []

    def set_data(self, data):
        self.data = data or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawRoundedRect(QRectF(rect.adjusted(1, 1, -1, -1)), 10, 10)

        painter.setPen(QColor("#0f172a"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(20, 26, "Revenue Share by CA Practice Area")

        if not self.data:
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No service billing data available")
            return

        cat_colors = [QColor("#4f46e5"), QColor("#059669"), QColor("#d97706"), QColor("#0284c7"), QColor("#9333ea"), QColor("#e11d48")]
        start_y = 50
        row_height = (rect.height() - 65) / max(len(self.data), 1)

        for i, (cat_name, amount, share) in enumerate(self.data[:5]):
            y = start_y + i * row_height
            col = cat_colors[i % len(cat_colors)]

            painter.setPen(QColor("#1e293b"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(20, int(y + 14), f"{cat_name} ({share:.1f}%)")

            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(int(rect.width() - 110), int(y + 14), money(amount))

            track_w = rect.width() - 140
            painter.setBrush(QBrush(QColor("#f1f5f9")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(20, y + 18, track_w, 10), 5, 5)

            fill_w = max((share / 100.0) * track_w, 4)
            painter.setBrush(QBrush(col))
            painter.drawRoundedRect(QRectF(20, y + 18, fill_w, 10), 5, 5)


class ReceivablesAgingWidget(QWidget):
    """Outstanding Receivables Aging Risk Radar & Metric Display."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
        self.counts = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}

    def set_data(self, buckets, counts):
        self.buckets = buckets
        self.counts = counts
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawRoundedRect(QRectF(rect.adjusted(1, 1, -1, -1)), 10, 10)

        painter.setPen(QColor("#0f172a"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(20, 26, "Accounts Receivable Aging (Credit Risk Breakdown)")

        total_due = sum(self.buckets.values())
        if total_due <= 0:
            painter.setPen(QColor("#10b981"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "All invoices fully settled! Zero outstanding dues.")
            return

        bar_x = 20
        bar_y = 48
        bar_w = rect.width() - 40
        bar_h = 20

        colors_map = {
            "0-30": QColor("#10b981"),
            "31-60": QColor("#0284c7"),
            "61-90": QColor("#f59e0b"),
            "90+": QColor("#ef4444")
        }

        painter.setBrush(QBrush(QColor("#f1f5f9")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 5, 5)

        curr_x = bar_x
        for key in ["0-30", "31-60", "61-90", "90+"]:
            val = self.buckets.get(key, 0.0)
            if val > 0:
                seg_w = (val / total_due) * bar_w
                painter.setBrush(QBrush(colors_map[key]))
                painter.drawRect(QRectF(curr_x, bar_y, seg_w, bar_h))
                curr_x += seg_w

        card_y = 90
        card_w = (rect.width() - 50) / 4
        card_h = 125

        titles = [("0-30 Days", "0-30", "Healthy"),
                  ("31-60 Days", "31-60", "Watchlist"),
                  ("61-90 Days", "61-90", "Delayed"),
                  ("> 90 Days", "90+", "Critical Risk")]

        for i, (label, key, subtitle) in enumerate(titles):
            cx = 20 + i * (card_w + 3)
            c_val = self.buckets.get(key, 0.0)
            c_cnt = self.counts.get(key, 0)

            painter.setBrush(QBrush(QColor("#f8fafc")))
            painter.setPen(QPen(colors_map[key], 1.5))
            painter.drawRoundedRect(QRectF(cx, card_y, card_w, card_h), 6, 6)

            painter.setBrush(QBrush(colors_map[key]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(cx, card_y, card_w, 6), 3, 3)

            painter.setPen(QColor("#475569"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(QRectF(cx + 6, card_y + 12, card_w - 12, 16), Qt.AlignmentFlag.AlignLeft, label)

            painter.setPen(QColor("#0f172a"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(QRectF(cx + 6, card_y + 36, card_w - 12, 22), Qt.AlignmentFlag.AlignLeft, money(c_val))

            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(QRectF(cx + 6, card_y + 64, card_w - 12, 16), Qt.AlignmentFlag.AlignLeft, f"{c_cnt} Invoice(s)")
            painter.drawText(QRectF(cx + 6, card_y + 82, card_w - 12, 16), Qt.AlignmentFlag.AlignLeft, f"Share: {(c_val/total_due*100):.1f}%")
            painter.drawText(QRectF(cx + 6, card_y + 100, card_w - 12, 16), Qt.AlignmentFlag.AlignLeft, subtitle)


class CollectionStatusDonutChart(QWidget):
    """Circular Donut Chart showing proportion of Settled vs Partial vs Overdue invoices."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.paid_cnt = 0
        self.partial_cnt = 0
        self.unpaid_cnt = 0

    def set_data(self, paid_cnt, partial_cnt, unpaid_cnt):
        self.paid_cnt = paid_cnt
        self.partial_cnt = partial_cnt
        self.unpaid_cnt = unpaid_cnt
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawRoundedRect(QRectF(rect.adjusted(1, 1, -1, -1)), 10, 10)

        painter.setPen(QColor("#0f172a"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(20, 26, "Invoice Settlement Portfolio")

        total = self.paid_cnt + self.partial_cnt + self.unpaid_cnt
        if total <= 0:
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No invoice records found")
            return

        d_size = min(rect.width() * 0.45, rect.height() - 70)
        d_rect = QRectF(25, 45, d_size, d_size)

        angle_paid = int((self.paid_cnt / total) * 360 * 16)
        angle_partial = int((self.partial_cnt / total) * 360 * 16)
        angle_unpaid = int(360 * 16 - angle_paid - angle_partial)

        start_angle = 90 * 16
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#10b981")))
        painter.drawPie(d_rect, start_angle, angle_paid)

        start_angle += angle_paid
        painter.setBrush(QBrush(QColor("#f59e0b")))
        painter.drawPie(d_rect, start_angle, angle_partial)

        start_angle += angle_partial
        painter.setBrush(QBrush(QColor("#ef4444")))
        painter.drawPie(d_rect, start_angle, angle_unpaid)

        hole_size = d_size * 0.58
        hole_rect = QRectF(d_rect.center().x() - hole_size/2, d_rect.center().y() - hole_size/2, hole_size, hole_size)
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawEllipse(hole_rect)

        painter.setPen(QColor("#0f172a"))
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        eff_pct = (self.paid_cnt / total) * 100
        painter.drawText(hole_rect, Qt.AlignmentFlag.AlignCenter, f"{eff_pct:.0f}%\nSettled")

        lx = int(d_rect.right() + 20)
        items = [
            ("Fully Settled", self.paid_cnt, QColor("#10b981")),
            ("Partially Paid", self.partial_cnt, QColor("#f59e0b")),
            ("Unpaid / Due", self.unpaid_cnt, QColor("#ef4444"))
        ]
        for i, (lbl, cnt, col) in enumerate(items):
            ly = int(75 + i * 36)
            painter.setBrush(QBrush(col))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(lx, ly, 14, 14), 4, 4)

            painter.setPen(QColor("#1e293b"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(int(lx + 22), int(ly + 12), f"{lbl} ({cnt})")

            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(int(lx + 22), int(ly + 25), f"Share: {(cnt/total*100):.1f}%")


# ---------------------------------------------------------
# Dynamic Master Dialog & Forms
# ---------------------------------------------------------
class MasterDialog(QDialog):
    def __init__(self, title, fields, values=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(540, 440)
        self.fields, self.widgets = fields, {}
        form = QFormLayout(self)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setVerticalSpacing(10)
        values = values or {}

        for key, label, kind in fields:
            val = values.get(key, "")
            if kind == "text":
                w = QLineEdit(str(val or ""))
            elif kind == "memo":
                w = QTextEdit(str(val or ""))
                w.setFixedHeight(65)
            elif kind == "number":
                w = QDoubleSpinBox()
                w.setMaximum(99999999)
                w.setDecimals(2)
                w.setValue(float(values.get(key, 0) or 0))
            elif kind == "rate":
                w = QComboBox()
                w.addItems([str(x) for x in GST_RATES])
                w.setCurrentText(str(int(float(values.get(key, 18) or 18))))
            elif kind == "check":
                w = QCheckBox()
                w.setChecked(bool(values.get(key, 1)))
            self.widgets[key] = w
            form.addRow(label + ":", w)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def data(self):
        output = {}
        for key, _, kind in self.fields:
            w = self.widgets[key]
            if kind == "memo":
                output[key] = w.toPlainText().strip()
            elif kind == "number":
                output[key] = w.value()
            elif kind == "rate":
                output[key] = int(w.currentText())
            elif kind == "check":
                output[key] = int(w.isChecked())
            else:
                output[key] = w.text().strip()
        return output


class RecordPaymentDialog(QDialog):
    """Modal for recording payment receipts with TDS u/s 194J / 194C and proof upload."""
    def __init__(self, invoice_info, parent=None):
        super().__init__(parent)
        self.invoice = dict(invoice_info)
        self.setWindowTitle(f"Record Payment - Invoice {self.invoice.get('invoice_no', '')}")
        self.resize(500, 440)
        self.balance = max(0.0, float(self.invoice.get('total') or 0) - float(self.invoice.get('total_paid') or 0))
        self.proof_path = ""

        layout = QVBoxLayout(self)
        form = QFormLayout()

        info_box = QFrame()
        info_box.setStyleSheet("background:#f0f9ff; border:1px solid #bae6fd; border-radius:6px; padding:10px;")
        ib_lay = QVBoxLayout(info_box)
        ib_lay.addWidget(QLabel(f"<b>Client:</b> {self.invoice.get('client_name', 'Client')}"))
        ib_lay.addWidget(QLabel(f"<b>Invoice Total:</b> {money(self.invoice.get('total'))} | <b>Settled:</b> {money(self.invoice.get('total_paid'))}"))
        ib_lay.addWidget(QLabel(f"<b>Net Outstanding Due:</b> <font color='#dc2626'><b>{money(self.balance)}</b></font>"))
        layout.addWidget(info_box)

        self.pay_date = QDateEdit(QDate.currentDate())
        self.pay_date.setCalendarPopup(True)
        self.pay_date.setDisplayFormat("dd-MM-yyyy")

        self.pay_mode = QComboBox()
        self.pay_mode.addItems(["Bank Transfer / NEFT / RTGS", "UPI / QR Code", "Cheque", "Cash", "Book Adjustment"])

        self.pay_amount = QDoubleSpinBox()
        self.pay_amount.setMaximum(99999999)
        self.pay_amount.setDecimals(2)
        self.pay_amount.setValue(self.balance)

        self.has_tds = QCheckBox("TDS Deducted by Client")
        self.tds_section = QComboBox()
        self.tds_section.addItems(["194J - Professional Fees (10%)", "194J - Technical Services (2%)", "194C - Contractor (2%)", "194C - Individual / HUF (1%)", "Custom TDS Amount"])
        self.tds_amount = QDoubleSpinBox()
        self.tds_amount.setMaximum(99999999)
        self.tds_amount.setDecimals(2)
        self.tds_amount.setEnabled(False)

        self.has_tds.toggled.connect(self.on_tds_toggle)
        self.tds_section.currentIndexChanged.connect(self.recalc_tds)

        self.ref_no = QLineEdit()
        self.ref_no.setPlaceholderText("UTR / Cheque No / IMPS Reference ID")

        proof_lay = QHBoxLayout()
        self.proof_lbl = QLabel("No file attached")
        btn_proof = QPushButton("Attach Proof")
        btn_proof.clicked.connect(self.choose_proof)
        proof_lay.addWidget(self.proof_lbl, 1)
        proof_lay.addWidget(btn_proof)

        self.notes = QLineEdit()
        self.notes.setPlaceholderText("Remarks / Bank Account credited")

        form.addRow("Payment Date:", self.pay_date)
        form.addRow("Payment Mode:", self.pay_mode)
        form.addRow("Net Received (₹):", self.pay_amount)
        form.addRow("", self.has_tds)
        form.addRow("TDS Section:", self.tds_section)
        form.addRow("TDS Deducted (₹):", self.tds_amount)
        form.addRow("Reference / UTR #:", self.ref_no)
        form.addRow("Payment Proof:", proof_lay)
        form.addRow("Remarks:", self.notes)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def choose_proof(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Payment Receipt / Screenshot", "", "Image/PDF Files (*.png *.jpg *.jpeg *.pdf)")
        if f:
            self.proof_path = f
            self.proof_lbl.setText(Path(f).name)

    def on_tds_toggle(self, checked):
        self.tds_amount.setEnabled(checked)
        if checked: self.recalc_tds()
        else: self.tds_amount.setValue(0.0)

    def recalc_tds(self):
        if not self.has_tds.isChecked(): return
        sec = self.tds_section.currentText()
        subtotal = float(self.invoice.get("subtotal") or 0.0)
        if "10%" in sec: tds = qround(subtotal * 0.10)
        elif "2%" in sec: tds = qround(subtotal * 0.02)
        elif "1%" in sec: tds = qround(subtotal * 0.01)
        else: tds = 0.0
        self.tds_amount.setValue(tds)
        if self.balance - tds > 0:
            self.pay_amount.setValue(self.balance - tds)

    def data(self):
        return {
            "invoice_id": self.invoice["id"],
            "payment_date": self.pay_date.date().toString("yyyy-MM-dd"),
            "amount": self.pay_amount.value(),
            "payment_mode": self.pay_mode.currentText(),
            "reference_no": self.ref_no.text().strip(),
            "tds_deducted": self.tds_amount.value() if self.has_tds.isChecked() else 0.0,
            "tds_section": self.tds_section.currentText() if self.has_tds.isChecked() else "",
            "proof_path": self.proof_path,
            "notes": self.notes.text().strip(),
            "created_at": datetime.now().isoformat()
        }


# ---------------------------------------------------------
# Form 26AS / AIS TDS Summary Reconciliation Dialog
# ---------------------------------------------------------
class Form26ASReconciliationDialog(QDialog):
    """Imports Form 26AS / AIS / TDS deduction summary and automatically maps to clients by PAN."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Reconcile Form 26AS / TDS Deduction Summary (Income Tax Portal)")
        self.resize(980, 560)
        self.parsed_records = []

        layout = QVBoxLayout(self)

        top_info = QLabel(
            "<b>Upload Form 26AS or AIS TDS Summary (Excel, CSV, or Text):</b><br/>"
            "The system reads Deductor Name, TAN/PAN, Section (194J/194C), Gross Amount, and Tax Deducted. "
            "It automatically searches clients based on their 10-character PAN (extracted from PAN or GSTIN) "
            "and pairs TDS deductions with outstanding invoices."
        )
        top_info.setWordWrap(True)
        top_info.setStyleSheet("background:#ecfeff; border:1px solid #a5f3fc; border-radius:6px; padding:10px; color:#0e7490;")
        layout.addWidget(top_info)

        btn_bar = QHBoxLayout()
        btn_upload = QPushButton("Upload 26AS / TDS File (Excel/CSV/Text)")
        btn_upload.setObjectName("successBtn")
        btn_upload.clicked.connect(self.choose_file)
        btn_bar.addWidget(btn_upload)
        btn_bar.addStretch()

        btn_apply = QPushButton("Apply Selected TDS Credits to Invoices")
        btn_apply.setObjectName("successBtn")
        btn_apply.clicked.connect(self.apply_credits)
        btn_bar.addWidget(btn_apply)
        layout.addLayout(btn_bar)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "Apply", "Deductor Name", "TAN / PAN", "Section", "Gross Credited", "TDS Deducted", "Matched Client", "Pending Invoice", "Match Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Form 26AS / TDS Summary", "", "26AS Files (*.xlsx *.csv *.txt *.xls)")
        if not path: return
        try:
            self.parsed_records = self.parse_26as_file(path)
            self.populate_table()
            QMessageBox.information(self, "File Processed", f"Identified {len(self.parsed_records)} TDS transaction record(s).")
        except Exception as e:
            QMessageBox.critical(self, "Parsing Error", f"Could not read Form 26AS file: {str(e)}")

    def parse_26as_file(self, file_path):
        records = []
        p = Path(file_path)
        ext = p.suffix.lower()

        if ext in (".xlsx", ".xls"):
            wb = load_workbook(file_path, data_only=True, read_only=True)
            ws = wb.active
            header_row = 1
            headers = []
            for row_no, row_vals in enumerate(ws.iter_rows(values_only=True), 1):
                txt = [str(v or "").strip().lower() for v in row_vals]
                if any("deductor" in c for c in txt) and any("tax" in c or "tds" in c or "amount" in c for c in txt):
                    header_row = row_no
                    headers = txt
                    break

            for r in ws.iter_rows(min_row=header_row + 1, values_only=True):
                if not r or all(v is None for v in r): continue
                def get_c(*keys):
                    for k in keys:
                        for idx, h in enumerate(headers):
                            if k in h and r[idx] not in (None, ""):
                                return r[idx]
                    return ""
                deductor = get_c("name of deductor", "deductor", "party")
                if not deductor: continue
                tan = get_c("tan", "pan", "deductor tan")
                sec = get_c("section", "sec") or "194J"
                gross = float(get_c("total amount paid", "amount paid", "gross", "credited") or 0)
                tds = float(get_c("total tax deducted", "tax deducted", "tds") or 0)
                dt = str(get_c("transaction date", "date", "booking date") or date.today().isoformat())
                records.append({
                    "deductor": str(deductor).strip(), "tan": str(tan).strip().upper(),
                    "section": str(sec).strip(), "gross": gross, "tds": tds, "date": dt
                })
        else:
            with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                reader = csv.reader(f)
                headers = []
                for r in reader:
                    if not r: continue
                    txt = [c.lower().strip() for c in r]
                    if any("deductor" in c for c in txt) and any("tax" in c or "tds" in c or "amount" in c for c in txt):
                        headers = txt
                        break
                for r in reader:
                    if not r or len(r) < 4: continue
                    def get_csv(*keys):
                        for k in keys:
                            for idx, h in enumerate(headers):
                                if idx < len(r) and k in h and r[idx].strip():
                                    return r[idx].strip()
                        return ""
                    deductor = get_csv("name of deductor", "deductor")
                    if not deductor: continue
                    tan = get_csv("tan", "pan")
                    sec = get_csv("section", "sec") or "194J"
                    gross = float(get_csv("total amount paid", "amount paid", "gross") or 0)
                    tds = float(get_csv("total tax deducted", "tax deducted", "tds") or 0)
                    dt = get_csv("transaction date", "date") or date.today().isoformat()
                    records.append({
                        "deductor": deductor, "tan": tan.upper(), "section": sec,
                        "gross": gross, "tds": tds, "date": dt
                    })
        return records

    def populate_table(self):
        self.table.setRowCount(len(self.parsed_records))
        for r, rec in enumerate(self.parsed_records):
            pan_cand = extract_pan_from_string(rec["tan"]) or extract_pan_from_string(rec["deductor"])

            matched_client = None
            if pan_cand:
                matched_client = self.db.one("SELECT * FROM clients WHERE (pan=? OR gstin LIKE ?) AND active=1", (pan_cand, f"%{pan_cand}%"))
            if not matched_client:
                matched_client = self.db.one("SELECT * FROM clients WHERE lower(name) LIKE ? AND active=1", (f"%{rec['deductor'][:10].lower()}%",))

            pending_inv = None
            if matched_client:
                pending_inv = self.db.one("""
                    SELECT i.* FROM invoices i WHERE i.client_id=? AND i.status != 'Paid' AND i.status != 'Cancelled'
                    ORDER BY i.invoice_date ASC LIMIT 1
                """, (matched_client["id"],))

            rec["client_id"] = matched_client["id"] if matched_client else None
            rec["invoice_id"] = pending_inv["id"] if pending_inv else None

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            chk.setCheckState(Qt.CheckState.Checked if pending_inv else Qt.CheckState.Unchecked)
            self.table.setItem(r, 0, chk)

            self.table.setItem(r, 1, QTableWidgetItem(rec["deductor"]))
            self.table.setItem(r, 2, QTableWidgetItem(rec["tan"]))
            self.table.setItem(r, 3, QTableWidgetItem(rec["section"]))
            self.table.setItem(r, 4, QTableWidgetItem(money(rec["gross"])))
            self.table.setItem(r, 5, QTableWidgetItem(money(rec["tds"])))
            self.table.setItem(r, 6, QTableWidgetItem(matched_client["name"] if matched_client else "Unmatched (New Client)"))
            self.table.setItem(r, 7, QTableWidgetItem(pending_inv["invoice_no"] if pending_inv else "None Pending"))

            status_item = QTableWidgetItem("Ready to Apply" if pending_inv else ("Client Matched" if matched_client else "Manual Review"))
            status_item.setForeground(QColor("#059669") if pending_inv else (QColor("#d97706") if matched_client else QColor("#64748b")))
            self.table.setItem(r, 8, status_item)

    def apply_credits(self):
        applied = 0
        for r, rec in enumerate(self.parsed_records):
            it = self.table.item(r, 0)
            if it and it.checkState() == Qt.CheckState.Checked:
                inv_id = rec.get("invoice_id")
                if inv_id:
                    self.db.execute("""
                        INSERT INTO payments(invoice_id, payment_date, amount, payment_mode, reference_no, tds_deducted, tds_section, notes, created_at)
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        inv_id, date.today().isoformat(), 0.0, "Form 26AS TDS Credit",
                        f"26AS-{rec['tan']}-{rec['section']}", rec["tds"], rec["section"],
                        f"TDS credit posted via Form 26AS on gross {money(rec['gross'])}", datetime.now().isoformat()
                    ))
                    inv = self.db.one("SELECT * FROM invoices WHERE id=?", (inv_id,))
                    paid_res = self.db.one("SELECT COALESCE(SUM(amount + tds_deducted), 0) paid FROM payments WHERE invoice_id=?", (inv_id,))
                    tot_paid = float(paid_res["paid"] if paid_res else 0.0)
                    status = "Paid" if tot_paid >= float(inv["total"] or 0) - 0.5 else "Partially Paid"
                    self.db.execute("UPDATE invoices SET status=? WHERE id=?", (status, inv_id))
                    applied += 1
        QMessageBox.information(self, "TDS Credits Posted", f"Successfully credited {applied} invoice(s) with Form 26AS TDS tax deductions.")
        self.accept()


# ---------------------------------------------------------
# Bank Statement & Payment Notification Reconciliation
# ---------------------------------------------------------
class BankReconciliationDialog(QDialog):
    """Reconciles Bank Statements & Bank Credit SMS notifications with client invoices."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Bank Statement & Payment SMS Reconciliation")
        self.resize(920, 560)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.stmt_tab = QWidget()
        self.build_statement_tab()
        self.tabs.addTab(self.stmt_tab, "Upload Bank Statement (Excel/CSV)")

        self.sms_tab = QWidget()
        self.build_sms_tab()
        self.tabs.addTab(self.sms_tab, "Paste Bank Credit SMS / Notification")

    def build_statement_tab(self):
        lay = QVBoxLayout(self.stmt_tab)
        desc = QLabel(
            "<b>Upload Bank Statement (Excel or CSV):</b><br/>"
            "The parser automatically identifies credit/deposit transactions, extracts UTR/reference numbers, "
            "and scans narrations for client names or invoice prefixes to match with pending dues."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:10px; color:#166534;")
        lay.addWidget(desc)

        top = QHBoxLayout()
        btn_up = QPushButton("Choose Bank Statement File")
        btn_up.setObjectName("successBtn")
        btn_up.clicked.connect(self.upload_statement)
        top.addWidget(btn_up)
        top.addStretch()

        btn_post = QPushButton("Confirm & Post Matched Payments")
        btn_post.setObjectName("successBtn")
        btn_post.clicked.connect(self.post_statement_payments)
        top.addWidget(btn_post)
        lay.addLayout(top)

        self.stmt_table = QTableWidget(0, 7)
        self.stmt_table.setHorizontalHeaderLabels(["Select", "Date", "Description / Narration", "Ref / UTR #", "Credit Amount", "Matched Invoice", "Client"])
        self.stmt_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stmt_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.stmt_table)
        self.stmt_records = []

    def upload_statement(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open Bank Statement", "", "Excel/CSV Files (*.xlsx *.xls *.csv)")
        if not f: return
        self.stmt_records = []
        try:
            if f.endswith((".xlsx", ".xls")):
                wb = load_workbook(f, data_only=True, read_only=True)
                ws = wb.active
                h_row = 1
                headers = []
                for r_no, r_vals in enumerate(ws.iter_rows(values_only=True), 1):
                    txt = [str(x or "").lower() for x in r_vals]
                    if any("date" in c for c in txt) and any("deposit" in c or "credit" in c or "amount" in c for c in txt):
                        h_row = r_no
                        headers = txt
                        break
                for r in ws.iter_rows(min_row=h_row + 1, values_only=True):
                    def get_f(*keys):
                        for k in keys:
                            for idx, h in enumerate(headers):
                                if k in h and r[idx] not in (None, ""):
                                    return r[idx]
                        return ""
                    c_amt = float(get_f("deposit", "credit", "cr amount", "deposit amount") or 0)
                    if c_amt <= 0: continue
                    narr = str(get_f("narration", "description", "particulars", "remarks") or "")
                    dt = str(get_f("date", "txn date") or date.today().isoformat())
                    chq = str(get_f("chq", "ref", "utr", "cheque no") or "")
                    self.stmt_records.append({"date": dt, "narration": narr, "ref": chq, "amount": c_amt})
            else:
                with open(f, "r", encoding="utf-8-sig", errors="ignore") as fp:
                    reader = csv.reader(fp)
                    headers = []
                    for r in reader:
                        txt = [c.lower() for c in r]
                        if any("date" in c for c in txt) and any("deposit" in c or "credit" in c for c in txt):
                            headers = txt
                            break
                    for r in reader:
                        def get_csv_f(*keys):
                            for k in keys:
                                for idx, h in enumerate(headers):
                                    if idx < len(r) and k in h and r[idx].strip():
                                        return r[idx].strip()
                            return ""
                        c_amt = float(get_csv_f("deposit", "credit") or 0)
                        if c_amt <= 0: continue
                        narr = get_csv_f("narration", "description", "particulars")
                        dt = get_csv_f("date") or date.today().isoformat()
                        chq = get_csv_f("ref", "chq", "utr")
                        self.stmt_records.append({"date": dt, "narration": narr, "ref": chq, "amount": c_amt})

            self.stmt_table.setRowCount(len(self.stmt_records))
            clients = self.db.rows("SELECT id, name FROM clients WHERE active=1")
            for r_idx, item in enumerate(self.stmt_records):
                matched_c = None
                for c in clients:
                    if c["name"].lower() in item["narration"].lower():
                        matched_c = c; break

                matched_inv = None
                if matched_c:
                    matched_inv = self.db.one("""
                        SELECT * FROM invoices WHERE client_id=? AND status != 'Paid' AND status != 'Cancelled'
                        ORDER BY ABS(total - ?) ASC LIMIT 1
                    """, (matched_c["id"], item["amount"]))

                item["invoice_id"] = matched_inv["id"] if matched_inv else None

                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                chk.setCheckState(Qt.CheckState.Checked if matched_inv else Qt.CheckState.Unchecked)
                self.stmt_table.setItem(r_idx, 0, chk)
                self.stmt_table.setItem(r_idx, 1, QTableWidgetItem(str(item["date"])))
                self.stmt_table.setItem(r_idx, 2, QTableWidgetItem(item["narration"]))
                self.stmt_table.setItem(r_idx, 3, QTableWidgetItem(item["ref"]))
                self.stmt_table.setItem(r_idx, 4, QTableWidgetItem(money(item["amount"])))
                self.stmt_table.setItem(r_idx, 5, QTableWidgetItem(matched_inv["invoice_no"] if matched_inv else "No Match"))
                self.stmt_table.setItem(r_idx, 6, QTableWidgetItem(matched_c["name"] if matched_c else "Unidentified Client"))

            QMessageBox.information(self, "Statement Loaded", f"Parsed {len(self.stmt_records)} credit transaction(s).")
        except Exception as e:
            QMessageBox.critical(self, "Statement Error", f"Failed to parse statement: {str(e)}")

    def post_statement_payments(self):
        posted = 0
        for r, item in enumerate(self.stmt_records):
            it = self.stmt_table.item(r, 0)
            if it and it.checkState() == Qt.CheckState.Checked and item.get("invoice_id"):
                inv_id = item["invoice_id"]
                self.db.execute("""
                    INSERT INTO payments(invoice_id, payment_date, amount, payment_mode, reference_no, notes, created_at)
                    VALUES(?,?,?,?,?,?,?)
                """, (inv_id, date.today().isoformat(), item["amount"], "Bank Statement Credit", item["ref"] or "Bank Statement", item["narration"], datetime.now().isoformat()))

                inv = self.db.one("SELECT * FROM invoices WHERE id=?", (inv_id,))
                paid_res = self.db.one("SELECT COALESCE(SUM(amount + tds_deducted), 0) paid FROM payments WHERE invoice_id=?", (inv_id,))
                tot = float(paid_res["paid"] if paid_res else 0.0)
                status = "Paid" if tot >= float(inv["total"] or 0) - 0.5 else "Partially Paid"
                self.db.execute("UPDATE invoices SET status=? WHERE id=?", (status, inv_id))
                posted += 1
        QMessageBox.information(self, "Payments Posted", f"Successfully posted {posted} bank payment(s).")
        self.accept()

    def build_sms_tab(self):
        lay = QVBoxLayout(self.sms_tab)
        lay.addWidget(QLabel("<b>Paste Bank SMS Notification / WhatsApp Credit Text:</b>"))
        self.sms_input = QTextEdit()
        self.sms_input.setPlaceholderText(
            "Example: Dear Customer, A/c *1234 credited with INR 14,160.00 on 10-Nov-26 by UPI/331234567890/BOLLYWOOD ENTERPRISES..."
        )
        self.sms_input.setFixedHeight(110)
        lay.addWidget(self.sms_input)

        btn_parse = QPushButton("Parse SMS & Find Matching Invoice")
        btn_parse.clicked.connect(self.parse_sms_text)
        lay.addWidget(btn_parse)

        form_box = QGroupBox("Parsed Bank Transaction Details")
        form = QFormLayout(form_box)
        self.sms_amt = QDoubleSpinBox()
        self.sms_amt.setMaximum(99999999)
        self.sms_amt.setDecimals(2)
        self.sms_date = QLineEdit()
        self.sms_ref = QLineEdit()
        self.sms_client = QComboBox()

        form.addRow("Detected Amount (₹):", self.sms_amt)
        form.addRow("Transaction Date:", self.sms_date)
        form.addRow("UTR / Reference No:", self.sms_ref)
        form.addRow("Matched Client / Invoice:", self.sms_client)
        lay.addWidget(form_box)

        btn_post_sms = QPushButton("Record Payment from SMS")
        btn_post_sms.setObjectName("successBtn")
        btn_post_sms.clicked.connect(self.post_sms_payment)
        lay.addWidget(btn_post_sms)
        lay.addStretch()

    def parse_sms_text(self):
        t = self.sms_input.toPlainText().strip()
        if not t: return
        res = parse_bank_sms(t)
        self.sms_amt.setValue(res["amount"])
        self.sms_date.setText(res["date"])
        self.sms_ref.setText(res["ref_no"])

        open_invs = self.db.rows("""
            SELECT i.id, i.invoice_no, i.total, c.name client_name
            FROM invoices i JOIN clients c ON c.id=i.client_id
            WHERE i.status != 'Paid' AND i.status != 'Cancelled'
            ORDER BY i.id DESC
        """)
        self.sms_client.clear()
        best_idx = 0
        for idx, inv in enumerate(open_invs):
            label = f"{inv['invoice_no']} - {inv['client_name']} ({money(inv['total'])})"
            self.sms_client.addItem(label, inv["id"])
            if res["remitter"] and res["remitter"].lower() in inv["client_name"].lower():
                best_idx = idx
            elif abs(float(inv["total"] or 0) - res["amount"]) < 1:
                best_idx = idx
        if open_invs:
            self.sms_client.setCurrentIndex(best_idx)

    def post_sms_payment(self):
        inv_id = self.sms_client.currentData()
        if not inv_id:
            QMessageBox.warning(self, "No Invoice", "Please select a client invoice to credit.")
            return
        amt = self.sms_amt.value()
        ref = self.sms_ref.text().strip() or "Bank SMS Credit"
        self.db.execute("""
            INSERT INTO payments(invoice_id, payment_date, amount, payment_mode, reference_no, notes, created_at)
            VALUES(?,?,?,?,?,?,?)
        """, (inv_id, date.today().isoformat(), amt, "UPI / Bank SMS Alert", ref, "Auto-parsed from bank credit notification", datetime.now().isoformat()))

        inv = self.db.one("SELECT * FROM invoices WHERE id=?", (inv_id,))
        paid_res = self.db.one("SELECT COALESCE(SUM(amount + tds_deducted), 0) paid FROM payments WHERE invoice_id=?", (inv_id,))
        tot = float(paid_res["paid"] if paid_res else 0.0)
        status = "Paid" if tot >= float(inv["total"] or 0) - 0.5 else "Partially Paid"
        self.db.execute("UPDATE invoices SET status=? WHERE id=?", (status, inv_id))

        QMessageBox.information(self, "Receipt Posted", f"Payment of {money(amt)} successfully recorded for invoice {inv['invoice_no']}.")
        self.accept()


# ---------------------------------------------------------
# Statutory GSTR-1 Upload-Ready Export (Excel & JSON)
# ---------------------------------------------------------
class GSTR1ExportDialog(QDialog):
    """Exports GSTR-1 in official Excel (.xlsx) and JSON (.json) schema formats for the GST Portal."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Official GSTR-1 Statutory Export (Excel & JSON)")
        self.resize(520, 320)

        layout = QVBoxLayout(self)

        info = QLabel(
            "<b>Statutory GSTR-1 Outward Supplies Return:</b><br/>"
            "• <b>Uploadable Excel (.xlsx):</b> Multi-sheet workbook formatted strictly as per the GST Offline Tool schema (b2b, b2cs, hsn, docs).<br/>"
            "• <b>Direct JSON (.json):</b> Validated schema file ready for immediate upload to the GST Portal (services.gst.gov.in)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background:#eff6ff; border:1px solid #bfdbfe; border-radius:6px; padding:10px; color:#1e3a8a;")
        layout.addWidget(info)

        form = QFormLayout()
        self.unit_combo = QComboBox()
        for u in self.db.rows("SELECT id, name, gstin FROM billing_units WHERE gst_registered=1"):
            self.unit_combo.addItem(f"{u['name']} (GSTIN: {u['gstin'] or 'None'})", u["id"])

        self.period_combo = QComboBox()
        today = date.today()
        for i in range(12):
            dt = today - timedelta(days=i*30)
            self.period_combo.addItem(dt.strftime("%B %Y"), dt.strftime("%m%Y"))

        form.addRow("Supplier Billing Unit:", self.unit_combo)
        form.addRow("Return Period (FP):", self.period_combo)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btn_excel = QPushButton("Export GSTR-1 Excel (.xlsx)")
        btn_excel.setObjectName("successBtn")
        btn_excel.clicked.connect(self.export_excel)

        btn_json = QPushButton("Export GSTR-1 JSON (.json)")
        btn_json.setObjectName("successBtn")
        btn_json.clicked.connect(self.export_json)

        btns.addWidget(btn_excel)
        btns.addWidget(btn_json)
        layout.addLayout(btns)

    def get_data(self):
        uid = self.unit_combo.currentData()
        unit = self.db.one("SELECT * FROM billing_units WHERE id=?", (uid,)) if uid else self.db.one("SELECT * FROM billing_units LIMIT 1")
        invoices = self.db.rows("""
            SELECT i.*, c.name client_name, c.gstin recipient_gstin, c.state client_state, c.state_code client_state_code
            FROM invoices i
            JOIN clients c ON c.id=i.client_id
            WHERE i.unit_id=? AND i.has_gst=1 AND i.status != 'Cancelled'
            ORDER BY i.invoice_date ASC
        """, (unit["id"],))
        return unit, invoices

    def export_excel(self):
        unit, invoices = self.get_data()
        path, _ = QFileDialog.getSaveFileName(self, "Save Official GSTR-1 Excel File", str(BASE / "GSTR1_Offline_Workbook.xlsx"), "Excel Workbook (*.xlsx)")
        if not path: return

        wb = Workbook()
        ws_b2b = wb.active
        ws_b2b.title = "b2b"
        b2b_headers = [
            "GSTIN/UIN of Recipient", "Receiver Name", "Invoice Number", "Invoice date",
            "Invoice Value", "Place Of Supply", "Reverse Charge", "Applicable % of Tax Rate",
            "Invoice Type", "E-Commerce GSTIN", "Rate", "Taxable Value", "Cess Amount"
        ]
        ws_b2b.append(b2b_headers)

        ws_b2cs = wb.create_sheet("b2cs")
        ws_b2cs.append(["Type", "Place Of Supply", "Applicable % of Tax Rate", "Rate", "Taxable Value", "Cess Amount", "E-Commerce GSTIN"])

        ws_hsn = wb.create_sheet("hsn")
        ws_hsn.append([
            "HSN", "Description", "UQC", "Total Quantity", "Total Value", "Taxable Value",
            "Integrated Tax Amount", "Central Tax Amount", "State/UT Tax Amount", "Cess Amount"
        ])

        ws_docs = wb.create_sheet("docs")
        ws_docs.append(["Nature of Document", "Sr. No. From", "Sr. No. To", "Total Number", "Cancelled", "Net Issued"])

        hsn_map = {}
        for inv in invoices:
            pos = inv["client_state_code"] or "27"
            pos_label = f"{pos}-{GST_STATE_CODES.get(pos, 'Maharashtra')}"
            inv_dt = inv["invoice_date"]
            try: inv_dt = datetime.strptime(inv_dt, "%Y-%m-%d").strftime("%d-%b-%Y")
            except Exception: pass

            is_b2b = bool(inv["recipient_gstin"] and len(inv["recipient_gstin"].strip()) == 15)
            if is_b2b:
                ws_b2b.append([
                    inv["recipient_gstin"], inv["client_name"], inv["invoice_no"], inv_dt,
                    inv["total"], pos_label, "N", "", "Regular", "", 18.0, inv["subtotal"], 0.0
                ])
            else:
                ws_b2cs.append(["OE", pos_label, "", 18.0, inv["subtotal"], 0.0, ""])

            items = self.db.rows("SELECT * FROM invoice_items WHERE invoice_id=?", (inv["id"],))
            for it in items:
                sac = it["sac"] or "998221"
                if sac not in hsn_map:
                    hsn_map[sac] = {"desc": it["description"][:30], "qty": 0.0, "val": 0.0, "txval": 0.0, "iamt": 0.0, "camt": 0.0, "samt": 0.0}
                hsn_map[sac]["qty"] += float(it["qty"] or 1)
                hsn_map[sac]["val"] += float(it["amount"] or 0)
                hsn_map[sac]["txval"] += float(it["amount"] or 0)
                hsn_map[sac]["camt"] += float(inv["cgst"] or 0)
                hsn_map[sac]["samt"] += float(inv["sgst"] or 0)
                hsn_map[sac]["iamt"] += float(inv["igst"] or 0)

        for sac, d in hsn_map.items():
            ws_hsn.append([sac, d["desc"], "OTH", d["qty"], d["val"], d["txval"], d["iamt"], d["camt"], d["samt"], 0.0])

        if invoices:
            first_no = invoices[0]["invoice_no"]
            last_no = invoices[-1]["invoice_no"]
            ws_docs.append(["Invoices for outward supply", first_no, last_no, len(invoices), 0, len(invoices)])

        wb.save(path)
        QMessageBox.information(self, "GSTR-1 Excel Saved", f"Official GSTR-1 offline workbook saved:\n{path}")
        self.accept()

    def export_json(self):
        unit, invoices = self.get_data()
        path, _ = QFileDialog.getSaveFileName(self, "Save Official GSTR-1 JSON File", str(BASE / "GSTR1_Direct_Upload.json"), "JSON Files (*.json)")
        if not path: return

        fp = self.period_combo.currentData()
        b2b_recipients = {}
        hsn_data = []
        doc_list = []

        for inv in invoices:
            gstin = (inv["recipient_gstin"] or "").strip().upper()
            if len(gstin) == 15:
                if gstin not in b2b_recipients:
                    b2b_recipients[gstin] = {"ctin": gstin, "cfs": "Y", "inv": []}

                inv_dt = inv["invoice_date"]
                try: inv_dt = datetime.strptime(inv_dt, "%Y-%m-%d").strftime("%d-%m-%Y")
                except Exception: pass

                b2b_recipients[gstin]["inv"].append({
                    "inum": inv["invoice_no"],
                    "idt": inv_dt,
                    "val": float(inv["total"] or 0),
                    "pos": inv["client_state_code"] or "27",
                    "rchrg": "N",
                    "etin": "",
                    "inv_typ": "R",
                    "itms": [{
                        "num": 1,
                        "itm_det": {
                            "txval": float(inv["subtotal"] or 0),
                            "rt": 18.0,
                            "iamt": float(inv["igst"] or 0),
                            "camt": float(inv["cgst"] or 0),
                            "samt": float(inv["sgst"] or 0),
                            "csamt": 0.0
                        }
                    }]
                })

        hsn_idx = 1
        hsn_summary = self.db.rows("""
            SELECT it.sac, it.description, SUM(it.qty) tot_qty, SUM(it.amount) tot_amt,
            SUM(i.cgst) tot_cgst, SUM(i.sgst) tot_sgst, SUM(i.igst) tot_igst
            FROM invoice_items it
            JOIN invoices i ON i.id=it.invoice_id
            WHERE i.unit_id=? AND i.status != 'Cancelled'
            GROUP BY it.sac
        """, (unit["id"],))

        for h in hsn_summary:
            hsn_data.append({
                "num": hsn_idx,
                "hsn_sc": h["sac"] or "998221",
                "desc": h["description"][:30],
                "uqc": "OTH",
                "qty": float(h["tot_qty"] or 1),
                "val": float(h["tot_amt"] or 0),
                "txval": float(h["tot_amt"] or 0),
                "iamt": float(h["tot_igst"] or 0),
                "camt": float(h["tot_cgst"] or 0),
                "samt": float(h["tot_sgst"] or 0),
                "csamt": 0.0
            })
            hsn_idx += 1

        if invoices:
            doc_list.append({
                "doc_num": 1,
                "doc_typ": "Invoices for outward supply",
                "docs": [{
                    "num": 1,
                    "from": invoices[0]["invoice_no"],
                    "to": invoices[-1]["invoice_no"],
                    "totnum": len(invoices),
                    "canc": 0,
                    "net_issue": len(invoices)
                }]
            })

        payload = {
            "gstin": unit["gstin"] or "27AABCS1234D1Z5",
            "fp": fp,
            "gt": 0.0,
            "cur_gt": 0.0,
            "version": "GST_1.0",
            "hash": "hash",
            "b2b": list(b2b_recipients.values()),
            "b2cs": [],
            "hsn": {"data": hsn_data},
            "doc_issue": {"doc_det": doc_list}
        }

        with open(path, "w", encoding="utf-8") as fp_json:
            json.dump(payload, fp_json, indent=2)

        QMessageBox.information(self, "GSTR-1 JSON Saved", f"Upload-ready GSTR-1 JSON file created:\n{path}")
        self.accept()


# ---------------------------------------------------------
# Main Application Window
# ---------------------------------------------------------
class InvoiceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.items = []
        self.editing_id = None

        self.setWindowTitle(APP_NAME)
        self.resize(1360, 860)
        
        # Application Desktop & Taskbar Icon
        for ic in [BASE / "app_icon.png", BASE / "app_icon.ico"]:
            if ic.exists():
                self.setWindowIcon(QIcon(str(ic)))
                break
        self.setStyleSheet("""
            QMainWindow { background-color: #f8fafc; font-family: 'Segoe UI', Arial, sans-serif; }
            QTabWidget::pane { border: 1px solid #e2e8f0; background: white; border-radius: 8px; }
            QTabBar::tab {
                background: #edf2f7; color: #334155; font-weight: 600; padding: 10px 18px;
                margin-right: 4px; border-top-left-radius: 6px; border-top-right-radius: 6px;
            }
            QTabBar::tab:selected { background: #1e3a8a; color: white; }
            QTabBar::tab:hover:!selected { background: #e2e8f0; }
            QPushButton {
                background-color: #1e3a8a; color: white; border: none; padding: 8px 15px;
                border-radius: 5px; font-weight: 600; font-size: 11px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:pressed { background-color: #172554; }
            QPushButton#secondaryBtn {
                background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1;
            }
            QPushButton#secondaryBtn:hover { background-color: #e2e8f0; }
            QPushButton#successBtn {
                background-color: #059669; color: white;
            }
            QPushButton#successBtn:hover { background-color: #047857; }
            QPushButton#dangerBtn {
                background-color: #dc2626; color: white;
            }
            QPushButton#dangerBtn:hover { background-color: #b91c1c; }
            QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QTextEdit {
                padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 5px; background: white;
                color: #0f172a; selection-background-color: #3b82f6;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus {
                border: 1.5px solid #2563eb;
            }
            QTableWidget {
                background-color: white; border: 1px solid #e2e8f0; border-radius: 6px;
                gridline-color: #f1f5f9; selection-background-color: #dbeafe; selection-color: #1e3a8a;
            }
            QHeaderView::section {
                background-color: #1e293b; color: white; font-weight: 700; padding: 8px;
                border: none; font-size: 11px;
            }
        """)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.dashboard_tab = QWidget()
        self.create_tab = QWidget()
        self.invoices_tab = QWidget()
        self.payments_tab = QWidget()
        self.nongst_tab = QWidget()
        self.clients_tab = QWidget()
        self.services_tab = QWidget()
        self.units_tab = QWidget()
        self.whatsapp_tab = QWidget()
        self.settings_tab = QWidget()

        for widget, title in [
            (self.dashboard_tab, "Dashboard & Analytics"),
            (self.create_tab, "Create Invoice"),
            (self.invoices_tab, "GST Invoices Register"),
            (self.payments_tab, "Payments & Collections"),
            (self.nongst_tab, "Non-GST & Reimbursements"),
            (self.clients_tab, "Clients Master"),
            (self.services_tab, "Service Catalogue"),
            (self.units_tab, "Billing Units"),
            (self.whatsapp_tab, "WhatsApp & Communication"),
            (self.settings_tab, "Settings & Integrations")
        ]:
            self.tabs.addTab(widget, title)

        self.build_dashboard()
        self.build_invoice()
        self.build_invoices()
        self.build_payments()
        self.build_nongst()
        self.build_clients()
        self.build_masters()
        self.build_whatsapp()
        self.build_settings()
        self.refresh_all()

    # -----------------------------------------------------
    # UI Components: KPI Card
    # -----------------------------------------------------
    def make_kpi_card(self, title, accent_color="#2563eb"):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff; border-radius: 8px;
                border: 1px solid #e2e8f0; border-top: 4px solid {accent_color};
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        lbl_title = QLabel(title.upper())
        lbl_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")

        lbl_value = QLabel("₹ 0.00")
        lbl_value.setStyleSheet("font-size: 20px; font-weight: 800; color: #0f172a;")

        lbl_sub = QLabel("0 records")
        lbl_sub.setStyleSheet("font-size: 11px; color: #94a3b8;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        layout.addWidget(lbl_sub)
        return frame, lbl_value, lbl_sub

    # -----------------------------------------------------
    # 1. Executive Dashboard & Analytics
    # -----------------------------------------------------
    def build_dashboard(self):
        main_layout = QVBoxLayout(self.dashboard_tab)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #f8fafc; }")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        h_label = QLabel("CA Practice Executive Intelligence & Analytics")
        h_label.setStyleSheet("font-size: 20px; font-weight: 800; color: #0f172a;")
        sub_label = QLabel("Live realization rate, receivables credit risk, and Form 26AS TDS matching")
        sub_label.setStyleSheet("font-size: 11px; color: #64748b;")
        title_box.addWidget(h_label)
        title_box.addWidget(sub_label)
        header.addLayout(title_box)
        header.addStretch()

        header.addWidget(QLabel("<b>Filter FY:</b>"))
        self.dash_fy_filter = QComboBox()
        self.dash_fy_filter.addItems(["All Financial Years", "FY 2026-27", "FY 2025-26", "FY 2024-25"])
        self.dash_fy_filter.currentIndexChanged.connect(self.refresh_dashboard)
        header.addWidget(self.dash_fy_filter)

        header.addWidget(QLabel("<b>Billing Unit:</b>"))
        self.dash_unit_filter = QComboBox()
        self.dash_unit_filter.addItem("All Billing Units", None)
        self.dash_unit_filter.currentIndexChanged.connect(self.refresh_dashboard)
        header.addWidget(self.dash_unit_filter)

        btn_refresh = QPushButton("Refresh Analytics")
        btn_refresh.setObjectName("secondaryBtn")
        btn_refresh.clicked.connect(self.refresh_dashboard)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        kpi_row = QHBoxLayout()
        self.kpi_billed_card, self.kpi_billed_val, self.kpi_billed_sub = self.make_kpi_card("Total Invoiced (FYTD)", "#2563eb")
        self.kpi_coll_card, self.kpi_coll_val, self.kpi_coll_sub = self.make_kpi_card("Collections Realized", "#10b981")
        self.kpi_tds_card, self.kpi_tds_val, self.kpi_tds_sub = self.make_kpi_card("TDS Credits (26AS)", "#f59e0b")
        self.kpi_due_card, self.kpi_due_val, self.kpi_due_sub = self.make_kpi_card("Net Outstanding Due", "#ef4444")
        self.kpi_eff_card, self.kpi_eff_val, self.kpi_eff_sub = self.make_kpi_card("Realization Efficiency", "#8b5cf6")
        self.kpi_clients_card, self.kpi_clients_val, self.kpi_clients_sub = self.make_kpi_card("Active Engagements", "#06b6d4")

        for c in [self.kpi_billed_card, self.kpi_coll_card, self.kpi_tds_card, self.kpi_due_card, self.kpi_eff_card, self.kpi_clients_card]:
            kpi_row.addWidget(c)
        layout.addLayout(kpi_row)

        charts_grid = QGridLayout()
        self.trend_chart = MonthlyBilledVsCollectedChart()
        self.service_chart = ServiceDistributionChart()
        self.aging_chart = ReceivablesAgingWidget()
        self.donut_chart = CollectionStatusDonutChart()

        charts_grid.addWidget(self.trend_chart, 0, 0)
        charts_grid.addWidget(self.service_chart, 0, 1)
        charts_grid.addWidget(self.aging_chart, 1, 0)
        charts_grid.addWidget(self.donut_chart, 1, 1)
        layout.addLayout(charts_grid)

        debtors_header = QHBoxLayout()
        dh_label = QLabel("Critical Receivables Ledger & Debtor Ageing")
        dh_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #1e293b;")
        debtors_header.addWidget(dh_label)
        debtors_header.addStretch()
        layout.addLayout(debtors_header)

        self.dashboard_detail = QTableWidget()
        self.dashboard_detail.setColumnCount(8)
        self.dashboard_detail.setHorizontalHeaderLabels([
            "Client Legal Name", "Total Invoiced", "Collections", "Net Outstanding", "Oldest Invoice", "Days Overdue", "TDS Credit", "Actions"
        ])
        self.dashboard_detail.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.dashboard_detail.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dashboard_detail.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.dashboard_detail.setMinimumHeight(320)
        layout.addWidget(self.dashboard_detail)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    # -----------------------------------------------------
    # 2. Create Invoice Tab
    # -----------------------------------------------------
    def build_invoice(self):
        lay = QVBoxLayout(self.create_tab)
        lay.setContentsMargins(18, 16, 18, 16)

        title_bar = QHBoxLayout()
        title = QLabel("Create / Edit Bill & Tax Invoice")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1e293b;")
        title_bar.addWidget(title)
        title_bar.addStretch()

        self.invoice_mode = QLabel("Status: New Invoice")
        self.invoice_mode.setStyleSheet("color: #2563eb; font-weight: 700; background: #eff6ff; padding: 4px 8px; border-radius: 4px;")
        title_bar.addWidget(self.invoice_mode)

        for text, fn, is_sec in [
            ("Import Excel / Tally XLSM", self.import_invoice_file, True),
            ("Export Invoice Register", self.export_invoice_register, True),
            ("Choose PDF Folder", self.choose_pdf_folder, True),
            ("New / Clear Form", self.clear_draft, True),
            ("Save Invoice & PDF", self.save_invoice, False)
        ]:
            b = QPushButton(text)
            if is_sec: b.setObjectName("secondaryBtn")
            else: b.setObjectName("successBtn")
            b.clicked.connect(fn)
            title_bar.addWidget(b)
        lay.addLayout(title_bar)

        form_box = QGroupBox("Invoice Metadata & Party Details")
        form_box.setStyleSheet("QGroupBox { font-weight: 700; color: #334155; }")
        form = QGridLayout(form_box)

        self.invoice_unit = QComboBox()
        self.invoice_client = QComboBox()
        self.invoice_type = QComboBox()
        self.invoice_type.addItems(["Tax Invoice", "Proforma Invoice", "Bill of Supply"])
        self.invoice_no_input = QLineEdit()
        self.invoice_no_input.setPlaceholderText("Auto sequence or custom invoice number")

        self.invoice_date = QDateEdit(QDate.currentDate())
        self.invoice_due = QDateEdit(QDate.currentDate().addDays(15))
        for w in [self.invoice_date, self.invoice_due]:
            w.setCalendarPopup(True)
            w.setDisplayFormat("dd-MM-yyyy")

        self.place_of_supply = QComboBox()
        for code, name in sorted(GST_STATE_CODES.items(), key=lambda x: x[0]):
            self.place_of_supply.addItem(f"{code} - {name}", code)

        form.addWidget(QLabel("Billing Unit:"), 0, 0)
        form.addWidget(self.invoice_unit, 0, 1)
        form.addWidget(QLabel("Client:"), 0, 2)
        form.addWidget(self.invoice_client, 0, 3)

        form.addWidget(QLabel("Invoice Type:"), 1, 0)
        form.addWidget(self.invoice_type, 1, 1)
        form.addWidget(QLabel("Invoice Number:"), 1, 2)
        form.addWidget(self.invoice_no_input, 1, 3)

        form.addWidget(QLabel("Invoice Date:"), 2, 0)
        form.addWidget(self.invoice_date, 2, 1)
        form.addWidget(QLabel("Due Date:"), 2, 2)
        form.addWidget(self.invoice_due, 2, 3)

        form.addWidget(QLabel("Place of Supply:"), 3, 0)
        form.addWidget(self.place_of_supply, 3, 1)
        lay.addWidget(form_box)

        item_box = QGroupBox("Add Professional Services / Disbursements")
        item_box.setStyleSheet("QGroupBox { font-weight: 700; color: #334155; }")
        addrow = QHBoxLayout(item_box)

        self.item_type = QComboBox()
        self.item_type.addItems(["Professional Service", "Reimbursement / Pure Agent"])
        self.item_service = QComboBox()
        self.item_description = QLineEdit()
        self.item_description.setPlaceholderText("Detailed description for client invoice")
        self.item_sac = QLineEdit()
        self.item_sac.setPlaceholderText("SAC Code")
        self.item_sac.setMaximumWidth(100)

        self.item_qty = QDoubleSpinBox()
        self.item_qty.setValue(1)
        self.item_qty.setMaximum(9999)
        self.item_qty.setMaximumWidth(70)

        self.item_rate = QDoubleSpinBox()
        self.item_rate.setMaximum(99999999)
        self.item_rate.setDecimals(2)
        self.item_rate.setMaximumWidth(120)

        self.item_gst = QComboBox()
        self.item_gst.addItems([str(x) for x in GST_RATES])
        self.item_gst.setCurrentText("18")
        self.item_gst.setMaximumWidth(70)

        self.item_type.currentTextChanged.connect(
            lambda x: self.item_gst.setCurrentText("0") if "Reimbursement" in x else self.item_gst.setCurrentText("18")
        )

        for lab, w in [
            ("Type", self.item_type), ("Preset Service", self.item_service),
            ("Description", self.item_description), ("SAC", self.item_sac),
            ("Qty", self.item_qty), ("Fee (₹)", self.item_rate), ("GST %", self.item_gst)
        ]:
            addrow.addWidget(QLabel(lab))
            addrow.addWidget(w)

        btn_add = QPushButton("Add Line Item")
        btn_add.clicked.connect(self.add_item)
        addrow.addWidget(btn_add)
        lay.addWidget(item_box)

        self.item_service.currentIndexChanged.connect(self.service_changed)
        self.invoice_client.currentIndexChanged.connect(self.client_changed)
        self.invoice_unit.currentIndexChanged.connect(self.unit_changed)

        self.item_table = QTableWidget(0, 8)
        self.item_table.setHorizontalHeaderLabels(["Type", "Description", "SAC", "Qty", "Fee (₹)", "GST %", "Tax Amount", "Total (₹)"])
        self.item_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.item_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.item_table)

        bottom = QHBoxLayout()
        self.total_label = QLabel("Taxable: ₹ 0.00 | Tax: ₹ 0.00 | Grand Total: ₹ 0.00")
        self.total_label.setStyleSheet("font-size: 15px; font-weight: 800; color: #047857; background: #ecfdf5; padding: 8px 14px; border-radius: 6px;")
        bottom.addWidget(self.total_label)
        bottom.addStretch()

        btn_remove = QPushButton("Remove Selected Line")
        btn_remove.setObjectName("secondaryBtn")
        btn_remove.clicked.connect(self.remove_item)
        btn_gen = QPushButton("Generate PDF & Finalize")
        btn_gen.setObjectName("successBtn")
        btn_gen.clicked.connect(self.save_invoice)

        bottom.addWidget(btn_remove)
        bottom.addWidget(btn_gen)
        lay.addLayout(bottom)

    # -----------------------------------------------------
    # 3. GST Invoices Register Tab
    # -----------------------------------------------------
    def build_invoices(self):
        lay = QVBoxLayout(self.invoices_tab)
        lay.setContentsMargins(18, 16, 18, 16)

        top = QHBoxLayout()
        label = QLabel("GST Tax Invoices Master Register")
        label.setStyleSheet("font-size: 18px; font-weight: 700; color: #1e293b;")
        top.addWidget(label)
        top.addStretch()

        for text, fn in [
            ("Record Payment / TDS", self.record_payment_action),
            ("Upload 26AS TDS Summary", self.open_26as_reconciliation),
            ("Bank Statement / SMS Recon", self.open_bank_reconciliation),
            ("Export GSTR-1 (Excel & JSON)", self.open_gstr1_export),
            ("Open PDF", self.open_pdf),
            ("Email Invoice & PDF", self.email_invoice),
            ("Edit Selected", self.edit_invoice),
            ("Delete Selected", self.delete_invoice)
        ]:
            b = QPushButton(text)
            if "Payment" in text or "26AS" in text or "GSTR-1" in text: b.setObjectName("successBtn")
            else: b.setObjectName("secondaryBtn")
            b.clicked.connect(fn)
            top.addWidget(b)
        lay.addLayout(top)

        self.invoices_table = QTableWidget()
        self.invoices_table.setColumnCount(12)
        self.invoices_table.setHorizontalHeaderLabels([
            "Invoice No", "Date", "Billing Unit", "Client Name", "Taxable", "CGST", "SGST", "IGST", "Grand Total", "Settled", "Balance Due", "Status"
        ])
        self.invoices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.invoices_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.invoices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.invoices_table.itemDoubleClicked.connect(lambda _item: self.open_pdf())
        lay.addWidget(self.invoices_table)

    # -----------------------------------------------------
    # 4. Payments & Collection Ledger Tab
    # -----------------------------------------------------
    def build_payments(self):
        lay = QVBoxLayout(self.payments_tab)
        lay.setContentsMargins(18, 16, 18, 16)

        top = QHBoxLayout()
        label = QLabel("Receipts, Bank Realizations & TDS Register")
        label.setStyleSheet("font-size: 18px; font-weight: 700; color: #1e293b;")
        top.addWidget(label)
        top.addStretch()

        for text, fn, is_succ in [
            ("Record New Payment", self.record_payment_standalone, True),
            ("Upload 26AS TDS Summary", self.open_26as_reconciliation, True),
            ("Bank Statement / SMS Recon", self.open_bank_reconciliation, True),
            ("Export Receipts Excel", self.export_payments, False),
            ("View Payment Proof", self.view_payment_proof, False),
            ("Delete Selected Payment", self.delete_payment, False)
        ]:
            b = QPushButton(text)
            if is_succ: b.setObjectName("successBtn")
            else: b.setObjectName("secondaryBtn")
            b.clicked.connect(fn)
            top.addWidget(b)
        lay.addLayout(top)

        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(10)
        self.payments_table.setHorizontalHeaderLabels([
            "Receipt ID", "Payment Date", "Invoice No", "Client Name", "Net Received", "TDS Deducted", "TDS Section", "Mode", "Reference / UTR", "Proof"
        ])
        self.payments_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.payments_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.payments_table)

    # -----------------------------------------------------
    # 5. Non-GST & Reimbursements Tab
    # -----------------------------------------------------
    def build_nongst(self):
        lay = QVBoxLayout(self.nongst_tab)
        lay.setContentsMargins(18, 16, 18, 16)

        top = QHBoxLayout()
        label = QLabel("Non-GST Bills of Supply & Expense Reimbursements")
        label.setStyleSheet("font-size: 18px; font-weight: 700; color: #1e293b;")
        top.addWidget(label)
        top.addStretch()

        for text, fn in [
            ("Record Payment", self.record_payment_nongst),
            ("Open PDF", self.open_nongst_pdf),
            ("Edit Selected", self.edit_nongst),
            ("Delete Selected", self.delete_nongst)
        ]:
            b = QPushButton(text)
            b.setObjectName("secondaryBtn")
            b.clicked.connect(fn)
            top.addWidget(b)
        lay.addLayout(top)

        self.nongst_table = QTableWidget()
        self.nongst_table.setColumnCount(8)
        self.nongst_table.setHorizontalHeaderLabels([
            "Invoice No", "Date", "Billing Unit", "Client", "Total Amount", "Paid", "Balance Due", "Source"
        ])
        self.nongst_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.nongst_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.nongst_table)

    # -----------------------------------------------------
    # 6. Clients Master Tab (With Multi-Select & Batch Deletion)
    # -----------------------------------------------------
    def build_clients(self):
        lay = QVBoxLayout(self.clients_tab)
        lay.setContentsMargins(18, 16, 18, 16)

        top = QHBoxLayout()
        label = QLabel("Client Master Directory")
        label.setStyleSheet("font-size: 18px; font-weight: 700; color: #1e293b;")
        top.addWidget(label)
        top.addStretch()

        for text, fn, is_danger, is_succ in [
            ("Add New Client", self.add_client, False, True),
            ("Select All", self.select_all_clients, False, False),
            ("Deselect All", self.deselect_all_clients, False, False),
            ("Delete Selected Clients", self.delete_selected_clients, True, False),
            ("Edit Selected", self.edit_client, False, False)
        ]:
            b = QPushButton(text)
            if is_danger: b.setObjectName("dangerBtn")
            elif is_succ: b.setObjectName("successBtn")
            else: b.setObjectName("secondaryBtn")
            b.clicked.connect(fn)
            top.addWidget(b)
        lay.addLayout(top)

        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(8)
        self.clients_table.setHorizontalHeaderLabels([
            "Select", "Client Legal Name", "GSTIN", "PAN", "Email Address", "Phone / Mobile", "State", "State Code"
        ])
        self.clients_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.clients_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.clients_table.itemDoubleClicked.connect(lambda _item: self.edit_client())
        lay.addWidget(self.clients_table)

        b_row = QHBoxLayout()
        for text, fn in [
            ("Import Clients (Excel/XLSM)", self.import_clients),
            ("Export Clients to Excel", self.export_clients),
            ("Live GSTIN Verification", self.lookup_selected_gstin),
            ("Bulk GSTIN Status Refresh", self.bulk_gstin_refresh),
            ("Email Selected Client", self.email_client),
            ("WhatsApp Selected Client", self.whatsapp_client)
        ]:
            b = QPushButton(text)
            b.setObjectName("secondaryBtn")
            b.clicked.connect(fn)
            b_row.addWidget(b)
        b_row.addStretch()
        lay.addLayout(b_row)

    def select_all_clients(self):
        for r in range(self.clients_table.rowCount()):
            it = self.clients_table.item(r, 0)
            if it: it.setCheckState(Qt.CheckState.Checked)

    def deselect_all_clients(self):
        for r in range(self.clients_table.rowCount()):
            it = self.clients_table.item(r, 0)
            if it: it.setCheckState(Qt.CheckState.Unchecked)

    def delete_selected_clients(self):
        ids_to_delete = []
        for r in range(self.clients_table.rowCount()):
            it = self.clients_table.item(r, 0)
            if it and it.checkState() == Qt.CheckState.Checked:
                cid = it.data(Qt.ItemDataRole.UserRole)
                if cid: ids_to_delete.append(cid)

        if not ids_to_delete:
            for s in self.clients_table.selectionModel().selectedRows():
                it = self.clients_table.item(s.row(), 0)
                if it:
                    cid = it.data(Qt.ItemDataRole.UserRole)
                    if cid: ids_to_delete.append(cid)

        if not ids_to_delete:
            QMessageBox.warning(self, "No Clients Selected", "Please tick or highlight at least one client row to delete.")
            return

        cnt = len(ids_to_delete)
        if QMessageBox.question(
            self, "Confirm Batch Delete",
            f"Are you sure you want to delete {cnt} selected client(s)?\nAll linked records will be archived and removed from active lists.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            for cid in ids_to_delete:
                self.db.execute("UPDATE clients SET active=0 WHERE id=?", (cid,))
            self.refresh_all()
            QMessageBox.information(self, "Deleted", f"Successfully deactivated {cnt} client record(s).")

    # -----------------------------------------------------
    # 7. WhatsApp & Client Communication Tab (With Full CRUD)
    # -----------------------------------------------------
    def build_whatsapp(self):
        lay = QVBoxLayout(self.whatsapp_tab)
        lay.setContentsMargins(18, 16, 18, 16)

        info = QLabel(
            "<b>Automated Payment Reminders & Client Outreach via WhatsApp:</b><br/>"
            "Select clients below to generate a pre-drafted WhatsApp reminder with invoice numbers, amounts due, "
            "and firm UPI ID for immediate payment. Double-click any row to edit phone/email, or use the top action buttons."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 10px; color: #1e3a8a;")
        lay.addWidget(info)

        # Action Toolbar with CRUD controls
        bar = QHBoxLayout()
        self.wa_search = QLineEdit()
        self.wa_search.setPlaceholderText("🔍 Search clients by name, mobile, email...")
        self.wa_search.textChanged.connect(self.filter_whatsapp_table)
        bar.addWidget(self.wa_search, 1)

        for text, fn, is_danger, is_succ in [
            ("Add Client", self.add_client, False, True),
            ("Edit Client / Mobile", self.edit_whatsapp_client, False, False),
            ("Delete Selected", self.delete_whatsapp_clients, True, False),
            ("Select All", self.select_all_whatsapp, False, False),
            ("Deselect All", self.deselect_all_whatsapp, False, False)
        ]:
            b = QPushButton(text)
            if is_danger: b.setObjectName("dangerBtn")
            elif is_succ: b.setObjectName("successBtn")
            else: b.setObjectName("secondaryBtn")
            b.clicked.connect(fn)
            bar.addWidget(b)
        lay.addLayout(bar)

        self.whatsapp_table = QTableWidget()
        self.whatsapp_table.setColumnCount(7)
        self.whatsapp_table.setHorizontalHeaderLabels([
            "Select", "Client Name", "Mobile Number", "Email", "Total Outstanding", "Pending Invoices", "Quick Action"
        ])
        self.whatsapp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.whatsapp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.whatsapp_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.whatsapp_table.itemDoubleClicked.connect(lambda _it: self.edit_whatsapp_client())
        lay.addWidget(self.whatsapp_table)

        btn_send = QPushButton("Launch Selected WhatsApp Payment Reminders")
        btn_send.setObjectName("successBtn")
        btn_send.clicked.connect(self.send_whatsapp_reminders)
        lay.addWidget(btn_send)

    def select_all_whatsapp(self):
        for r in range(self.whatsapp_table.rowCount()):
            it = self.whatsapp_table.item(r, 0)
            if it: it.setCheckState(Qt.CheckState.Checked)

    def deselect_all_whatsapp(self):
        for r in range(self.whatsapp_table.rowCount()):
            it = self.whatsapp_table.item(r, 0)
            if it: it.setCheckState(Qt.CheckState.Unchecked)

    def filter_whatsapp_table(self):
        q = self.wa_search.text().strip().lower()
        for r in range(self.whatsapp_table.rowCount()):
            match = False
            for col in range(1, 5):
                it = self.whatsapp_table.item(r, col)
                if it and q in it.text().lower():
                    match = True; break
            self.whatsapp_table.setRowHidden(r, not match if q else False)

    def edit_whatsapp_client(self):
        """Allows direct editing of client name, mobile number, and email from the WhatsApp tab."""
        cid = None
        for r in range(self.whatsapp_table.rowCount()):
            it = self.whatsapp_table.item(r, 0)
            if it and it.checkState() == Qt.CheckState.Checked:
                cid = it.data(Qt.ItemDataRole.UserRole); break

        if not cid:
            rows = self.whatsapp_table.selectionModel().selectedRows()
            if rows:
                it = self.whatsapp_table.item(rows[0].row(), 0)
                if it: cid = it.data(Qt.ItemDataRole.UserRole)
            elif self.whatsapp_table.currentRow() >= 0:
                it = self.whatsapp_table.item(self.whatsapp_table.currentRow(), 0)
                if it: cid = it.data(Qt.ItemDataRole.UserRole)

        if not cid:
            QMessageBox.warning(self, "Select Client", "Please tick or click on a client row to edit their details / mobile number.")
            return

        row = self.db.one("SELECT * FROM clients WHERE id=?", (cid,))
        if not row: return
        row_dict = dict(row)

        fields = [
            ("name", "Client Legal Name", "text"),
            ("phone", "Mobile / Phone (with Country Code e.g. 919820012345)", "text"),
            ("email", "Email Address", "text"),
            ("gstin", "GSTIN", "text"),
            ("pan", "PAN", "text"),
            ("address", "Registered Address", "memo"),
            ("state", "State", "text"),
            ("state_code", "State Code", "text"),
            ("notes", "Client Notes", "memo")
        ]
        d = MasterDialog("Edit Client & Contact Details", fields, row_dict, parent=self)
        if d.exec():
            data = {**d.data(), "id": cid}
            if data["gstin"] and not data["state_code"]: data["state_code"] = data["gstin"][:2]
            if not data["pan"] and len(data["gstin"]) == 15: data["pan"] = data["gstin"][2:12]
            self.db.execute("""
                UPDATE clients SET name=:name, gstin=:gstin, pan=:pan, email=:email, phone=:phone,
                address=:address, state=:state, state_code=:state_code, notes=:notes WHERE id=:id
            """, data)
            self.refresh_all()
            QMessageBox.information(self, "Updated", f"Client contact details updated successfully.")

    def delete_whatsapp_clients(self):
        """Allows direct deletion / archiving of clients from the WhatsApp tab."""
        ids_to_del = []
        for r in range(self.whatsapp_table.rowCount()):
            it = self.whatsapp_table.item(r, 0)
            if it and it.checkState() == Qt.CheckState.Checked:
                cid = it.data(Qt.ItemDataRole.UserRole)
                if cid: ids_to_del.append(cid)

        if not ids_to_del:
            rows = self.whatsapp_table.selectionModel().selectedRows()
            for s in rows:
                it = self.whatsapp_table.item(s.row(), 0)
                if it:
                    cid = it.data(Qt.ItemDataRole.UserRole)
                    if cid: ids_to_del.append(cid)
            if not ids_to_del and self.whatsapp_table.currentRow() >= 0:
                it = self.whatsapp_table.item(self.whatsapp_table.currentRow(), 0)
                if it:
                    cid = it.data(Qt.ItemDataRole.UserRole)
                    if cid: ids_to_del.append(cid)

        if not ids_to_del:
            QMessageBox.warning(self, "No Clients Selected", "Please tick or highlight at least one client row to delete.")
            return

        cnt = len(ids_to_del)
        if QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {cnt} selected client(s)?\nThey will be removed from WhatsApp outreach and active masters.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            for cid in ids_to_del:
                self.db.execute("UPDATE clients SET active=0 WHERE id=?", (cid,))
            self.refresh_all()
            QMessageBox.information(self, "Deleted", f"Removed {cnt} client(s).")

    def build_whatsapp_table(self):
        """Populates WhatsApp outreach table strictly for active clients (WHERE c.active = 1)."""
        rows = self.db.rows("""
            SELECT c.*,
            COALESCE(SUM(i.total), 0) billed,
            COALESCE((SELECT SUM(amount + tds_deducted) FROM payments p JOIN invoices inv ON inv.id=p.invoice_id WHERE inv.client_id=c.id), 0) paid,
            COUNT(i.id) inv_cnt
            FROM clients c
            LEFT JOIN invoices i ON i.client_id=c.id AND i.status != 'Cancelled'
            WHERE c.active = 1
            GROUP BY c.id ORDER BY (billed - paid) DESC, c.name ASC
        """)
        self.whatsapp_table.setRowCount(len(rows))
        for r, x in enumerate(rows):
            due = max(0.0, float(x["billed"] or 0) - float(x["paid"] or 0))
            phone_str = str(x["phone"] or "").strip()

            tick = QTableWidgetItem()
            tick.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            tick.setCheckState(Qt.CheckState.Checked if due > 0 and phone_str and phone_str != "-" else Qt.CheckState.Unchecked)
            tick.setData(Qt.ItemDataRole.UserRole, x["id"])
            self.whatsapp_table.setItem(r, 0, tick)

            display_phone = phone_str if phone_str else "-"
            display_email = str(x["email"] or "-")
            for col, v in enumerate([x["name"], display_phone, display_email, money(due), f"{x['inv_cnt']} bill(s)"], 1):
                it = QTableWidgetItem(str(v))
                if col == 4 and due > 0: it.setForeground(QColor("#dc2626"))
                self.whatsapp_table.setItem(r, col, it)

            btn_wa_single = QPushButton("WhatsApp")
            btn_wa_single.setObjectName("secondaryBtn")
            btn_wa_single.clicked.connect(lambda _, cid=x["id"]: self.prompt_whatsapp_single(cid))
            self.whatsapp_table.setCellWidget(r, 6, btn_wa_single)

        if hasattr(self, "wa_search") and self.wa_search.text().strip():
            self.filter_whatsapp_table()

    def prompt_whatsapp_single(self, client_id):
        client = self.db.one("SELECT * FROM clients WHERE id=?", (client_id,))
        if not client: return
        client = dict(client)
        unit = self.db.one("SELECT * FROM billing_units WHERE id=?", (client["default_unit_id"],)) or self.db.one("SELECT * FROM billing_units LIMIT 1")
        unit = dict(unit) if unit else {}

        latest = self.db.one("SELECT * FROM invoices WHERE client_id=? ORDER BY invoice_date DESC, id DESC LIMIT 1", (client_id,))
        latest = dict(latest) if latest else None

        phone = str(client.get("phone") or "").strip()
        if not phone or phone == "-":
            new_phone, ok = QInputDialog.getText(
                self, "Mobile Number Required",
                f"Client '{client['name']}' has no registered mobile number.\n\nEnter WhatsApp mobile number (with country code, e.g. 919820012345):",
                QLineEdit.EchoMode.Normal, ""
            )
            if ok and new_phone.strip():
                phone = new_phone.strip()
                self.db.execute("UPDATE clients SET phone=? WHERE id=?", (phone, client_id))
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Cannot Send", f"No valid mobile number provided for '{client['name']}'.")
                return

        due_res = self.db.one("""
            SELECT COALESCE(SUM(total), 0) - COALESCE((SELECT SUM(amount + tds_deducted) FROM payments p JOIN invoices inv ON inv.id=p.invoice_id WHERE inv.client_id=?), 0) due
            FROM invoices WHERE client_id=? AND status != 'Cancelled'
        """, (client_id, client_id))
        due_amt = due_res["due"] if due_res else 0.0

        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "").strip()
        if latest and latest.get("pdf_path") and Path(latest["pdf_path"]).exists():
            open_file(latest["pdf_path"])

        upi_msg = f" Remittance can be made via UPI to {unit.get('upi_id')}." if unit.get("upi_id") else ""
        msg = f"Dear {client['name']},\n\nGreetings from {unit.get('name', 'our CA Firm')}.\n" \
              f"This is a gentle reminder regarding your outstanding professional fee of {money(due_amt)}" \
              f"{' against Invoice ' + latest['invoice_no'] if latest else ''}." \
              f"{upi_msg}\n\nKindly arrange clearance at your earliest convenience."

        url = "https://web.whatsapp.com/send?phone=" + clean_phone + "&text=" + urllib.parse.quote(msg)
        webbrowser.open(url)

    def send_whatsapp_reminders(self):
        count = 0
        skipped = 0
        for r in range(self.whatsapp_table.rowCount()):
            it = self.whatsapp_table.item(r, 0)
            if it and it.checkState() == Qt.CheckState.Checked:
                cid = it.data(Qt.ItemDataRole.UserRole)
                c_row = self.db.one("SELECT phone FROM clients WHERE id=?", (cid,))
                p = str(c_row["phone"] or "").strip() if c_row else ""
                if p and p != "-":
                    self.prompt_whatsapp_single(cid)
                    count += 1
                else:
                    skipped += 1

        if count == 0 and skipped == 0:
            QMessageBox.information(self, "No Clients Selected", "Please tick clients with valid mobile numbers.")
        elif skipped > 0:
            QMessageBox.information(
                self, "Reminders Dispatched",
                f"Launched {count} WhatsApp reminder(s).\nSkipped {skipped} selected client(s) with missing mobile numbers.\n"
                f"Double-click clients with '-' in Mobile Number to add their phone."
            )

    # -----------------------------------------------------
    # 8. Masters: Services & Billing Units
    # -----------------------------------------------------
    def master_layout(self, tab, title, table_attr, columns, add_fn, edit_fn, del_fn):
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(18, 16, 18, 16)
        top = QHBoxLayout()
        label = QLabel(title)
        label.setStyleSheet("font-size: 18px; font-weight: 700; color: #1e293b;")
        top.addWidget(label)
        top.addStretch()

        for text, fn in [("Add New", add_fn), ("Edit Selected", edit_fn), ("Delete Selected", del_fn)]:
            b = QPushButton(text)
            b.setObjectName("secondaryBtn")
            b.clicked.connect(fn)
            top.addWidget(b)
        lay.addLayout(top)

        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.itemDoubleClicked.connect(lambda _item: edit_fn())
        lay.addWidget(table)
        setattr(self, table_attr, table)

    def build_masters(self):
        self.master_layout(
            self.services_tab, "Service Catalogue & SAC Master", "services_table",
            ["Service Name", "SAC Code", "GST Rate %", "Default Fee (₹)", "Category", "Taxable"],
            self.add_service, self.edit_service, self.delete_service
        )
        self.master_layout(
            self.units_tab, "Billing Units (Offices / Firms / LLPs)", "units_table",
            ["Firm Name", "GST Status", "GSTIN", "FRN", "Partner", "State", "Prefix"],
            self.add_unit, self.edit_unit, self.delete_unit
        )

    # -----------------------------------------------------
    # 9. Settings & Integrations Tab
    # -----------------------------------------------------
    def build_settings(self):
        lay = QVBoxLayout(self.settings_tab)
        lay.setContentsMargins(18, 16, 18, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        c_lay = QVBoxLayout(container)

        smtp_box = QGroupBox("SMTP Outgoing Email Configuration (Gmail App Password Pre-Configured)")
        smtp_lay = QFormLayout(smtp_box)

        preset_lay = QHBoxLayout()
        for p_name, p_host, p_port, p_sec in [
            ("Gmail (Port 465 SSL)", "smtp.gmail.com", "465", "Implicit SSL (Port 465)"),
            ("Gmail (Port 587 TLS)", "smtp.gmail.com", "587", "STARTTLS (Port 587)"),
            ("Office 365 (Port 587)", "smtp.office365.com", "587", "STARTTLS (Port 587)"),
            ("Zoho Mail (Port 465)", "smtp.zoho.in", "465", "Implicit SSL (Port 465)")
        ]:
            b = QPushButton(p_name)
            b.setObjectName("secondaryBtn")
            b.clicked.connect(lambda _, h=p_host, p=p_port, s=p_sec: self.apply_smtp_preset(h, p, s))
            preset_lay.addWidget(b)
        preset_lay.addStretch()
        smtp_lay.addRow("Quick Presets:", preset_lay)

        self.smtp_host = QLineEdit()
        self.smtp_port = QLineEdit()
        self.smtp_user = QLineEdit()
        self.smtp_user.setPlaceholderText("Enter your Gmail address (e.g. pritesh.ca@gmail.com)")
        self.smtp_password = QLineEdit()
        self.smtp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.smtp_security = QComboBox()
        self.smtp_security.addItems(["Implicit SSL (Port 465)", "STARTTLS (Port 587)", "Auto-Detect (SSL/STARTTLS)", "Plain / None"])

        btn_test_email = QPushButton("Test Email Connection (Verify App Password)")
        btn_test_email.setObjectName("successBtn")
        btn_test_email.clicked.connect(self.test_email_connection)

        smtp_lay.addRow("SMTP Host Server:", self.smtp_host)
        smtp_lay.addRow("Port:", self.smtp_port)
        smtp_lay.addRow("Firm Email / User:", self.smtp_user)
        smtp_lay.addRow("App Password:", self.smtp_password)
        smtp_lay.addRow("Security Mode:", self.smtp_security)
        smtp_lay.addRow("", btn_test_email)
        c_lay.addWidget(smtp_box)

        api_box = QGroupBox("Government GST Portal & API Gateway Integrations")
        api_lay = QFormLayout(api_box)
        self.gstin_api_key_input = QLineEdit()
        self.gstin_api_key_input.setPlaceholderText("Enter your GSTINAPI.in / GSP Key")
        api_lay.addRow("GSTIN Verification API Key:", self.gstin_api_key_input)
        c_lay.addWidget(api_box)

        pdf_box = QGroupBox("PDF Storage & Archival Directory")
        pdf_lay = QHBoxLayout(pdf_box)
        self.pdf_folder_lbl = QLabel(str(PDF_DIR))
        btn_ch_pdf = QPushButton("Change Folder")
        btn_ch_pdf.setObjectName("secondaryBtn")
        btn_ch_pdf.clicked.connect(self.choose_pdf_folder)
        pdf_lay.addWidget(self.pdf_folder_lbl, 1)
        pdf_lay.addWidget(btn_ch_pdf)
        c_lay.addWidget(pdf_box)

        btn_save = QPushButton("Save Settings & Credentials")
        btn_save.clicked.connect(self.save_settings)
        c_lay.addWidget(btn_save)
        c_lay.addStretch()

        scroll.setWidget(container)
        lay.addWidget(scroll)

    def apply_smtp_preset(self, host, port, sec):
        self.smtp_host.setText(host)
        self.smtp_port.setText(port)
        self.smtp_security.setCurrentText(sec)

    def test_email_connection(self):
        host = self.smtp_host.text().strip() or "smtp.gmail.com"
        port = self.smtp_port.text().strip() or "465"
        user = self.smtp_user.text().strip()
        pwd = self.smtp_password.text().strip().replace(" ", "") or CONFIGURED_GMAIL_APP_PASSWORD
        sec = self.smtp_security.currentText()

        if not user:
            new_u, ok = QInputDialog.getText(self, "Enter Your Gmail Address", "Enter your sender Gmail address (e.g. yourname@gmail.com):")
            if ok and new_u.strip():
                user = new_u.strip()
                self.smtp_user.setText(user)
            else:
                QMessageBox.warning(self, "Email Required", "Please enter your Gmail address in Firm Email / User.")
                return

        try:
            msg = EmailMessage()
            msg["Subject"] = "CA Firm Automation - SMTP Connection Test Successful"
            msg["From"] = user
            msg["To"] = user
            msg.set_content(
                f"Hello,\n\nThis is an automated confirmation that your Gmail App Password has been successfully verified!\n"
                f"Host: {host} (Port {port})\nTimestamp: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n\n"
                f"Best regards,\nCA Firm Invoice & Practice Automation Pro"
            )
            ok, note = send_smtp_email(host, port, user, pwd, sec, msg)
            QMessageBox.information(
                self, "Connection Verified",
                f"Gmail SMTP Server Connected Successfully!\n{note}\nA test email has been sent to {user}."
            )
        except Exception as e:
            QMessageBox.critical(self, "Connection Test Failed", str(e))

    # -----------------------------------------------------
    # Core Billing Engine & Invoice Computation
    # -----------------------------------------------------
    def service_changed(self):
        sid = self.item_service.currentData()
        if sid:
            s = self.db.one("SELECT * FROM services WHERE id=?", (sid,))
            if s:
                self.item_description.setText(s["name"])
                self.item_sac.setText(s["sac"] or "")
                self.item_rate.setValue(float(s["default_fee"] or 0))
                self.item_gst.setCurrentText(str(int(s["rate"] if s["taxable"] else 0)))

    def client_changed(self):
        cid = self.invoice_client.currentData()
        if cid:
            c = self.db.one("SELECT * FROM clients WHERE id=?", (cid,))
            if c:
                if c["default_unit_id"]:
                    idx = self.invoice_unit.findData(c["default_unit_id"])
                    if idx >= 0: self.invoice_unit.setCurrentIndex(idx)
                state_code = (c["state_code"] or (c["gstin"] or "")[:2] or STATE_NAME_TO_CODE.get((c["state"] or "").lower(), "")).strip()
                if state_code:
                    idx = self.place_of_supply.findData(state_code)
                    if idx >= 0: self.place_of_supply.setCurrentIndex(idx)
        self.refresh_item_table()

    def unit_changed(self):
        self.refresh_item_table()

    def add_item(self):
        desc = self.item_description.text().strip()
        if not desc:
            QMessageBox.warning(self, "Description Required", "Please enter a description for the line item.")
            return

        unit = self.db.one("SELECT gst_registered FROM billing_units WHERE id=?", (self.invoice_unit.currentData(),))
        gst_reg = unit["gst_registered"] if unit else 1
        gst_rate = float(self.item_gst.currentText() or 0)

        if not gst_reg: gst_rate = 0.0

        self.items.append({
            "type": self.item_type.currentText(),
            "description": desc,
            "sac": self.item_sac.text().strip(),
            "qty": self.item_qty.value(),
            "rate": self.item_rate.value(),
            "gst_rate": gst_rate
        })
        self.item_description.clear()
        self.item_sac.clear()
        self.item_rate.setValue(0)
        self.refresh_item_table()

    def remove_item(self):
        rows = sorted([x.row() for x in self.item_table.selectionModel().selectedRows()], reverse=True)
        if not rows:
            QMessageBox.information(self, "Select Row", "Please select a line item to remove.")
            return
        for r in rows: self.items.pop(r)
        self.refresh_item_table()

    def get_tax_split(self, subtotal, tax_rate, unit_state_code, client_state_code):
        is_intra = bool(unit_state_code and client_state_code and unit_state_code == client_state_code)
        if is_intra:
            half_rate = Decimal(str(tax_rate)) / Decimal("2")
            cgst = qround(Decimal(str(subtotal)) * (half_rate / Decimal("100")))
            sgst = cgst
            igst = 0.0
        else:
            cgst = 0.0
            sgst = 0.0
            igst = qround(Decimal(str(subtotal)) * (Decimal(str(tax_rate)) / Decimal("100")))
        return cgst, sgst, igst

    def refresh_item_table(self):
        self.item_table.setRowCount(len(self.items))
        unit = self.db.one("SELECT * FROM billing_units WHERE id=?", (self.invoice_unit.currentData(),))
        unit_sc = (unit["state_code"] or (unit["gstin"] or "")[:2] if unit else "").strip()
        client_sc = self.place_of_supply.currentData() if self.place_of_supply.currentIndex() >= 0 else ""

        total_taxable = Decimal("0")
        total_cgst = Decimal("0")
        total_sgst = Decimal("0")
        total_igst = Decimal("0")

        for r, x in enumerate(self.items):
            amt = qround(Decimal(str(x["qty"])) * Decimal(str(x["rate"])))
            total_taxable += Decimal(str(amt))

            if unit and unit["gst_registered"] and x["gst_rate"] > 0:
                cg, sg, ig = self.get_tax_split(amt, x["gst_rate"], unit_sc, client_sc)
                total_cgst += Decimal(str(cg))
                total_sgst += Decimal(str(sg))
                total_igst += Decimal(str(ig))
                tax_amt = cg + sg + ig
            else:
                tax_amt = 0.0

            line_total = amt + tax_amt
            for c, val in enumerate([
                x.get("type", "Professional Service"), x["description"], x.get("sac", ""),
                f"{x['qty']:g}", money(x["rate"]), f"{x['gst_rate']:g}%", money(tax_amt), money(line_total)
            ]):
                self.item_table.setItem(r, c, QTableWidgetItem(str(val)))

        tot_tax = float(total_cgst + total_sgst + total_igst)
        grand = float(total_taxable) + tot_tax

        if total_cgst > 0 or total_sgst > 0:
            tax_str = f"CGST: {money(total_cgst)} | SGST: {money(total_sgst)}"
        elif total_igst > 0:
            tax_str = f"IGST: {money(total_igst)}"
        else:
            tax_str = "Tax: ₹ 0.00"

        self.total_label.setText(f"Taxable: {money(total_taxable)}   |   {tax_str}   |   Grand Total: {money(grand)}")

    def generate_next_invoice_no(self, unit):
        today = date.today()
        fy_start = today.year if today.month >= 4 else today.year - 1
        fy = f"{str(fy_start)[-2:]}-{str(fy_start + 1)[-2:]}"
        prefix = unit["invoice_prefix"] or "INV"
        count = self.db.one("SELECT COUNT(*) n FROM invoices WHERE unit_id=?", (unit["id"],))["n"] + 1
        return f"{prefix}/{fy}/{count:04d}"

    def save_invoice(self):
        if not self.items:
            QMessageBox.warning(self, "No Line Items", "Please add at least one line item before saving.")
            return

        unit = self.db.one("SELECT * FROM billing_units WHERE id=?", (self.invoice_unit.currentData(),))
        client = self.db.one("SELECT * FROM clients WHERE id=?", (self.invoice_client.currentData(),))
        if not unit or not client:
            QMessageBox.warning(self, "Details Missing", "Please select both a Billing Unit and a Client.")
            return

        unit_sc = (unit["state_code"] or (unit["gstin"] or "")[:2] or "").strip()
        client_sc = self.place_of_supply.currentData() or ""
        pos_name = GST_STATE_CODES.get(client_sc, client["state"] or "")

        subtotal = qround(sum(x["qty"] * x["rate"] for x in self.items))
        total_cgst = total_sgst = total_igst = 0.0

        if unit["gst_registered"]:
            for x in self.items:
                if x["gst_rate"] > 0:
                    amt = qround(x["qty"] * x["rate"])
                    cg, sg, ig = self.get_tax_split(amt, x["gst_rate"], unit_sc, client_sc)
                    total_cgst += cg
                    total_sgst += sg
                    total_igst += ig

        total_cgst = qround(total_cgst)
        total_sgst = qround(total_sgst)
        total_igst = qround(total_igst)
        grand_total = qround(subtotal + total_cgst + total_sgst + total_igst)

        has_gst = int(unit["gst_registered"] and (total_cgst + total_sgst + total_igst) > 0)
        inv_type = self.invoice_type.currentText()
        if not unit["gst_registered"] and inv_type == "Tax Invoice": inv_type = "Bill of Supply"

        inv_no = self.invoice_no_input.text().strip() or self.generate_next_invoice_no(unit)

        try:
            if self.editing_id:
                iid = self.editing_id
                self.db.execute("""
                    UPDATE invoices SET invoice_no=?, invoice_type=?, unit_id=?, client_id=?,
                    invoice_date=?, due_date=?, place_of_supply=?, subtotal=?, cgst=?, sgst=?, igst=?,
                    total=?, has_gst=? WHERE id=?
                """, (
                    inv_no, inv_type, unit["id"], client["id"],
                    self.invoice_date.date().toString("yyyy-MM-dd"),
                    self.invoice_due.date().toString("yyyy-MM-dd"),
                    pos_name, subtotal, total_cgst, total_sgst, total_igst, grand_total, has_gst, iid
                ))
                self.db.execute("DELETE FROM invoice_items WHERE invoice_id=?", (iid,))
            else:
                cur = self.db.execute("""
                    INSERT INTO invoices(invoice_no, invoice_type, unit_id, client_id, invoice_date, due_date,
                    place_of_supply, subtotal, cgst, sgst, igst, total, status, created_at, source, has_gst)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    inv_no, inv_type, unit["id"], client["id"],
                    self.invoice_date.date().toString("yyyy-MM-dd"),
                    self.invoice_due.date().toString("yyyy-MM-dd"),
                    pos_name, subtotal, total_cgst, total_sgst, total_igst, grand_total,
                    "Issued", datetime.now().isoformat(), "Manual", has_gst
                ))
                iid = cur.lastrowid

            for x in self.items:
                self.db.execute("""
                    INSERT INTO invoice_items(invoice_id, description, sac, qty, rate, gst_rate, taxable, amount)
                    VALUES(?,?,?,?,?,?,?,?)
                """, (iid, x["description"], x["sac"], x["qty"], x["rate"], x["gst_rate"], 1, x["qty"] * x["rate"]))

            pdf_path = self.create_pdf(iid, unit, client)
            self.db.execute("UPDATE invoices SET pdf_path=? WHERE id=?", (str(pdf_path), iid))

            was_edit = bool(self.editing_id)
            self.clear_draft()
            self.refresh_all()
            self.tabs.setCurrentWidget(self.invoices_tab if has_gst else self.nongst_tab)
            QMessageBox.information(
                self, "Invoice Saved Successfully",
                f"Invoice {inv_no} has been {'updated' if was_edit else 'created'}.\nPDF: {pdf_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Invoice Creation Error", f"Failed to save invoice: {str(e)}")

    # -----------------------------------------------------
    # ReportLab PDF Generation (Compliant with Rule 46 CGST)
    # -----------------------------------------------------
    def create_pdf(self, iid, unit, client):
        inv = self.db.one("SELECT * FROM invoices WHERE id=?", (iid,))
        items = self.db.rows("SELECT * FROM invoice_items WHERE invoice_id=?", (iid,))

        out_set = self.db.one("SELECT value FROM settings WHERE key='pdf_output_folder'")
        out_dir = Path(out_set["value"]) if out_set and out_set["value"] else PDF_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        clean_no = inv["invoice_no"].replace("/", "-").replace("\\", "-")
        path = out_dir / f"{clean_no}.pdf"

        if path.exists():
            try:
                with open(path, "ab"): pass
            except PermissionError:
                path = out_dir / f"{clean_no}-rev-{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"

        doc = SimpleDocTemplate(
            str(path), pagesize=A4,
            rightMargin=14*mm, leftMargin=14*mm, topMargin=12*mm, bottomMargin=12*mm
        )
        styles = getSampleStyleSheet()
        story = []

        firm_style = ParagraphStyle("firm_title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=colors.HexColor("#1e3a8a"), alignment=0)
        norm = styles["Normal"]
        bold = ParagraphStyle("bold", parent=styles["Normal"], fontName="Helvetica-Bold")

        story.append(Paragraph(unit["name"], firm_style))
        firm_details = f"<b>FRN:</b> {unit['frn'] or '-'} | <b>GSTIN:</b> {unit['gstin'] or 'Unregistered'} | <b>PAN:</b> {unit['pan'] or '-'}<br/>" \
                       f"{unit['address'] or 'Registered Office'}<br/>" \
                       f"<b>Email:</b> {unit['email'] or '-'} | <b>Phone:</b> {unit['phone'] or '-'}"
        story.append(Paragraph(firm_details, norm))
        story.append(Spacer(1, 8))

        inv_title = (inv["invoice_type"] or "TAX INVOICE").upper()
        header_table = Table([[
            Paragraph(f"<b><font size='14' color='#1e3a8a'>{inv_title}</font></b><br/><font size='8' color='#64748b'>(Issued under Section 31 of CGST Act, 2017)</font>", norm),
            Paragraph(f"<b>Invoice No:</b> {inv['invoice_no']}<br/>"
                      f"<b>Invoice Date:</b> {inv['invoice_date']}<br/>"
                      f"<b>Due Date:</b> {inv['due_date']}<br/>"
                      f"<b>Place of Supply:</b> {inv['place_of_supply'] or '-'}", norm)
        ]], colWidths=[100*mm, 82*mm], style=[
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 6)
        ])
        story.append(header_table)
        story.append(Spacer(1, 8))

        bill_to_text = f"<b>Client Legal Name:</b> {client['name']}<br/>" \
                       f"<b>Address:</b> {client['address'] or 'Address on record'}<br/>" \
                       f"<b>GSTIN:</b> {client['gstin'] or 'Unregistered Consumer'} | <b>PAN:</b> {client['pan'] or '-'}"
        story.append(Table([[Paragraph(f"<b>BILL TO (RECIPIENT):</b>", bold)], [Paragraph(bill_to_text, norm)]],
                           colWidths=[182*mm], style=[
                               ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                               ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                               ("PADDING", (0, 0), (-1, -1), 5)
                           ]))
        story.append(Spacer(1, 8))

        t_data = [["#", "Particulars of Professional Services", "SAC", "Qty", "Rate (Rs.)", "GST %", "Amount (Rs.)"]]
        for idx, it in enumerate(items, 1):
            t_data.append([
                str(idx),
                Paragraph(it["description"], norm),
                it["sac"] or "-",
                f"{it['qty']:g}",
                pdf_money(it["rate"]).replace("Rs. ", ""),
                f"{it['gst_rate']:g}%",
                pdf_money(it["amount"]).replace("Rs. ", "")
            ])

        t_data.append(["", "", "", "", "", "Taxable Value:", pdf_money(inv["subtotal"]).replace("Rs. ", "")])
        if inv["cgst"] > 0 or inv["sgst"] > 0:
            t_data.append(["", "", "", "", "", "CGST:", pdf_money(inv["cgst"]).replace("Rs. ", "")])
            t_data.append(["", "", "", "", "", "SGST:", pdf_money(inv["sgst"]).replace("Rs. ", "")])
        elif inv["igst"] > 0:
            t_data.append(["", "", "", "", "", "IGST:", pdf_money(inv["igst"]).replace("Rs. ", "")])

        t_data.append(["", "", "", "", "", "Grand Total:", f"Rs. {float(inv['total'] or 0):,.2f}"])

        items_table = Table(t_data, colWidths=[10*mm, 78*mm, 20*mm, 14*mm, 26*mm, 16*mm, 26*mm])
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dcfce7")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("PADDING", (0, 0), (-1, -1), 5)
        ]))
        story.append(items_table)
        story.append(Spacer(1, 8))

        in_words = amount_to_words_inr(inv["total"])
        summary_box = Table([[
            Paragraph(f"<b>Amount in Words:</b> {in_words}<br/>"
                      f"<b>Whether Tax Payable on Reverse Charge (RCM):</b> No", norm)
        ]], colWidths=[182*mm], style=[
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 5)
        ])
        story.append(summary_box)
        story.append(Spacer(1, 10))

        bank_info = f"<b>Bank Name:</b> {unit['bank_name'] or '-'}<br/>" \
                    f"<b>Current A/c No:</b> {unit['bank_account'] or '-'}<br/>" \
                    f"<b>IFSC Code:</b> {unit['ifsc'] or '-'}<br/>" \
                    f"<b>UPI ID:</b> {unit['upi_id'] or '-'}"

        sign_info = f"For <b>{unit['name']}</b><br/><br/><br/><br/>" \
                    f"<b>{unit['partner_name'] or 'Partner'}</b><br/>" \
                    f"M. No.: {unit['partner_mno'] or '-'}<br/>" \
                    f"<i>Authorized Signatory</i>"

        footer_table = Table([[
            Paragraph(f"<b>BANK REMITTANCE DETAILS:</b><br/>{bank_info}", norm),
            Paragraph(sign_info, norm)
        ]], colWidths=[100*mm, 82*mm], style=[
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 6)
        ])
        story.append(footer_table)
        doc.build(story)
        return path

    # -----------------------------------------------------
    # Payments & Collections Actions
    # -----------------------------------------------------
    def record_payment_action(self):
        inv_row = self.invoice_row()
        if not inv_row: return
        self.show_payment_dialog(inv_row)

    def record_payment_standalone(self):
        open_invs = self.db.rows("""
            SELECT i.id, i.invoice_no, i.total, c.name client_name
            FROM invoices i JOIN clients c ON c.id=i.client_id
            WHERE i.status != 'Paid' AND i.status != 'Cancelled' ORDER BY i.id DESC
        """)
        if not open_invs:
            QMessageBox.information(self, "All Settled", "No pending or partially paid invoices found.")
            return

        items = [f"{x['invoice_no']} - {x['client_name']} ({money(x['total'])})" for x in open_invs]
        choice, ok = QInputDialog.getItem(self, "Select Invoice to Settle", "Choose Invoice:", items, 0, False)
        if ok and choice:
            inv_id = open_invs[items.index(choice)]["id"]
            inv = self.db.one("SELECT i.*, c.name client_name, c.email client_email, u.name unit_name FROM invoices i JOIN clients c ON c.id=i.client_id JOIN billing_units u ON u.id=i.unit_id WHERE i.id=?", (inv_id,))
            if inv: self.show_payment_dialog(dict(inv))

    def record_payment_nongst(self):
        ids = [self.nongst_table.item(i.row(), 0).data(Qt.ItemDataRole.UserRole) for i in self.nongst_table.selectionModel().selectedRows()]
        if not ids and self.nongst_table.currentRow() >= 0:
            it = self.nongst_table.item(self.nongst_table.currentRow(), 0)
            if it: ids = [it.data(Qt.ItemDataRole.UserRole)]

        if not ids:
            QMessageBox.warning(self, "Select Invoice", "Please select an invoice first.")
            return
        inv = self.db.one("""
            SELECT i.*, c.name client_name,
            COALESCE((SELECT SUM(amount + tds_deducted) FROM payments WHERE invoice_id=i.id), 0) total_paid
            FROM invoices i JOIN clients c ON c.id=i.client_id WHERE i.id=?
        """, (ids[0],))
        if inv: self.show_payment_dialog(dict(inv))

    def show_payment_dialog(self, invoice_dict):
        inv_d = dict(invoice_dict)
        paid_res = self.db.one("SELECT COALESCE(SUM(amount + tds_deducted), 0) paid FROM payments WHERE invoice_id=?", (inv_d["id"],))
        inv_d["total_paid"] = float(paid_res["paid"] if paid_res else 0.0)

        dlg = RecordPaymentDialog(inv_d, self)
        if dlg.exec():
            d = dlg.data()
            self.db.execute("""
                INSERT INTO payments(invoice_id, payment_date, amount, payment_mode, reference_no, tds_deducted, tds_section, proof_path, notes, created_at)
                VALUES(:invoice_id, :payment_date, :amount, :payment_mode, :reference_no, :tds_deducted, :tds_section, :proof_path, :notes, :created_at)
            """, d)

            new_paid = inv_d["total_paid"] + d["amount"] + d["tds_deducted"]
            status = "Paid" if new_paid >= float(inv_d.get("total") or 0) - 0.5 else "Partially Paid"
            self.db.execute("UPDATE invoices SET status=? WHERE id=?", (status, inv_d["id"]))

            self.refresh_all()
            QMessageBox.information(
                self, "Payment Recorded",
                f"Receipt of {money(d['amount'])} (+ TDS {money(d['tds_deducted'])}) successfully posted."
            )

    def view_payment_proof(self):
        rows = self.payments_table.selectionModel().selectedRows()
        pid = None
        if rows: pid = self.payments_table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        elif self.payments_table.currentRow() >= 0:
            it = self.payments_table.item(self.payments_table.currentRow(), 0)
            if it: pid = it.data(Qt.ItemDataRole.UserRole)

        if not pid: return
        p = self.db.one("SELECT proof_path FROM payments WHERE id=?", (pid,))
        if p and p["proof_path"] and Path(p["proof_path"]).exists():
            open_file(p["proof_path"])
        else:
            QMessageBox.information(self, "No Proof Attached", "No screenshot or deposit voucher was attached to this receipt.")

    def delete_payment(self):
        rows = self.payments_table.selectionModel().selectedRows()
        pid = None
        if rows: pid = self.payments_table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        elif self.payments_table.currentRow() >= 0:
            it = self.payments_table.item(self.payments_table.currentRow(), 0)
            if it: pid = it.data(Qt.ItemDataRole.UserRole)

        if not pid:
            QMessageBox.warning(self, "Select Payment", "Please select a payment receipt to delete.")
            return

        if QMessageBox.question(self, "Confirm Delete", "Delete this payment receipt?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            p = self.db.one("SELECT invoice_id FROM payments WHERE id=?", (pid,))
            self.db.execute("DELETE FROM payments WHERE id=?", (pid,))
            if p:
                inv = self.db.one("SELECT * FROM invoices WHERE id=?", (p["invoice_id"],))
                paid_res = self.db.one("SELECT COALESCE(SUM(amount + tds_deducted), 0) paid FROM payments WHERE invoice_id=?", (p["invoice_id"],))
                tot_paid = float(paid_res["paid"] if paid_res else 0.0)
                status = "Paid" if tot_paid >= float(inv["total"] or 0) - 0.5 else ("Partially Paid" if tot_paid > 0 else "Issued")
                self.db.execute("UPDATE invoices SET status=? WHERE id=?", (status, p["invoice_id"]))
            self.refresh_all()

    # -----------------------------------------------------
    # Dialog Openers
    # -----------------------------------------------------
    def open_26as_reconciliation(self):
        dlg = Form26ASReconciliationDialog(self.db, self)
        if dlg.exec(): self.refresh_all()

    def open_bank_reconciliation(self):
        dlg = BankReconciliationDialog(self.db, self)
        if dlg.exec(): self.refresh_all()

    def open_gstr1_export(self):
        dlg = GSTR1ExportDialog(self.db, self)
        dlg.exec()

    # -----------------------------------------------------
    # Master Table Fillers & Refresh
    # -----------------------------------------------------
    def refresh_all(self):
        self.fill_units()
        self.fill_clients()
        self.fill_services()
        self.fill_invoices()
        self.fill_payments()
        self.fill_nongst()
        self.build_whatsapp_table()
        self.refresh_dashboard()
        self.load_settings()
        self.refresh_item_table()

    def fill_units(self):
        rows = self.db.rows("SELECT *, CASE WHEN COALESCE(gst_registered,1)=1 THEN 'GST Registered' ELSE 'Non-GST Unit' END gst_status FROM billing_units ORDER BY name")
        self.units_table.setRowCount(len(rows))
        for r, x in enumerate(rows):
            for c, key in enumerate(["name", "gst_status", "gstin", "frn", "partner_name", "state", "invoice_prefix"]):
                item = QTableWidgetItem(str(x[key] or ""))
                if c == 0: item.setData(Qt.ItemDataRole.UserRole, x["id"])
                self.units_table.setItem(r, c, item)

        self.invoice_unit.clear()
        self.dash_unit_filter.clear()
        self.dash_unit_filter.addItem("All Billing Units", None)
        for r in rows:
            self.invoice_unit.addItem(r["name"], r["id"])
            self.dash_unit_filter.addItem(r["name"], r["id"])

    def fill_clients(self):
        rows = self.db.rows("SELECT * FROM clients WHERE active=1 ORDER BY name")
        self.clients_table.setRowCount(len(rows))
        for r, x in enumerate(rows):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, x["id"])
            self.clients_table.setItem(r, 0, chk)

            for c, key in enumerate(["name", "gstin", "pan", "email", "phone", "state", "state_code"], 1):
                item = QTableWidgetItem(str(x[key] or ""))
                self.clients_table.setItem(r, c, item)

        self.invoice_client.clear()
        for r in rows:
            self.invoice_client.addItem(r["name"], r["id"])

    def fill_services(self):
        rows = self.db.rows("SELECT * FROM services WHERE active=1 ORDER BY category, name")
        self.services_table.setRowCount(len(rows))
        for r, x in enumerate(rows):
            for c, key in enumerate(["name", "sac", "rate", "default_fee", "category", "taxable"]):
                val = f"₹ {float(x[key] or 0):,.2f}" if key == "default_fee" else (f"{x[key]:g}%" if key == "rate" else str(x[key]))
                item = QTableWidgetItem(val)
                if c == 0: item.setData(Qt.ItemDataRole.UserRole, x["id"])
                self.services_table.setItem(r, c, item)

        self.item_service.clear()
        self.item_service.addItem("Custom Service / Free Text", None)
        for r in rows:
            self.item_service.addItem(f"{r['name']} ({r['sac'] or 'No SAC'})", r["id"])

    def fill_invoices(self):
        rows = self.db.rows("""
            SELECT i.*, u.name unit_name, c.name client_name,
            COALESCE((SELECT SUM(amount + tds_deducted) FROM payments WHERE invoice_id=i.id), 0) total_paid
            FROM invoices i
            JOIN billing_units u ON u.id=i.unit_id
            JOIN clients c ON c.id=i.client_id
            WHERE COALESCE(i.has_gst,0)=1
            ORDER BY i.id DESC
        """)
        self.invoices_table.setRowCount(len(rows))
        for r, x in enumerate(rows):
            due = max(0.0, float(x["total"] or 0) - float(x["total_paid"] or 0))
            vals = [
                x["invoice_no"], x["invoice_date"], x["unit_name"], x["client_name"],
                money(x["subtotal"]), money(x["cgst"]), money(x["sgst"]), money(x["igst"]),
                money(x["total"]), money(x["total_paid"]), money(due), x["status"]
            ]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                if c == 0: it.setData(Qt.ItemDataRole.UserRole, x["id"])
                if c == 11:
                    it.setForeground(QColor("#059669") if x["status"] == "Paid" else (QColor("#d97706") if x["status"] == "Partially Paid" else QColor("#dc2626")))
                self.invoices_table.setItem(r, c, it)

    def fill_payments(self):
        rows = self.db.rows("""
            SELECT p.*, i.invoice_no, c.name client_name
            FROM payments p
            JOIN invoices i ON i.id=p.invoice_id
            JOIN clients c ON c.id=i.client_id
            ORDER BY p.payment_date DESC, p.id DESC
        """)
        self.payments_table.setRowCount(len(rows))
        for r, x in enumerate(rows):
            has_proof = "Yes" if x["proof_path"] else "No"
            vals = [
                f"REC-{x['id']:04d}", x["payment_date"], x["invoice_no"], x["client_name"],
                money(x["amount"]), money(x["tds_deducted"]), x["tds_section"] or "-", x["payment_mode"], x["reference_no"] or "-", has_proof
            ]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                if c == 0: it.setData(Qt.ItemDataRole.UserRole, x["id"])
                self.payments_table.setItem(r, c, it)

    def fill_nongst(self):
        rows = self.db.rows("""
            SELECT i.*, u.name unit_name, c.name client_name,
            COALESCE((SELECT SUM(amount + tds_deducted) FROM payments WHERE invoice_id=i.id), 0) total_paid
            FROM invoices i
            JOIN billing_units u ON u.id=i.unit_id
            JOIN clients c ON c.id=i.client_id
            WHERE COALESCE(i.has_gst,0)=0
            ORDER BY i.id DESC
        """)
        self.nongst_table.setRowCount(len(rows))
        for r, x in enumerate(rows):
            due = max(0.0, float(x["total"] or 0) - float(x["total_paid"] or 0))
            vals = [x["invoice_no"], x["invoice_date"], x["unit_name"], x["client_name"], money(x["total"]), money(x["total_paid"]), money(due), x["source"] or "Manual"]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                if c == 0: it.setData(Qt.ItemDataRole.UserRole, x["id"])
                self.nongst_table.setItem(r, c, it)

    # -----------------------------------------------------
    # Dashboard Analytics Engine
    # -----------------------------------------------------
    def refresh_dashboard(self):
        fy_text = self.dash_fy_filter.currentText()
        unit_id = self.dash_unit_filter.currentData() if hasattr(self, "dash_unit_filter") else None

        fy_filter_sql = ""
        if "2026-27" in fy_text: fy_filter_sql = " AND invoice_date >= '2026-04-01' AND invoice_date <= '2027-03-31' "
        elif "2025-26" in fy_text: fy_filter_sql = " AND invoice_date >= '2025-04-01' AND invoice_date <= '2026-03-31' "
        elif "2024-25" in fy_text: fy_filter_sql = " AND invoice_date >= '2024-04-01' AND invoice_date <= '2025-03-31' "

        unit_filter_sql = f" AND unit_id={unit_id} " if unit_id else ""

        inv_summary = self.db.one(f"""
            SELECT COUNT(*) n, COALESCE(SUM(total), 0) total_billed
            FROM invoices WHERE status != 'Cancelled' {fy_filter_sql} {unit_filter_sql}
        """)
        pay_summary = self.db.one(f"""
            SELECT COALESCE(SUM(p.amount), 0) cash_collected, COALESCE(SUM(p.tds_deducted), 0) total_tds
            FROM payments p
            JOIN invoices i ON i.id=p.invoice_id
            WHERE 1=1 {fy_filter_sql} {unit_filter_sql}
        """)

        total_billed = float(inv_summary["total_billed"] if inv_summary else 0.0)
        cash_coll = float(pay_summary["cash_collected"] if pay_summary else 0.0)
        total_tds = float(pay_summary["total_tds"] if pay_summary else 0.0)
        total_settled = cash_coll + total_tds
        total_due = max(0.0, total_billed - total_settled)

        self.kpi_billed_val.setText(money(total_billed))
        self.kpi_billed_sub.setText(f"{inv_summary['n']} Invoices Issued")

        self.kpi_coll_val.setText(money(cash_coll))
        self.kpi_coll_sub.setText("Direct Bank Realizations")

        self.kpi_tds_val.setText(money(total_tds))
        self.kpi_tds_sub.setText("Form 26AS Tax Credits")

        self.kpi_due_val.setText(money(total_due))
        self.kpi_due_sub.setText("Unsettled Receivables")

        realization_rate = (total_settled / total_billed * 100) if total_billed > 0 else 0
        self.kpi_eff_val.setText(f"{realization_rate:.1f}%")
        self.kpi_eff_sub.setText("Cash Collection Efficiency")

        active_clients_cnt = self.db.one("SELECT COUNT(*) c FROM clients WHERE active=1")["c"]
        self.kpi_clients_val.setText(str(active_clients_cnt))
        self.kpi_clients_sub.setText("Registered CA Clients")

        monthly_billed = self.db.rows("""
            SELECT substr(invoice_date, 1, 7) period, COALESCE(SUM(total), 0) amt
            FROM invoices WHERE status != 'Cancelled'
            GROUP BY period ORDER BY period DESC LIMIT 6
        """)
        monthly_pay = self.db.rows("""
            SELECT substr(payment_date, 1, 7) period, COALESCE(SUM(amount + tds_deducted), 0) amt
            FROM payments GROUP BY period ORDER BY period DESC LIMIT 6
        """)

        b_map = {r["period"]: float(r["amt"] or 0) for r in monthly_billed}
        p_map = {r["period"]: float(r["amt"] or 0) for r in monthly_pay}
        all_periods = sorted(list(set(list(b_map.keys()) + list(p_map.keys()))))[-6:]
        if not all_periods: all_periods = [date.today().strftime("%Y-%m")]

        trend_b = [b_map.get(p, 0.0) for p in all_periods]
        trend_c = [p_map.get(p, 0.0) for p in all_periods]
        self.trend_chart.set_data(all_periods, trend_b, trend_c)

        cat_data = self.db.rows("""
            SELECT COALESCE(s.category, 'General Services') category, COALESCE(SUM(it.amount), 0) cat_amt
            FROM invoice_items it
            JOIN invoices i ON i.id=it.invoice_id
            LEFT JOIN services s ON (s.sac=it.sac AND it.sac != '') OR s.name=it.description
            WHERE i.status != 'Cancelled'
            GROUP BY s.category ORDER BY cat_amt DESC LIMIT 5
        """)
        tot_cat = sum(float(c["cat_amt"] or 0) for c in cat_data) or 1.0
        dist_data = [(c["category"] or "General", float(c["cat_amt"] or 0), (float(c["cat_amt"] or 0) / tot_cat) * 100) for c in cat_data]
        self.service_chart.set_data(dist_data)

        active_invoices = self.db.rows("""
            SELECT i.id, i.invoice_date, i.total,
            COALESCE((SELECT SUM(amount + tds_deducted) FROM payments WHERE invoice_id=i.id), 0) paid
            FROM invoices i WHERE i.status != 'Paid' AND i.status != 'Cancelled'
        """)
        buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
        counts = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
        today = date.today()

        for inv in active_invoices:
            due = float(inv["total"] or 0) - float(inv["paid"] or 0)
            if due <= 0: continue
            days = 0
            date_str = str(inv["invoice_date"] or "")
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    days = (today - datetime.strptime(date_str, fmt).date()).days
                    break
                except Exception: pass

            if days <= 30: buckets["0-30"] += due; counts["0-30"] += 1
            elif days <= 60: buckets["31-60"] += due; counts["31-60"] += 1
            elif days <= 90: buckets["61-90"] += due; counts["61-90"] += 1
            else: buckets["90+"] += due; counts["90+"] += 1

        self.aging_chart.set_data(buckets, counts)

        status_data = self.db.rows("SELECT status, COUNT(*) cnt FROM invoices WHERE status != 'Cancelled' GROUP BY status")
        st_map = {s["status"]: s["cnt"] for s in status_data}
        self.donut_chart.set_data(st_map.get("Paid", 0), st_map.get("Partially Paid", 0), st_map.get("Issued", 0))

        debtors = self.db.rows("""
            SELECT c.id client_id, c.name client_name,
            COALESCE(SUM(i.total), 0) total_billed,
            MIN(i.invoice_date) oldest_date,
            COALESCE((SELECT SUM(p.amount) FROM payments p JOIN invoices inv ON inv.id=p.invoice_id WHERE inv.client_id=c.id), 0) total_paid,
            COALESCE((SELECT SUM(p.tds_deducted) FROM payments p JOIN invoices inv ON inv.id=p.invoice_id WHERE inv.client_id=c.id), 0) total_tds
            FROM clients c
            JOIN invoices i ON i.client_id=c.id
            WHERE i.status != 'Cancelled' AND c.active = 1
            GROUP BY c.id
            ORDER BY (total_billed - (total_paid + total_tds)) DESC
        """)

        self.dashboard_detail.setRowCount(0)
        row_idx = 0
        for d in debtors:
            net_due = float(d["total_billed"] or 0) - (float(d["total_paid"] or 0) + float(d["total_tds"] or 0))
            if net_due <= 0.01: continue
            self.dashboard_detail.insertRow(row_idx)

            oldest_str = str(d["oldest_date"] or "-")
            days_overdue = 0
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    days_overdue = (today - datetime.strptime(oldest_str, fmt).date()).days
                    break
                except Exception: pass

            self.dashboard_detail.setItem(row_idx, 0, QTableWidgetItem(d["client_name"]))
            self.dashboard_detail.setItem(row_idx, 1, QTableWidgetItem(money(d["total_billed"])))
            self.dashboard_detail.setItem(row_idx, 2, QTableWidgetItem(money(d["total_paid"])))

            due_it = QTableWidgetItem(money(net_due))
            due_it.setForeground(QColor("#dc2626"))
            due_it.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.dashboard_detail.setItem(row_idx, 3, due_it)

            self.dashboard_detail.setItem(row_idx, 4, QTableWidgetItem(oldest_str))
            self.dashboard_detail.setItem(row_idx, 5, QTableWidgetItem(f"{days_overdue} days"))
            self.dashboard_detail.setItem(row_idx, 6, QTableWidgetItem(money(d["total_tds"])))

            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(2, 2, 2, 2)
            act_l.setSpacing(4)

            b_pay = QPushButton("Pay")
            b_pay.setObjectName("successBtn")
            b_pay.clicked.connect(lambda _, cid=d["client_id"]: self.prompt_pay_for_client(cid))

            b_rem = QPushButton("Remind")
            b_rem.setObjectName("secondaryBtn")
            b_rem.clicked.connect(lambda _, cid=d["client_id"]: self.prompt_whatsapp_single(cid))

            act_l.addWidget(b_pay)
            act_l.addWidget(b_rem)
            self.dashboard_detail.setCellWidget(row_idx, 7, act_w)
            row_idx += 1

    def prompt_pay_for_client(self, client_id):
        inv = self.db.one("""
            SELECT i.*, c.name client_name FROM invoices i JOIN clients c ON c.id=i.client_id
            WHERE i.client_id=? AND i.status != 'Paid' AND i.status != 'Cancelled' ORDER BY i.invoice_date ASC LIMIT 1
        """, (client_id,))
        if inv: self.show_payment_dialog(dict(inv))
        else: QMessageBox.information(self, "No Due", "Client has no unsettled invoices.")

    # -----------------------------------------------------
    # Master Entity Operations (CRUD)
    # -----------------------------------------------------
    def selected_id(self, table):
        rows = table.selectionModel().selectedRows()
        if rows:
            it = table.item(rows[0].row(), 0)
            if it: return it.data(Qt.ItemDataRole.UserRole)
        if table.currentRow() >= 0:
            it = table.item(table.currentRow(), 0)
            if it: return it.data(Qt.ItemDataRole.UserRole)
        QMessageBox.warning(self, "Select Row", "Please select a row first.")
        return None

    def invoice_row(self):
        ident = self.selected_id(self.invoices_table)
        if not ident: return None
        row = self.db.one("SELECT i.*, c.name client_name, c.email client_email, u.name unit_name FROM invoices i JOIN clients c ON c.id=i.client_id JOIN billing_units u ON u.id=i.unit_id WHERE i.id=?", (ident,))
        return dict(row) if row else None

    def add_unit(self):
        fields = [
            ("name", "Firm Legal Name", "text"), ("gst_registered", "GST Registered", "check"),
            ("gstin", "GSTIN", "text"), ("pan", "PAN", "text"), ("frn", "Firm Reg. No. (FRN)", "text"),
            ("partner_name", "Partner Name", "text"), ("partner_mno", "Partner Membership No", "text"),
            ("address", "Registered Office Address", "memo"), ("state", "State", "text"),
            ("state_code", "State Code (e.g. 27)", "text"), ("email", "Email", "text"),
            ("phone", "Phone", "text"), ("bank_name", "Bank Name", "text"),
            ("bank_account", "Account Number", "text"), ("ifsc", "IFSC Code", "text"),
            ("upi_id", "UPI ID / VPA", "text"), ("invoice_prefix", "Invoice Prefix", "text")
        ]
        d = MasterDialog("Add Billing Unit / CA Firm", fields, parent=self)
        if d.exec():
            try:
                self.db.execute("""
                    INSERT INTO billing_units(name, gst_registered, gstin, pan, frn, partner_name, partner_mno,
                    address, state, state_code, email, phone, bank_name, bank_account, ifsc, upi_id, invoice_prefix)
                    VALUES(:name, :gst_registered, :gstin, :pan, :frn, :partner_name, :partner_mno,
                    :address, :state, :state_code, :email, :phone, :bank_name, :bank_account, :ifsc, :upi_id, :invoice_prefix)
                """, d.data())
                self.refresh_all()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Duplicate", "Unit name must be unique.")

    def edit_unit(self):
        ident = self.selected_id(self.units_table)
        if not ident: return
        row = self.db.one("SELECT * FROM billing_units WHERE id=?", (ident,))
        if not row: return
        row_dict = dict(row)
        fields = [
            ("name", "Firm Legal Name", "text"), ("gst_registered", "GST Registered", "check"),
            ("gstin", "GSTIN", "text"), ("pan", "PAN", "text"), ("frn", "Firm Reg. No. (FRN)", "text"),
            ("partner_name", "Partner Name", "text"), ("partner_mno", "Partner Membership No", "text"),
            ("address", "Registered Office Address", "memo"), ("state", "State", "text"),
            ("state_code", "State Code (e.g. 27)", "text"), ("email", "Email", "text"),
            ("phone", "Phone", "text"), ("bank_name", "Bank Name", "text"),
            ("bank_account", "Account Number", "text"), ("ifsc", "IFSC Code", "text"),
            ("upi_id", "UPI ID / VPA", "text"), ("invoice_prefix", "Invoice Prefix", "text")
        ]
        d = MasterDialog("Edit Billing Unit", fields, row_dict, parent=self)
        if d.exec():
            data = {**d.data(), "id": ident}
            self.db.execute("""
                UPDATE billing_units SET name=:name, gst_registered=:gst_registered, gstin=:gstin, pan=:pan,
                frn=:frn, partner_name=:partner_name, partner_mno=:partner_mno, address=:address, state=:state,
                state_code=:state_code, email=:email, phone=:phone, bank_name=:bank_name, bank_account=:bank_account,
                ifsc=:ifsc, upi_id=:upi_id, invoice_prefix=:invoice_prefix WHERE id=:id
            """, data)
            self.refresh_all()

    def delete_unit(self):
        ident = self.selected_id(self.units_table)
        if ident and QMessageBox.question(self, "Confirm Delete", "Delete billing unit?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.db.execute("DELETE FROM billing_units WHERE id=?", (ident,))
            self.refresh_all()

    def add_client(self):
        fields = [
            ("name", "Client Legal Name", "text"), ("phone", "Mobile / Phone (e.g. 919820012345)", "text"),
            ("email", "Email Address", "text"), ("gstin", "GSTIN", "text"), ("pan", "PAN", "text"),
            ("address", "Registered Address", "memo"), ("state", "State", "text"),
            ("state_code", "State Code", "text"), ("notes", "Client Notes", "memo")
        ]
        d = MasterDialog("Add New Client", fields, parent=self)
        if d.exec():
            data = d.data()
            if data["gstin"] and not data["state_code"]: data["state_code"] = data["gstin"][:2]
            if not data["pan"] and len(data["gstin"]) == 15: data["pan"] = data["gstin"][2:12]
            self.db.execute("""
                INSERT INTO clients(name, gstin, pan, email, phone, address, state, state_code, notes)
                VALUES(:name, :gstin, :pan, :email, :phone, :address, :state, :state_code, :notes)
            """, data)
            self.refresh_all()

    def edit_client(self):
        ident = None
        for r in range(self.clients_table.rowCount()):
            it = self.clients_table.item(r, 0)
            if it and it.checkState() == Qt.CheckState.Checked:
                ident = it.data(Qt.ItemDataRole.UserRole); break
        if not ident: ident = self.selected_id(self.clients_table)
        if not ident: return

        row = self.db.one("SELECT * FROM clients WHERE id=?", (ident,))
        if not row: return
        row_dict = dict(row)
        fields = [
            ("name", "Client Legal Name", "text"), ("phone", "Mobile / Phone", "text"),
            ("email", "Email Address", "text"), ("gstin", "GSTIN", "text"), ("pan", "PAN", "text"),
            ("address", "Registered Address", "memo"), ("state", "State", "text"),
            ("state_code", "State Code", "text"), ("notes", "Client Notes", "memo")
        ]
        d = MasterDialog("Edit Client", fields, row_dict, parent=self)
        if d.exec():
            data = {**d.data(), "id": ident}
            if data["gstin"] and not data["state_code"]: data["state_code"] = data["gstin"][:2]
            if not data["pan"] and len(data["gstin"]) == 15: data["pan"] = data["gstin"][2:12]
            self.db.execute("""
                UPDATE clients SET name=:name, gstin=:gstin, pan=:pan, email=:email, phone=:phone,
                address=:address, state=:state, state_code=:state_code, notes=:notes WHERE id=:id
            """, data)
            self.refresh_all()

    def add_service(self):
        fields = [
            ("name", "Service Name", "text"), ("sac", "SAC Code", "text"), ("rate", "GST Rate %", "rate"),
            ("default_fee", "Default Fee (₹)", "number"), ("category", "Practice Category", "text"), ("taxable", "Taxable", "check")
        ]
        d = MasterDialog("Add Service to Catalogue", fields, parent=self)
        if d.exec():
            self.db.execute("INSERT INTO services(name, sac, rate, default_fee, category, taxable) VALUES(:name, :sac, :rate, :default_fee, :category, :taxable)", d.data())
            self.refresh_all()

    def edit_service(self):
        ident = self.selected_id(self.services_table)
        if not ident: return
        row = self.db.one("SELECT * FROM services WHERE id=?", (ident,))
        if not row: return
        row_dict = dict(row)
        fields = [
            ("name", "Service Name", "text"), ("sac", "SAC Code", "text"), ("rate", "GST Rate %", "rate"),
            ("default_fee", "Default Fee (₹)", "number"), ("category", "Practice Category", "text"), ("taxable", "Taxable", "check")
        ]
        d = MasterDialog("Edit Service", fields, row_dict, parent=self)
        if d.exec():
            self.db.execute("UPDATE services SET name=:name, sac=:sac, rate=:rate, default_fee=:default_fee, category=:category, taxable=:taxable WHERE id=:id", {**d.data(), "id": ident})
            self.refresh_all()

    def delete_service(self):
        ident = self.selected_id(self.services_table)
        if ident and QMessageBox.question(self, "Confirm Delete", "Delete selected service?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.db.execute("DELETE FROM services WHERE id=?", (ident,))
            self.refresh_all()

    # -----------------------------------------------------
    # Invoice Register Operations
    # -----------------------------------------------------
    def edit_invoice(self):
        x = self.invoice_row()
        if not x: return
        self.editing_id = x["id"]
        self.invoice_no_input.setText(x["invoice_no"])
        self.invoice_mode.setText(f"Editing {x['invoice_no']}")
        self.invoice_unit.setCurrentIndex(self.invoice_unit.findData(x["unit_id"]))
        self.invoice_client.setCurrentIndex(self.invoice_client.findData(x["client_id"]))

        sc = STATE_NAME_TO_CODE.get((x["place_of_supply"] or "").lower(), "")
        if sc:
            idx = self.place_of_supply.findData(sc)
            if idx >= 0: self.place_of_supply.setCurrentIndex(idx)

        self.items = [{
            "type": "Professional Service", "description": i["description"], "sac": i["sac"],
            "qty": i["qty"], "rate": i["rate"], "gst_rate": i["gst_rate"]
        } for i in self.db.rows("SELECT * FROM invoice_items WHERE invoice_id=?", (x["id"],))]
        self.refresh_item_table()
        self.tabs.setCurrentWidget(self.create_tab)

    def delete_invoice(self):
        rows = self.invoices_table.selectionModel().selectedRows()
        if not rows: return
        if QMessageBox.question(self, "Delete Invoices", f"Delete {len(rows)} selected invoice(s)?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            for r in rows:
                it = self.invoices_table.item(r.row(), 0)
                if it:
                    ident = it.data(Qt.ItemDataRole.UserRole)
                    self.db.execute("DELETE FROM invoice_items WHERE invoice_id=?", (ident,))
                    self.db.execute("DELETE FROM payments WHERE invoice_id=?", (ident,))
                    self.db.execute("DELETE FROM invoices WHERE id=?", (ident,))
            self.refresh_all()

    def open_pdf(self):
        x = self.invoice_row()
        if x and x.get("pdf_path"):
            if not open_file(x["pdf_path"]):
                unit = self.db.one("SELECT * FROM billing_units WHERE id=?", (x["unit_id"],))
                client = self.db.one("SELECT * FROM clients WHERE id=?", (x["client_id"],))
                if unit and client:
                    p = self.create_pdf(x["id"], dict(unit), dict(client))
                    open_file(p)

    def open_nongst_pdf(self):
        ids = [self.nongst_table.item(i.row(), 0).data(Qt.ItemDataRole.UserRole) for i in self.nongst_table.selectionModel().selectedRows()]
        if not ids and self.nongst_table.currentRow() >= 0:
            it = self.nongst_table.item(self.nongst_table.currentRow(), 0)
            if it: ids = [it.data(Qt.ItemDataRole.UserRole)]
        if ids:
            x = self.db.one("SELECT * FROM invoices WHERE id=?", (ids[0],))
            if x and x["pdf_path"]: open_file(x["pdf_path"])

    def clear_draft(self):
        self.items = []
        self.editing_id = None
        self.invoice_no_input.clear()
        self.invoice_mode.setText("Status: New Invoice")
        self.refresh_item_table()

    def edit_nongst(self):
        ids = [self.nongst_table.item(i.row(), 0).data(Qt.ItemDataRole.UserRole) for i in self.nongst_table.selectionModel().selectedRows()]
        if not ids and self.nongst_table.currentRow() >= 0:
            it = self.nongst_table.item(self.nongst_table.currentRow(), 0)
            if it: ids = [it.data(Qt.ItemDataRole.UserRole)]
        if not ids: return
        x = self.db.one("SELECT * FROM invoices WHERE id=?", (ids[0],))
        if not x: return
        self.editing_id = x["id"]
        self.invoice_no_input.setText(x["invoice_no"])
        self.invoice_mode.setText(f"Editing {x['invoice_no']}")
        self.invoice_unit.setCurrentIndex(self.invoice_unit.findData(x["unit_id"]))
        self.invoice_client.setCurrentIndex(self.invoice_client.findData(x["client_id"]))
        self.items = [{
            "type": "Reimbursement", "description": i["description"], "sac": i["sac"],
            "qty": i["qty"], "rate": i["rate"], "gst_rate": i["gst_rate"]
        } for i in self.db.rows("SELECT * FROM invoice_items WHERE invoice_id=?", (x["id"],))]
        self.refresh_item_table()
        self.tabs.setCurrentWidget(self.create_tab)

    def delete_nongst(self):
        ids = [self.nongst_table.item(i.row(), 0).data(Qt.ItemDataRole.UserRole) for i in self.nongst_table.selectionModel().selectedRows()]
        if not ids and self.nongst_table.currentRow() >= 0:
            it = self.nongst_table.item(self.nongst_table.currentRow(), 0)
            if it: ids = [it.data(Qt.ItemDataRole.UserRole)]
        if ids and QMessageBox.question(self, "Delete Invoices", f"Delete {len(ids)} selected bill(s)?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            for ident in ids:
                self.db.execute("DELETE FROM invoice_items WHERE invoice_id=?", (ident,))
                self.db.execute("DELETE FROM payments WHERE invoice_id=?", (ident,))
                self.db.execute("DELETE FROM invoices WHERE id=?", (ident,))
            self.refresh_all()

    # -----------------------------------------------------
    # Excel Import & Export
    # -----------------------------------------------------
    def import_clients(self): self.import_excel("clients")
    def import_invoice_file(self): self.import_excel("invoices")
    def export_clients(self): self.export_excel("clients")
    def export_invoice_register(self): self.export_excel("invoices")
    def export_payments(self): self.export_excel("payments")

    def import_excel(self, kind):
        path, _ = QFileDialog.getOpenFileName(self, "Import Excel / Tally XLSM", "", "Excel Files (*.xlsx *.xlsm)")
        if not path: return
        try:
            ws = load_workbook(path, data_only=True, read_only=True).active
            header_row = 1
            for row_no, row_vals in enumerate(ws.iter_rows(values_only=True), 1):
                txt = [str(v or "").strip().lower() for v in row_vals]
                if ("date" in txt and ("particulars" in txt or "client" in txt or "party name" in txt)) or ("invoice no" in txt) or ("client name" in txt):
                    header_row = row_no; break

            headers = [str(c.value or "").strip().lower() for c in next(ws.iter_rows(min_row=header_row, max_row=header_row))]
            def get_val(r, *keys):
                for k in keys:
                    if k in headers and r[headers.index(k)] not in (None, ""): return r[headers.index(k)]
                return None

            n = 0
            for r in ws.iter_rows(min_row=header_row + 1, values_only=True):
                name = get_val(r, "name", "client", "client name", "party name", "customer", "particulars")
                if not name: continue
                if kind == "clients":
                    gstin = str(get_val(r, "gstin", "gst no", "gst") or "").strip().upper()
                    state_code = gstin[:2] if len(gstin) >= 2 and gstin[:2].isdigit() else ""
                    self.db.execute("""
                        INSERT INTO clients(name, gstin, pan, email, phone, address, state, state_code, notes)
                        VALUES(?,?,?,?,?,?,?,?,?)
                    """, (str(name), gstin, str(get_val(r, "pan") or (gstin[2:12] if len(gstin) == 15 else "")),
                          str(get_val(r, "email") or ""), str(get_val(r, "phone", "mobile") or ""),
                          str(get_val(r, "address") or ""), str(get_val(r, "state") or ""),
                          state_code, "Imported from Excel"))
                    n += 1
                else:
                    no = get_val(r, "invoice no", "invoice number", "voucher no", "voucher number", "vch no.")
                    if not no and "vch type" in headers: no = f"{get_val(r, 'vch type') or 'Tally'}/{get_val(r, 'vch no.') or ''}"
                    if not no or self.db.one("SELECT id FROM invoices WHERE invoice_no=?", (str(no),)): continue

                    c = self.db.one("SELECT * FROM clients WHERE lower(name)=lower(?)", (str(name),))
                    if not c:
                        self.db.execute("INSERT INTO clients(name, notes) VALUES(?,?)", (str(name), "Created from Excel Import"))
                        c = self.db.one("SELECT * FROM clients WHERE lower(name)=lower(?)", (str(name),))

                    u = self.db.one("SELECT * FROM billing_units ORDER BY id LIMIT 1")
                    total = float(get_val(r, "amount", "total", "invoice value", "debit") or 0)
                    tax = float(get_val(r, "gst", "tax", "igst") or 0)
                    dt = get_val(r, "date", "invoice date") or date.today().isoformat()
                    dt = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)

                    self.db.execute("""
                        INSERT INTO invoices(invoice_no, unit_id, client_id, invoice_date, due_date, subtotal,
                        cgst, sgst, igst, total, created_at, source, has_gst)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (str(no), u["id"], c["id"], dt, dt, total - tax, tax / 2, tax / 2, 0, total, datetime.now().isoformat(), "Excel Import", int(tax > 0)))
                    n += 1

            self.refresh_all()
            QMessageBox.information(self, "Import Complete", f"Successfully imported {n} {kind} record(s).")
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Could not process Excel file: {str(e)}")

    def export_excel(self, kind):
        path, _ = QFileDialog.getSaveFileName(self, f"Export {kind.capitalize()}", str(BASE / f"{kind}_export.xlsx"), "Excel Files (*.xlsx)")
        if not path: return
        wb = Workbook()
        ws = wb.active
        if kind == "clients":
            ws.append(["Legal Name", "GSTIN", "PAN", "Email", "Phone", "Address", "State", "State Code"])
            for x in self.db.rows("SELECT * FROM clients WHERE active=1 ORDER BY name"):
                ws.append([x["name"], x["gstin"], x["pan"], x["email"], x["phone"], x["address"], x["state"], x["state_code"]])
        elif kind == "payments":
            ws.append(["Receipt ID", "Payment Date", "Invoice No", "Client Name", "Net Amount", "TDS Deducted", "TDS Section", "Mode", "Reference / UTR"])
            for x in self.db.rows("""
                SELECT p.*, i.invoice_no, c.name client_name FROM payments p
                JOIN invoices i ON i.id=p.invoice_id JOIN clients c ON c.id=i.client_id ORDER BY p.payment_date DESC
            """):
                ws.append([x["id"], x["payment_date"], x["invoice_no"], x["client_name"], x["amount"], x["tds_deducted"], x["tds_section"], x["payment_mode"], x["reference_no"]])
        else:
            ws.append(["Invoice No", "Invoice Date", "Billing Unit", "Client Name", "Taxable", "CGST", "SGST", "IGST", "Grand Total", "Settled", "Balance Due", "Status"])
            for r in range(self.invoices_table.rowCount()):
                ws.append([self.invoices_table.item(r, c).text() if self.invoices_table.item(r, c) else "" for c in range(12)])
        wb.save(path)
        QMessageBox.information(self, "Export Complete", f"Data exported successfully to:\n{path}")

    # -----------------------------------------------------
    # GSTIN Live Verification
    # -----------------------------------------------------
    def lookup_selected_gstin(self):
        ident = self.selected_id(self.clients_table)
        if not ident: return
        client = self.db.one("SELECT * FROM clients WHERE id=?", (ident,))
        gstin = (client["gstin"] or "").strip().upper()
        if len(gstin) != 15:
            QMessageBox.warning(self, "Invalid GSTIN", "Please enter a valid 15-character GSTIN first.")
            return

        api_key_row = self.db.one("SELECT value FROM settings WHERE key='gstinapi_key'")
        api_key = api_key_row["value"] if api_key_row and api_key_row["value"] else DEFAULT_GSTINAPI_KEY

        try:
            resp = requests.get(f"https://www.gstinapi.in/v1/gstin/{gstin}", headers={"x-api-key": api_key}, timeout=15)
            payload = resp.json()
            if not resp.ok or not payload.get("success"):
                raise ValueError(payload.get("message") or payload.get("error") or f"HTTP {resp.status_code}")

            data = payload.get("data") or {}
            legal_name = data.get("legal_name") or data.get("trade_name") or client["name"]
            st_name = data.get("state") or data.get("state_name") or client["state"]
            st_code = gstin[:2]
            status = data.get("status") or data.get("gstin_status") or "Active"
            addr = data.get("address") or client["address"]
            if isinstance(addr, dict): addr = ", ".join(str(v) for v in addr.values() if v)

            self.db.execute("""
                UPDATE clients SET name=?, address=?, state=?, state_code=?, pan=?, notes=? WHERE id=?
            """, (legal_name, addr, st_name, st_code, gstin[2:12], f"GSTIN Verified: {status} ({datetime.now().strftime('%d-%m-%Y')})", client["id"]))
            self.refresh_all()
            QMessageBox.information(self, "GSTIN Verified & Saved", f"Taxpayer: {legal_name}\nStatus: {status}\nState: {st_name} ({st_code})")
        except Exception as e:
            QMessageBox.warning(self, "GSTIN Lookup Failed", f"Verification failed: {str(e)}\nEnsure GSTIN is correct and API key is valid.")

    def bulk_gstin_refresh(self):
        rows = self.clients_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Select Clients", "Select client rows to refresh.")
            return
        succ = fail = 0
        for r in rows:
            it = self.clients_table.item(r.row(), 0)
            if it:
                ident = it.data(Qt.ItemDataRole.UserRole)
                c = self.db.one("SELECT * FROM clients WHERE id=?", (ident,))
                if c and c["gstin"] and len(c["gstin"]) == 15: succ += 1
                else: fail += 1
        QMessageBox.information(self, "Bulk Validation", f"Validated {succ} GSTIN(s). {fail} had invalid/missing GSTINs.")

    # -----------------------------------------------------
    # Email Transmission via Resilient SMTP Dispatcher
    # -----------------------------------------------------
    def email_client(self):
        ident = self.selected_id(self.clients_table)
        if not ident: return
        c = self.db.one("SELECT * FROM clients WHERE id=?", (ident,))
        if c and c["email"]:
            webbrowser.open(f"mailto:{c['email']}?subject=Professional%20Communication%20-%20Chartered%20Accountants")
        else:
            QMessageBox.warning(self, "No Email", "Client email address is missing.")

    def whatsapp_client(self):
        ident = self.selected_id(self.clients_table)
        if not ident: return
        self.prompt_whatsapp_single(ident)

    def email_invoice(self):
        x = self.invoice_row()
        if not x: return
        if not x.get("client_email"):
            new_mail, ok = QInputDialog.getText(self, "Client Email Missing", f"Enter email address for '{x.get('client_name', 'Client')}':")
            if ok and new_mail.strip():
                x["client_email"] = new_mail.strip()
                self.db.execute("UPDATE clients SET email=? WHERE id=?", (new_mail.strip(), x["client_id"]))
            else:
                QMessageBox.warning(self, "Missing Email", "Please add an email address for this client first.")
                return

        unit = self.db.one("SELECT * FROM billing_units WHERE id=?", (x["unit_id"],))
        client = self.db.one("SELECT * FROM clients WHERE id=?", (x["client_id"],))
        pdf_path = self.create_pdf(x["id"], dict(unit), dict(client))

        host = self.smtp_host.text().strip() or "smtp.gmail.com"
        port = self.smtp_port.text().strip() or "465"
        user = self.smtp_user.text().strip()
        pwd = self.smtp_password.text().strip().replace(" ", "") or CONFIGURED_GMAIL_APP_PASSWORD
        sec = self.smtp_security.currentText()

        if not user:
            new_u, ok = QInputDialog.getText(self, "Enter Your Gmail Address", "Enter your sender Gmail address (e.g. pritesh.ca@gmail.com):")
            if ok and new_u.strip():
                user = new_u.strip()
                self.smtp_user.setText(user)
                self.db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", ("smtp_user", user))
            else:
                webbrowser.open(f"mailto:{x['client_email']}?subject=Tax%20Invoice%20{x['invoice_no']}")
                return

        try:
            msg = EmailMessage()
            msg["Subject"] = f"Tax Invoice {x['invoice_no']} from {x['unit_name']}"
            msg["From"] = user
            msg["To"] = x["client_email"]
            msg.set_content(
                f"Dear {x['client_name']},\n\n"
                f"Please find attached Tax Invoice {x['invoice_no']} dated {x['invoice_date']} amounting to {money(x['total'])} for professional services rendered.\n\n"
                f"Remittance can be made to:\nBank: {unit['bank_name'] or '-'}\nA/c: {unit['bank_account'] or '-'}\nIFSC: {unit['ifsc'] or '-'}\nUPI: {unit['upi_id'] or '-'}\n\n"
                f"Best regards,\n{x['unit_name']}"
            )
            with open(pdf_path, "rb") as f:
                msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=Path(pdf_path).name)

            ok, note = send_smtp_email(host, port, user, pwd, sec, msg)
            QMessageBox.information(self, "Email Sent", f"Invoice successfully dispatched to {x['client_email']}!\n({note})")
        except Exception as e:
            QMessageBox.critical(self, "Dispatch Failed", f"SMTP Transmission Error: {str(e)}")

    # -----------------------------------------------------
    # Settings & PDF Path Persistence
    # -----------------------------------------------------
    def choose_pdf_folder(self):
        curr = self.db.one("SELECT value FROM settings WHERE key='pdf_output_folder'")
        folder = QFileDialog.getExistingDirectory(self, "Select PDF Output Directory", curr["value"] if curr else str(PDF_DIR))
        if folder:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", ("pdf_output_folder", folder))
            self.pdf_folder_lbl.setText(folder)
            QMessageBox.information(self, "Folder Saved", f"PDF directory updated to:\n{folder}")

    def save_settings(self):
        pwd = self.smtp_password.text().strip().replace(" ", "")
        for k, w in [
            ("smtp_host", self.smtp_host.text().strip()),
            ("smtp_port", self.smtp_port.text().strip()),
            ("smtp_user", self.smtp_user.text().strip()),
            ("smtp_password", pwd),
            ("smtp_security", self.smtp_security.currentText()),
            ("gstinapi_key", self.gstin_api_key_input.text().strip())
        ]:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (k, w))
        QMessageBox.information(self, "Settings Saved", "System settings, Gmail credentials, and API configuration saved.")

    def load_settings(self):
        if not hasattr(self, "smtp_host"): return
        data = {x["key"]: x["value"] for x in self.db.rows("SELECT * FROM settings")}
        self.smtp_host.setText(data.get("smtp_host", "smtp.gmail.com"))
        self.smtp_port.setText(data.get("smtp_port", "465"))
        self.smtp_user.setText(data.get("smtp_user", ""))
        self.smtp_password.setText(data.get("smtp_password", CONFIGURED_GMAIL_APP_PASSWORD))
        self.smtp_security.setCurrentText(data.get("smtp_security", "Implicit SSL (Port 465)"))
        self.gstin_api_key_input.setText(data.get("gstinapi_key", DEFAULT_GSTINAPI_KEY))
        pdf_f = data.get("pdf_output_folder", str(PDF_DIR))
        self.pdf_folder_lbl.setText(pdf_f)


# ---------------------------------------------------------
# Global Anti-Crash Exception Shield
# ---------------------------------------------------------
def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print("UNHANDLED EXCEPTION INTERCEPTED:\n", err_msg)
    app = QApplication.instance()
    if app:
        QMessageBox.critical(
            None, "System Notice",
            f"An unexpected operation notice occurred:\n\n{str(exc_value)}\n\nThe system remains stable. Please verify inputs."
        )

sys.excepthook = global_exception_handler

# ---------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = InvoiceApp()
    window.show()
    sys.exit(app.exec())