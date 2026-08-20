"""
config.py
---------
Fixed firm details used across the application (invoice header/footer, PDF
generation, etc.). These values are sourced from the firm's sample invoice.

If any of these details ever change (address, bank account, contact number,
etc.), this is the ONLY file that needs to be edited -- every screen and the
PDF generator reads from here.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Base directories (auto-created at runtime by main.py / database.py)
# ---------------------------------------------------------------------------
# When running as a PyInstaller-built .exe (--onefile or --onedir), the app
# is unpacked into a temporary folder at startup (sys._MEIPASS) and __file__
# points there, NOT to the folder the .exe actually lives in -- that temp
# folder is deleted when the app closes. So when frozen, anchor BASE_DIR to
# the real .exe's own folder instead, so database/ and invoices_pdf/ persist
# next to the .exe as intended.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
INVOICES_PDF_DIR = os.path.join(BASE_DIR, "invoices_pdf")
DATABASE_FILE = os.path.join(DATABASE_DIR, "invoices.json")
USERS_FILE = os.path.join(DATABASE_DIR, "users.json")

# ---------------------------------------------------------------------------
# Firm identity (header)
# ---------------------------------------------------------------------------
FIRM_NAME = "Lochan & Co"
FIRM_TAGLINE = "Chartered Accountants"

# Left block of header
FIRM_OFFICE_LABEL = "Noida Office:"
FIRM_ADDRESS_LINES = [
    "Suite 415, A-46, Sector-67,",
    "Noida, Distt. G.B. Nagar,",
    "U.P, 201301",
]

# Right block of header
FIRM_MOBILE_NUMBERS = "9810156292, 8800595945"
FIRM_EMAILS = ["amit.bansal@lochanco.com", "directtaxmaven@lochanco.com"]
FIRM_WEBSITE = "www.lochanco.com"

# Firm's own statutory details (printed near Dated/Invoice No. block)
FIRM_PAN = "AACFL4183D"
FIRM_GSTIN = "09AACFL4183D1ZF"
FIRM_STATE_NAME = "Uttar Pradesh"
FIRM_STATE_CODE = "09"

# ---------------------------------------------------------------------------
# Invoice numbering
# ---------------------------------------------------------------------------
INVOICE_PREFIX = "LC"  # LC/26-27/Aug/01

# ---------------------------------------------------------------------------
# Banking details (footer)
# ---------------------------------------------------------------------------
BANK_ACCOUNT_NAME = "Lochan and Company"
BANK_NAME = "HDFC Bank"
BANK_ACCOUNT_NO = "99909810156292"
BANK_ADDRESS = "Sector-26, Noida, UP- 201301"
BANK_IFSC = "HDFC0000651"
BANK_UPI_ID = ""  # not provided in sample; leave blank / editable later

# ---------------------------------------------------------------------------
# Terms & Conditions (footer) -- verbatim from firm's sample invoice
# ---------------------------------------------------------------------------
TERMS_AND_CONDITIONS = [
    "This bill is payable on receipt by Cheque/ Wire transfer in favor of "
    "Lochan and Company. In case payment is made by electronic fund "
    "transfer, please send details to accountsmaven@lochanco.com",
    "Please make payment within 15 days of receipt of this invoice.",
    "This invoice for professional charges is due from the date of receipt. "
    "In case of any clarification, please contact us within 15 days from "
    "the receipt of invoice, the payment of this invoice shall be made "
    "within 30 days of its presentation. Lochan & Co. is committed to "
    "provide the qualitative and timely services to its clients and "
    "expects you to make the payment in time.",
    "TDS certificate, if applicable, is to be sent to the above address.",
    "We are a MSME registered firm vide Regn. No. DL02E0008168",
]

SIGNATORY_LINE_1 = "Authorized Signatory"
SIGNATORY_LINE_2 = FIRM_NAME
SIGNATORY_LINE_3 = FIRM_TAGLINE

# ---------------------------------------------------------------------------
# Theme colours (White / Blue / Red professional theme)
# ---------------------------------------------------------------------------
COLOR_PRIMARY_BLUE = "#0B3D91"
COLOR_ACCENT_RED = "#C1272D"
COLOR_WHITE = "#FFFFFF"
COLOR_LIGHT_GREY = "#F2F4F7"
COLOR_BORDER_GREY = "#D0D5DD"
COLOR_TEXT_DARK = "#1D2939"

# ---------------------------------------------------------------------------
# Business rules
# ---------------------------------------------------------------------------
ROUND_OFF_ENABLED = True  # round Grand Total to nearest rupee
DEFAULT_GST_RATES = [0, 5, 12, 18, 28]

# ---------------------------------------------------------------------------
# Tally Prime auto-sync
# ---------------------------------------------------------------------------
# Set to True only after Tally's HTTP/XML gateway is enabled (Gateway of
# Tally -> F11 -> Connectivity -> "Client/Server configuration" -> set
# "TallyPrime acts as" to Server, and note the port -- default 9000) and
# TALLY_COMPANY_NAME below has been verified against your actual Tally
# company. See README section 8 for full setup steps and important
# caveats before relying on this with real invoices.
TALLY_SYNC_ENABLED = False

TALLY_HOST = "localhost"
TALLY_PORT = 9000

# EDIT THIS to match the company exactly as it appears in Tally Prime's
# company list (Gateway of Tally, top-left). This is a placeholder --
# verify/correct it before enabling sync.
TALLY_COMPANY_NAME = "Lochan & Co"

TALLY_VOUCHER_TYPE = "Sales"
TALLY_SALES_LEDGER = "Sales"

# Rate-specific GST ledger names. {rate} is replaced with the numeric rate
# (e.g. "9", "18", "6"). CGST/SGST use the half-rate (so an 18% item posts
# to the "...9%" ledgers below); IGST uses the full rate.
TALLY_CGST_LEDGER_TEMPLATE = "Output CGST {rate}%"
TALLY_SGST_LEDGER_TEMPLATE = "Output SGST {rate}%"
TALLY_IGST_LEDGER_TEMPLATE = "Output IGST {rate}%"

# New customers are auto-created as a Tally ledger under this group if no
# matching ledger already exists.
TALLY_PARTY_GROUP = "Sundry Debtors"

# When checking whether a customer already has a Tally ledger, ignore these
# suffixes/variations so e.g. "ABC Industries Pvt Ltd" and "ABC Industries
# Private Limited" are treated as the same party instead of creating a
# near-duplicate ledger.
TALLY_NAME_SUFFIXES_TO_IGNORE = [
    "private limited", "pvt. ltd.", "pvt ltd.", "pvt ltd", "p. ltd.",
    "p ltd", "(p) ltd", "limited", "ltd.", "ltd", "llp",
]

# No dedicated Round Off ledger is used (per firm's instruction): the party
# ledger is debited with the exact pre-rounding total so the voucher stays
# balanced without an extra posting. The rounded figure is still what's
# shown/printed on the invoice PDF.
TALLY_POST_EXACT_UNROUNDED_TOTAL = True
