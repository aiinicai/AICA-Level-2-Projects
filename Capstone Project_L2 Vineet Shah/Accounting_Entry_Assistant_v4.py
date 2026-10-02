"""Accounting Entry Assistant v4 — local, offline, standard-library desktop app.

Run: python Accounting_Entry_Assistant_v4.py
Data: ~/Accounting_Entry_Assistant_v2/ (journal.sqlite3 and settings.json).
Enter a complete plain-language transaction and confirm any missing tax facts.
"""

from __future__ import annotations

import datetime as dt
import calendar
import json
import re
import sqlite3
import tkinter as tk
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED

APP = "Accounting Entry Assistant v4"
DATA_DIR = Path.home() / "Accounting_Entry_Assistant_v2"
DB_PATH = DATA_DIR / "journal.sqlite3"
SETTINGS_PATH = DATA_DIR / "settings.json"
CENT = Decimal("0.01")


def money(value):
    try:
        d = Decimal(str(value).replace(",", "").replace("₹", "").strip())
        if not d.is_finite():
            raise ValueError("Amount must be finite")
        return d.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Enter a valid amount in rupees.") from exc


def amount_text(value):
    return f"₹{value:,.2f}"


def tax_split(base, rate, inclusive, interstate):
    if rate < 0 or rate > 100:
        raise ValueError("GST rate must be between 0 and 100%.")
    taxable = money(base / (Decimal(1) + rate / 100)) if inclusive else money(base)
    gross = money(base) if inclusive else money(taxable * (Decimal(1) + rate / 100))
    tax = gross - taxable
    if interstate:
        return taxable, gross, {"IGST": tax}
    cgst = money(tax / 2)
    return taxable, gross, {"CGST": cgst, "SGST": tax - cgst}


# Income Tax Department, Depreciation rates, AY 2018-19 onwards (WDV).
# https://www.incometaxindia.gov.in/w/depreciation-rates
DEPRECIATION_RATES = {
    "Computer / computer software": Decimal("40"),
    "Furniture / electrical fittings": Decimal("10"),
    "General plant / machinery": Decimal("15"),
    "Motor car (not on hire)": Decimal("15"),
    "Motor bus / lorry / taxi on hire": Decimal("30"),
    "Residential building": Decimal("5"),
    "Other building": Decimal("10"),
    "Intangible rights (excluding goodwill)": Decimal("25"),
}


def classify_depreciation_asset(description):
    s = description.lower()
    if re.search(r"\b(?:goodwill|land|leased software|software subscription|cloud subscription)\b", s):
        return None
    if re.search(r"\b(?:computer|laptop|desktop|server|computer software)\b", s):
        return "Computer / computer software"
    if re.search(r"\b(?:furniture|chair|desk|electrical fittings?|wiring|switchgear)\b", s):
        return "Furniture / electrical fittings"
    if re.search(r"\b(?:residential|dwelling)\b.*\b(?:building|premises|flat)\b|\b(?:building|premises|flat)\b.*\b(?:residential|dwelling)\b", s):
        return "Residential building"
    if re.search(r"\b(?:office|commercial|factory)\s+(?:building|premises)\b", s):
        return "Other building"
    if re.search(r"\b(?:motor\s+)?(?:bus|lorry|taxi)\b", s) and re.search(r"\b(?:on hire|running on hire|hire business)\b", s):
        return "Motor bus / lorry / taxi on hire"
    if re.search(r"\b(?:motor car|car)\b", s):
        return "Motor car (not on hire)" if not re.search(r"\bhire\b", s) else None
    if re.search(r"\b(?:patent|copyright|trademark|franchise|licen[cs]e|know-how)\b", s):
        return "Intangible rights (excluding goodwill)"
    if re.search(r"\b(?:machinery|machine|plant|equipment)\b", s):
        return "General plant / machinery" if not re.search(r"\b(?:pollution|energy saving|renewable|solar|medical|semiconductor|mould|water treatment)\b", s) else None
    return None


def tax_depreciation(description, amount, journal_date, asset_class="", basis="Opening WDV", put_to_use=""):
    asset = asset_class or classify_depreciation_asset(description)
    if asset not in DEPRECIATION_RATES:
        raise ValueError("Choose a verified asset class in Review details; special assets need a separately verified rate.")
    wdv = require_positive(money(amount))
    date = dt.date.fromisoformat(journal_date)
    start = dt.date(date.year if date.month >= 4 else date.year - 1, 4, 1)
    end = dt.date(start.year + 1, 3, 31)
    rate = DEPRECIATION_RATES[asset]
    if basis == "New asset cost":
        if not put_to_use.strip():
            raise ValueError("Enter the date first put to use (DD/MM/YYYY) for a new asset.")
        used = dt.datetime.strptime(put_to_use.strip(), "%d/%m/%Y").date()
        if not start <= used <= end or used > date:
            raise ValueError("Date first put to use must be within this tax year and on or before the entry date.")
        if (end - used).days + 1 < 180:
            rate /= 2
    elif basis != "Opening WDV":
        raise ValueError("Choose Opening WDV or New asset cost for depreciation basis.")
    value = money(wdv * rate / 100)
    return asset, rate, value, wdv - value


@dataclass
class Line:
    ledger: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")


def dr(lines, ledger, value):
    if value > 0:
        lines.append(Line(ledger, value, Decimal(0)))


def cr(lines, ledger, value):
    if value > 0:
        lines.append(Line(ledger, Decimal(0), value))


def validate(lines):
    if len(lines) < 2:
        raise ValueError("At least two nonzero journal lines are required.")
    for line in lines:
        if not line.ledger.strip() or line.debit < 0 or line.credit < 0:
            raise ValueError("Each line needs a ledger and nonnegative amount.")
        if bool(line.debit) == bool(line.credit):
            raise ValueError("A line must have either a debit or credit amount.")
        if line.debit != money(line.debit) or line.credit != money(line.credit):
            raise ValueError("Journal amounts must have at most two decimal places.")
    debit = sum((x.debit for x in lines), Decimal(0))
    credit = sum((x.credit for x in lines), Decimal(0))
    if debit != credit:
        raise ValueError(f"Entry is not balanced: debit {amount_text(debit)}, credit {amount_text(credit)}.")
    return debit


DEFAULT_SETTINGS = {
    "gst_rates": ["0", "5", "12", "18", "28"],
    "tds_rates": ["0", "1", "2", "10"],
    "ledgers": {
        "bank": "Bank A/c", "cash": "Cash A/c", "purchase": "Purchases A/c",
        "sales": "Sales A/c", "expense": "Expense A/c", "asset": "Fixed Assets A/c",
        "input_igst": "Input IGST A/c", "input_cgst": "Input CGST A/c",
        "input_sgst": "Input SGST A/c", "output_igst": "Output IGST A/c",
        "output_cgst": "Output CGST A/c", "output_sgst": "Output SGST A/c",
        "rcm_igst": "RCM IGST Payable A/c", "rcm_cgst": "RCM CGST Payable A/c",
        "rcm_sgst": "RCM SGST Payable A/c", "rcm_pending_igst": "RCM IGST Pending ITC A/c",
        "rcm_pending_cgst": "RCM CGST Pending ITC A/c",
        "rcm_pending_sgst": "RCM SGST Pending ITC A/c",
        "tds_payable": "TDS Payable A/c", "tds_receivable": "TDS Receivable A/c",
        "advance_paid": "Advance to Supplier A/c", "advance_received": "Advance from Customer A/c",
        "accrued": "Accrued Expenses A/c", "loan": "Loan Payable A/c",
        "depreciation": "Depreciation Expense A/c", "accum_depreciation": "Accumulated Depreciation A/c",
    },
}


def load_settings():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        SETTINGS_PATH.write_text(json.dumps(DEFAULT_SETTINGS, indent=2), encoding="utf-8")
    data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data.get("ledgers"), dict) or not all(
        isinstance(data["ledgers"].get(key), str) and data["ledgers"][key].strip()
        for key in DEFAULT_SETTINGS["ledgers"]
    ):
        raise ValueError("settings.json needs every ledger key listed in the default configuration.")
    return data


TYPES = [
    "Expense", "Purchase", "Fixed asset purchase", "Sale", "Accrued expense",
    "Pay supplier", "Receive from customer", "Pay accrued expense",
    "Advance to supplier", "Advance from customer", "Adjust supplier advance",
    "Adjust customer advance", "Loan received", "Loan principal repaid",
    "Loan interest paid", "Depreciation", "RCM assessment", "RCM tax payment",
    "RCM ITC claim", "RCM ITC disallowed", "Manual compound journal",
]
INVOICE_TYPES = {"Expense", "Purchase", "Fixed asset purchase", "Sale", "Accrued expense"}
PARTY_TYPES = INVOICE_TYPES | {"Pay supplier", "Receive from customer", "Advance to supplier",
    "Advance from customer", "Adjust supplier advance", "Adjust customer advance", "Loan received",
    "Loan principal repaid", "RCM assessment"}


def party_ledger(party):
    party = party.strip()
    if not party:
        raise ValueError("Enter the supplier, customer, or lender name.")
    return f"Party: {party}"


def require_positive(value):
    if value <= 0:
        raise ValueError("Amount must be greater than zero.")
    return value


def infer_type(description):
    s = description.lower()
    patterns = [
        (r"depreciation", "Depreciation"),
        (r"rcm.*(itc|credit)", "RCM ITC claim"),
        (r"rcm.*(pay|deposit)", "RCM tax payment"),
        (r"rcm", "RCM assessment"),
        (r"(repay|repayment).*(loan|principal)", "Loan principal repaid"),
        (r"(loan|borrow).*(receiv|taken)", "Loan received"),
        (r"(advanc).*(receiv|customer)", "Advance from customer"),
        (r"advanc", "Advance to supplier"),
        (r"(paid|pay).*(supplier|creditor)", "Pay supplier"),
        (r"(receiv|customer paid|debtor paid)", "Receive from customer"),
        (r"(sale|sold|invoice to customer)", "Sale"),
        (r"(fixed asset|machinery|laptop|computer equipment)", "Fixed asset purchase"),
        (r"(purchas|bought)", "Purchase"),
        (r"(accru|outstanding)", "Accrued expense"),
        (r"(interest paid|loan interest)", "Loan interest paid"),
        (r"(fee|rent|expense|paid|professional service|consultancy|consulting|technical service|commission|brokerage|contractor|contract work|job work|labour charges|audit)", "Expense"),
    ]
    for pattern, result in patterns:
        if re.search(pattern, s):
            return result
    return None


def build(p, settings):
    kind = p["type"]
    L = settings["ledgers"]
    lines = []
    details = []
    value = Decimal(0) if kind == "Manual compound journal" else require_positive(money(p["amount"]))
    party = party_ledger(p["party"]) if kind in PARTY_TYPES else ""
    bank = L["cash"] if p["payment"] == "Cash" else L["bank"]
    account = p["ledger"].strip()

    if kind == "Manual compound journal":
        for row in p["manual"].strip().splitlines():
            cells = [x.strip() for x in row.split("|")]
            if len(cells) != 3:
                raise ValueError("Manual rows must read: Ledger | Debit | Credit")
            ledger, debit, credit = cells
            lines.append(Line(ledger, money(debit or "0"), money(credit or "0")))
        validate(lines)
        return lines, ["Manual journal; review each ledger and supporting document."]

    if kind in INVOICE_TYPES:
        if not account:
            key = {"Expense": "expense", "Purchase": "purchase", "Sale": "sales",
                   "Fixed asset purchase": "asset", "Accrued expense": "expense"}[kind]
            account = L[key]
        rate = Decimal(str(p["gst_rate"] or "0"))
        tds_rate = Decimal(str(p["tds_rate"] or "0"))
        if not rate.is_finite() or not tds_rate.is_finite() or not 0 <= tds_rate <= 100:
            raise ValueError("Enter valid GST and TDS rates (0–100%).")
        if kind == "Accrued expense" and rate:
            raise ValueError("Do not estimate GST on an uninvoiced accrual; enter GST when the invoice is booked.")
        taxable, gross, taxes = tax_split(value, rate, p["inclusive"], p["interstate"])
        if kind == "Sale" and p["rcm"]:
            raise ValueError("RCM supply treatment requires a separate reviewed workflow; do not post output GST here.")
        if p["rcm"]:
            raise ValueError("For reverse charge, book the supplier invoice with GST 0, then use RCM assessment.")
        if kind == "Accrued expense":
            dr(lines, account, value)
            withheld = money(p["tds_amount"]) if p.get("tds_amount") is not None else money(value * tds_rate / 100)
            if withheld > value:
                raise ValueError("TDS cannot exceed the accrued expense.")
            if withheld:
                cr(lines, L["tds_payable"], withheld)
                details.append(f"TDS {p['tds_section']}: {amount_text(withheld)} on accrual.")
            cr(lines, L["accrued"], value - withheld)
        else:
            tax_total = gross - taxable
            eligible = p["itc"] == "Eligible"
            if kind == "Sale":
                cr(lines, account, taxable)
                for tax, portion in taxes.items():
                    cr(lines, L[f"output_{tax.lower()}"], portion)
            else:
                dr(lines, account, taxable + (Decimal(0) if eligible else tax_total))
                if eligible:
                    for tax, portion in taxes.items():
                        dr(lines, L[f"input_{tax.lower()}"], portion)
                elif tax_total:
                    details.append("GST included in cost/expense; check capitalization and ITC eligibility.")
            tds_base = money(p["tds_base"]) if p["tds_base"].strip() else taxable
            if tds_base < 0 or (tds_base > gross and tds_rate):
                raise ValueError("TDS base must be between zero and invoice gross amount.")
            tds = money(p["tds_amount"]) if p.get("tds_amount") is not None else money(tds_base * tds_rate / 100)
            if tds > gross:
                raise ValueError("TDS cannot exceed gross invoice amount.")
            if tds:
                if not p["tds_section"].strip():
                    raise ValueError("Enter and verify the TDS section when TDS is applied.")
                if kind == "Sale":
                    dr(lines, L["tds_receivable"], tds)
                    details.append("Customer TDS receivable shown; verify withholding evidence.")
                else:
                    cr(lines, L["tds_payable"], tds)
                details.append(f"TDS {p['tds_section'].strip()}; current invoice base {amount_text(tds_base)}; deduction {amount_text(tds)}.")
            settlement = gross - tds
            if kind == "Sale":
                dr(lines, bank if p["payment"] != "Credit" else party, settlement)
            else:
                cr(lines, bank if p["payment"] != "Credit" else party, settlement)
            details.append(f"Taxable {amount_text(taxable)}; GST {amount_text(tax_total)}; gross {amount_text(gross)}.")

    elif kind == "Pay supplier":
        dr(lines, party, value); cr(lines, bank, value)
    elif kind == "Receive from customer":
        dr(lines, bank, value); cr(lines, party, value)
    elif kind == "Pay accrued expense":
        dr(lines, L["accrued"], value); cr(lines, bank, value)
    elif kind == "Advance to supplier":
        dr(lines, L["advance_paid"] + " : " + p["party"].strip(), value); cr(lines, bank, value)
        details.append("Tax on advances requires a separate supply-specific review.")
    elif kind == "Advance from customer":
        dr(lines, bank, value); cr(lines, L["advance_received"] + " : " + p["party"].strip(), value)
        details.append("Review GST timing and nature of supply for customer advance.")
    elif kind == "Adjust supplier advance":
        dr(lines, party, value); cr(lines, L["advance_paid"] + " : " + p["party"].strip(), value)
    elif kind == "Adjust customer advance":
        dr(lines, L["advance_received"] + " : " + p["party"].strip(), value); cr(lines, party, value)
    elif kind == "Loan received":
        dr(lines, bank, value); cr(lines, L["loan"] + " : " + p["party"].strip(), value)
    elif kind == "Loan principal repaid":
        dr(lines, L["loan"] + " : " + p["party"].strip(), value); cr(lines, bank, value)
    elif kind == "Loan interest paid":
        dr(lines, account or "Interest Expense A/c", value); cr(lines, bank, value)
        details.append("Withholding and other tax consequences require separate review.")
    elif kind == "Depreciation":
        asset, rate, value, closing = tax_depreciation(p["description"], value, p["date"],
            p.get("depreciation_class", ""), p.get("depreciation_basis", "Opening WDV"), p.get("put_to_use", ""))
        dr(lines, "Income-tax depreciation (memorandum) : " + asset, value)
        cr(lines, "Tax WDV adjustment (memorandum) : " + asset, value)
        details.append(f"Income-tax WDV calculation: {asset}; {rate}% of {amount_text(money(p['amount']))} = {amount_text(value)}; closing WDV {amount_text(closing)}. Tax computation only; do not post this as book depreciation. Source: https://www.incometaxindia.gov.in/w/depreciation-rates")
    elif kind in {"RCM assessment", "RCM tax payment", "RCM ITC claim", "RCM ITC disallowed"}:
        rate = Decimal(str(p["gst_rate"] or "0"))
        if not rate.is_finite() or rate <= 0 or rate > 100:
            raise ValueError("Enter the verified RCM GST rate.")
        taxable, gross, taxes = tax_split(value, rate, p["inclusive"], p["interstate"])
        if kind == "RCM assessment":
            for tax, portion in taxes.items():
                dr(lines, L[f"rcm_pending_{tax.lower()}"], portion)
                cr(lines, L[f"rcm_{tax.lower()}"], portion)
            details.append("RCM tax assessment only. Vendor invoice and tax payment are separate entries.")
        elif kind == "RCM tax payment":
            for tax, portion in taxes.items():
                dr(lines, L[f"rcm_{tax.lower()}"], portion)
            cr(lines, L["bank"], gross - taxable)
            details.append("Verify RCM was assessed and paid using the permitted payment method.")
        elif kind == "RCM ITC claim":
            if p["itc"] != "Eligible":
                raise ValueError("RCM ITC claim requires an affirmative eligible-ITC selection.")
            for tax, portion in taxes.items():
                dr(lines, L[f"input_{tax.lower()}"], portion)
                cr(lines, L[f"rcm_pending_{tax.lower()}"], portion)
            details.append("Post only once RCM payment and all ITC conditions are confirmed.")
        else:
            if not account:
                raise ValueError("Enter the cost or asset ledger for ineligible RCM tax.")
            for tax, portion in taxes.items():
                dr(lines, account, portion)
                cr(lines, L[f"rcm_pending_{tax.lower()}"], portion)
            details.append("Ineligible RCM tax transferred to cost; verify treatment and capitalization.")
        details.append(f"RCM base {amount_text(taxable)}; tax {amount_text(gross - taxable)}.")
    else:
        raise ValueError("Choose a supported transaction type.")

    validate(lines)
    return lines, details


class JournalStore:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(DB_PATH)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS journals (
                id INTEGER PRIMARY KEY, posted_at TEXT NOT NULL, transaction_date TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL,
                description TEXT NOT NULL, party TEXT NOT NULL, notes TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS lines (
                journal_id INTEGER NOT NULL REFERENCES journals(id), position INTEGER NOT NULL,
                ledger TEXT NOT NULL, debit TEXT NOT NULL, credit TEXT NOT NULL,
                PRIMARY KEY(journal_id, position));
            CREATE TABLE IF NOT EXISTS tds_events (
                journal_id INTEGER PRIMARY KEY REFERENCES journals(id),
                party TEXT NOT NULL, category TEXT NOT NULL, period TEXT NOT NULL,
                base TEXT NOT NULL, deducted TEXT NOT NULL);
        """)
        if "transaction_date" not in [col[1] for col in self.db.execute("PRAGMA table_info(journals)")]:
            self.db.execute("ALTER TABLE journals ADD COLUMN transaction_date TEXT NOT NULL DEFAULT ''")

    def balance(self, ledger):
        debit = credit = Decimal(0)
        for d, c in self.db.execute("SELECT debit, credit FROM lines WHERE ledger=?", (ledger,)):
            debit += Decimal(d); credit += Decimal(c)
        return debit - credit

    def rcm_claimed(self, ledger):
        total = Decimal(0)
        for (debit,) in self.db.execute("""SELECT l.debit FROM lines l JOIN journals j ON j.id=l.journal_id
            WHERE j.kind='RCM ITC claim' AND l.ledger=?""", (ledger,)):
            total += Decimal(debit)
        return total

    def tds_totals(self, party, category, period, through_date):
        base = deducted = Decimal(0)
        for value, tax, recorded_date in self.db.execute("""SELECT e.base,e.deducted,j.transaction_date
            FROM tds_events e JOIN journals j ON j.id=e.journal_id
            WHERE e.party=? AND e.category=? AND e.period=?""",
            (party.casefold().strip(), category, period)):
            if recorded_date > through_date:
                raise ValueError("Post this payee's entries in date order to calculate cumulative TDS accurately.")
            base += Decimal(value)
            deducted += Decimal(tax)
        return base, deducted

    def post(self, kind, description, party, notes, lines, transaction_date=None, tds_event=None):
        validate(lines)
        transaction_date = transaction_date or dt.date.today().isoformat()
        dt.date.fromisoformat(transaction_date)
        with self.db:
            cursor = self.db.execute("INSERT INTO journals(posted_at,transaction_date,kind,description,party,notes) VALUES(?,?,?,?,?,?)",
                (dt.datetime.now().astimezone().isoformat(timespec="seconds"), transaction_date, kind, description, party, notes))
            self.db.executemany("INSERT INTO lines(journal_id,position,ledger,debit,credit) VALUES(?,?,?,?,?)",
                [(cursor.lastrowid, i, x.ledger, str(x.debit), str(x.credit)) for i, x in enumerate(lines, 1)])
            if tds_event:
                self.db.execute("INSERT INTO tds_events(journal_id,party,category,period,base,deducted) VALUES(?,?,?,?,?,?)",
                    (cursor.lastrowid, tds_event["party"].casefold().strip(), tds_event["category"],
                     tds_event["period"], str(tds_event["base"]), str(tds_event["deducted"])))
        return cursor.lastrowid

    def export_rows(self):
        return list(self.db.execute("""SELECT j.id,j.posted_at,j.kind,j.description,j.party,
            l.position,l.ledger,l.debit,l.credit,j.notes,j.transaction_date FROM journals j JOIN lines l
            ON l.journal_id=j.id ORDER BY j.id,l.position"""))


def colref(n):
    result = ""
    while n:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


def sheet_xml(rows, monetary_cols=()):
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetData>']
    for r, row in enumerate(rows, 1):
        parts.append(f'<row r="{r}">')
        for c, value in enumerate(row, 1):
            ref = f"{colref(c)}{r}"
            if r > 1 and c in monetary_cols:
                parts.append(f'<c r="{ref}" s="1"><v>{escape(str(value))}</v></c>')
            else:
                # Inline strings prevent user-entered descriptions becoming Excel formulas.
                safe = escape(str(value), {'"': '&quot;'})
                parts.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{safe}</t></is></c>')
        parts.append('</row>')
    parts.append('</sheetData></worksheet>')
    return ''.join(parts)


def export_xlsx(path, records):
    if not records:
        raise ValueError("There are no posted entries to export.")
    total_dr = sum((Decimal(r[7]) for r in records), Decimal(0))
    total_cr = sum((Decimal(r[8]) for r in records), Decimal(0))
    if total_dr != total_cr:
        raise ValueError("Export blocked: the stored journal is not balanced.")
    journal = [("Entry ID", "Posted at", "Type", "Description", "Party", "Line", "Ledger", "Debit INR", "Credit INR", "Notes", "Transaction date")]
    journal.extend(records)
    summary = [("Control", "Value"), ("Total debit", str(total_dr)),
               ("Total credit", str(total_cr)), ("Difference", str(total_dr - total_cr)),
               ("Status", "BALANCED"), ("Number of journals", str(len({x[0] for x in records})))]
    # Minimal valid OOXML workbook, generated without third-party packages.
    with ZipFile(path, "w", ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Journal Entries" sheetId="1" r:id="rId1"/><sheet name="Control Summary" sheetId="2" r:id="rId2"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr("xl/styles.xml", '<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0.00"/></numFmts><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" xfId="0"/><xf numFmtId="164" xfId="0" applyNumberFormat="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml(journal, (8, 9)))
        z.writestr("xl/worksheets/sheet2.xml", sheet_xml(summary))



def parse_description(description):
    """Extract stated facts only. Missing decisions remain None for clarification."""
    text = description.strip()
    if not text:
        raise ValueError("Describe the transaction first.")
    low = text.lower()
    kind = infer_type(text)
    explicit = [
        (r"\b(rcm|reverse charge)\b.*\b(itc|input credit)\b", "RCM ITC claim"),
        (r"\b(rcm|reverse charge)\b.*\b(pay|paid|deposit|remit)\b", "RCM tax payment"),
        (r"\b(rcm|reverse charge)\b", "RCM assessment"),
        (r"\b(loan|principal)\b.*\b(repaid|repayment|returned)\b|\brepaid\b.*\bloan\b", "Loan principal repaid"),
        (r"\b(received|borrowed|obtained)\b.*\bloan\b", "Loan received"),
        (r"\binterest\b.*\b(paid|payment)\b|\bpaid\b.*\binterest\b", "Loan interest paid"),
        (r"\b(sold|sales|sale)\b", "Sale"),
        (r"\b(advance)\b.*\b(customer|received|from)\b", "Advance from customer"),
        (r"\b(advance)\b.*\b(supplier|paid|to)\b", "Advance to supplier"),
    ]
    for pattern, detected in explicit:
        if re.search(pattern, low):
            kind = detected
            break
    # Indian day-first dates, ISO dates, and named-month dates.
    date = None
    iso = re.search(r"\b\d{4}-\d{1,2}-\d{1,2}\b", text)
    day_first = re.search(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}\b", text)
    named = re.search(r"\b\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}\b", text, re.I)
    if iso:
        date = dt.date.fromisoformat(iso.group()).isoformat()
    elif day_first:
        date = dt.datetime.strptime(day_first.group().replace("/", "-").replace(".", "-"), "%d-%m-%Y").date().isoformat()
    elif named:
        raw = named.group()
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                date = dt.datetime.strptime(raw, fmt).date().isoformat()
                break
            except ValueError:
                pass
    if (iso or day_first or named) and date is None:
        raise ValueError("Could not read the transaction date. Use DD/MM/YYYY or YYYY-MM-DD.")

    # A currency-tagged amount is unambiguous even if a date or tax rate follows.
    found = re.findall(r"(?:₹|\b(?:Rs\.?|INR)\s*)\s*([\d,]+(?:\.\d{1,2})?)", text, re.I)
    if not found:
        found = re.findall(r"\b(?:amount(?:ing)?\s+(?:of|to)\s+|for\s+)([\d,]+(?:\.\d{1,2})?)\b", text, re.I)
    amount = found[0].replace(",", "") if len(found) == 1 else None

    gst = re.search(r"\b(?:gst|igst|cgst|sgst)\b\s*(?:(?:@|rate|of|at|:|is)\s*)?(\d+(?:\.\d+)?)\s*%", low)
    if not gst:
        gst = re.search(r"\b(\d+(?:\.\d+)?)\s*%\s*(?:gst|igst|cgst|sgst)\b", low)
    # A nearby TDS percentage must never be borrowed as the GST rate.
    gst_free = bool(re.search(r"\b(?:no\s+gst|gst\s+(?:exempt|nil|not\s+applicable)|non.?gst|zero.?rated)\b", low))
    gst_rate = gst.group(1) if gst else ("0" if gst_free else None)
    tds = re.search(r"\btds\b\s*(?:(?:@|rate|of|at|:|is)\s*)?(\d+(?:\.\d+)?)\s*%", low)
    if not tds:
        tds = re.search(r"\b(\d+(?:\.\d+)?)\s*%\s*tds\b", low)
    tds_rate = tds.group(1) if tds else (None if re.search(r"\btds\b", low) else "0")
    section = re.search(r"\b(?:section|u/s|under)\s*(194\s*[A-Za-z]{1,3}|19[2-9]\s*[A-Za-z]{0,3})\b", text, re.I)

    party = ""
    for match in re.finditer(r"\b(?:from|to)\s+([^,.₹\n]+)", text, re.I):
        candidate = re.split(r"\b(?:on|by|via|through|for|at|including|incl|with|dated|date|under|plus|exclusive|inclusive|gst|tds|interstate|intra.?state)\b|\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d+\s*%", match.group(1), maxsplit=1, flags=re.I)[0].strip(" .,-")
        if candidate and candidate.lower() not in {"bank", "cash", "supplier", "customer", "a supplier", "a customer"}:
            party = candidate
            break
    payment = "Bank" if re.search(r"\b(by|via|through)\s+(?:the\s+)?(?:bank|upi|neft|rtgs|imps|cheque|card)\b", low) else \
        "Cash" if re.search(r"\b(for|by|in)\s+cash\b", low) else \
        "Credit" if re.search(r"\b(on\s+credit|credit\s+(?:basis|purchase|sale)|unpaid|outstanding)\b", low) else None
    if kind in {"Loan received", "Loan principal repaid", "Loan interest paid", "Pay supplier", "Receive from customer", "Advance to supplier", "Advance from customer"} and payment is None:
        payment = "Bank" if re.search(r"\b(?:paid|received|repaid|borrowed)\b", low) else None
    inclusive = True if re.search(r"\b(?:including|inclusive|incl\.?|includes)\b[^.]{0,25}\bgst\b|\bgst\s+(?:\d+(?:\.\d+)?\s*%\s*)?(?:inclusive|included)\b", low) else \
        False if re.search(r"\b(?:plus|exclusive|excluding)\b[^.]{0,25}\bgst\b|\bgst\s+(?:\d+(?:\.\d+)?\s*%\s*)?(?:extra|exclusive|excluded)\b", low) else None
    interstate = True if re.search(r"\b(?:inter.?state|igst|different\s+states?)\b", low) else \
        False if re.search(r"\b(?:intra.?state|cgst|sgst|same\s+state)\b", low) else None
    itc = "Ineligible" if re.search(r"\b(?:itc\s+(?:ineligible|blocked|not\s+available)|no\s+itc|ineligible\s+itc)\b", low) else \
        "Eligible" if re.search(r"\b(?:itc\s+eligible|eligible\s+itc|itc\s+available)\b", low) else None
    ledger = ""
    if kind == "Fixed asset purchase":
        ledger = "Computer Equipment A/c" if re.search(r"\b(?:laptop|computer|desktop|server)\b", low) else \
            "Plant & Machinery A/c" if re.search(r"\b(?:plant|machinery|machine)\b", low) else "Fixed Assets A/c"
    elif kind in {"Expense", "Accrued expense"}:
        for pattern, name in [(r"\b(?:professional|consulting|consultancy)\s+fees?\b", "Professional Fees A/c"),
                              (r"\b(?:office\s+)?rent\b", "Rent Expense A/c"),
                              (r"\b(?:audit\s+fees?)\b", "Audit Fees A/c"),
                              (r"\b(?:salary|salaries|wages)\b", "Salaries A/c"),
                              (r"\b(?:insurance)\b", "Insurance Expense A/c")]:
            if re.search(pattern, low):
                ledger = name
                break
    return dict(type=kind, amount=amount, date=date, party=party, ledger=ledger,
                payment=payment, gst_rate=gst_rate, tds_rate=tds_rate,
                tds_section=section.group(1).replace(" ", "") if section else "",
                tds_base="", inclusive=inclusive, interstate=interstate, itc=itc,
                rcm=False, manual="", life="", residual="0", days="365",
                description=text)


# Resident domestic transactions from the supplied Tax Year 2026-27 chart,
# cross-checked against section 393 of the Income-tax Act, 2025.
TDS_RULES = {
    "professional": (Decimal("10"), Decimal("50000"), "393(1) Table 6(iii)(b) [194J]", "year"),
    "technical": (Decimal("2"), Decimal("50000"), "393(1) Table 6(iii)(a) [194J]", "year"),
    "director": (Decimal("10"), Decimal("0"), "393(1) Table 6(iii)(b) [194J]", "year"),
    "rent_property": (Decimal("10"), Decimal("50000"), "393(1) Table 2(ii)(b) [194I]", "month"),
    "rent_machinery": (Decimal("2"), Decimal("50000"), "393(1) Table 2(ii)(a) [194I]", "month"),
    "commission": (Decimal("2"), Decimal("20000"), "393(1) Table 1(ii) [194H]", "year"),
    "contract": (None, Decimal("30000"), "393(1) Table 6(i) [194C]", "year"),
}

# Codes to be used in Returns, from the user's 2026-27 TDS chart.
TDS_IDENTIFIERS = {
    "professional": ("1027", "194J(b)", "393(1) Table Sl. No. 6(iii).D(b)"),
    "technical": ("1026", "194J(a)", "393(1) Table Sl. No. 6(iii).D(a)"),
    "director": ("1028", "194J(b)", "393(1) Table Sl. No. 6(iii).D(b)"),
    "rent_property": ("1009", "194I(b)", "393(1) Table Sl. No. 2(ii).D(b)"),
    "rent_machinery": ("1008", "194I(a)", "393(1) Table Sl. No. 2(ii).D(a)"),
    "commission": ("1006", "194H", "393(1) Table Sl. No. 1(ii)"),
    "contract_individual": ("1023", "194C", "393(1) Table Sl. No. 6(i).D(a)"),
    "contract_other": ("1024", "194C", "393(1) Table Sl. No. 6(i).D(b)"),
}


def tds_identifiers(category, payee_type="Other"):
    key = ("contract_individual" if payee_type == "Individual/HUF" else "contract_other") if category == "contract" else category
    return TDS_IDENTIFIERS[key]


def classify_tds(description, kind):
    if kind not in {"Expense", "Purchase", "Fixed asset purchase", "Accrued expense"}:
        return None
    s = description.lower()
    if re.search(r"\b(?:director(?:'s)?\s+(?:fee|remuneration|commission)|sitting\s+fees?)\b", s):
        return "director"
    if re.search(r"\b(?:technical\s+(?:services?|fees?|consultancy)|engineering\s+consultancy)\b", s):
        return "technical"
    if re.search(r"\b(?:professional\s+(?:fees?|services?|charges?|expenses?)|consultancy\s+(?:fees?|charges?|expenses?)|consulting\s+(?:fees?|charges?|services?)|consultant|audit\s+(?:fees?|charges?|expenses?)|legal\s+(?:fees?|charges?|services?)|advocate\s+fees?|chartered\s+accountant\s+fees?)\b", s):
        return "professional"
    if re.search(r"\b(?:machinery|equipment|plant)\s+rent\b|\brent\s+(?:of|for)\s+(?:machinery|equipment|plant)\b", s):
        return "rent_machinery"
    if re.search(r"\b(?:rent|lease\s+rent)\b", s):
        return "rent_property"
    if re.search(r"\b(?:commission|brokerage)\b", s):
        return "commission"
    if re.search(r"\b(?:contractor|contract\s+(?:work|charges)|works\s+contract|job\s+work|labou?r\s+(?:charges|contract))\b", s):
        return "contract"
    return None


def tds_period(transaction_date, mode):
    date = dt.date.fromisoformat(transaction_date)
    if mode == "month":
        return date.strftime("%Y-%m")
    year = date.year if date.month >= 4 else date.year - 1
    return f"{year}-{year + 1}"


def calculate_tds(p, store, opening_base="", opening_tax="", payee_type="", gst_separate=""):
    """Return computed draft and tracking event; never infer unknown residency/PAN."""
    p = dict(p)
    notes = []
    category = p.get("tds_category") or classify_tds(p["description"], p["type"])
    if category and category not in TDS_RULES:
        raise ValueError("Choose a supported TDS nature in Review details.")
    if not category:
        if p["type"] in {"Purchase", "Fixed asset purchase"} and money(p["amount"]) > Decimal("5000000"):
            notes.append("Review purchase-of-goods TDS (old 194Q): buyer turnover and cumulative vendor purchases are required.")
        if p["type"] in {"Expense", "Loan interest paid", "Accrued expense"}:
            notes.append("No automatic TDS rule matches this expense; review its withholding treatment.")
        return p, None, notes
    if not dt.date(2026, 4, 1) <= dt.date.fromisoformat(p["date"]) <= dt.date(2027, 3, 31):
        raise ValueError("Automatic TDS rates use the attached 2026-27 chart. Review another tax year separately.")
    if re.search(r"\b(?:non.?resident|foreign\s+vendor)\b", p["description"], re.I):
        raise ValueError("This rate chart's domestic rules cannot determine withholding for a nonresident payee.")
    if not p["party"].strip():
        raise ValueError("Add the payee name to the description, for example 'to ABC Ltd'.")
    rate, threshold, section, mode = TDS_RULES[category]
    if category == "contract":
        if payee_type not in {"Individual/HUF", "Other"}:
            raise ValueError("For contract work, select the payee type in the TDS review row.")
        rate = Decimal("1") if payee_type == "Individual/HUF" else Decimal("2")
    base, gross, _ = tax_split(money(p["amount"]), Decimal(p["gst_rate"]), p["inclusive"], p["interstate"])
    if Decimal(p["gst_rate"]) > 0:
        if gst_separate not in {"Yes", "No"}:
            raise ValueError("For TDS, select whether GST is separately shown on the supplier's invoice.")
        current = base if gst_separate == "Yes" else gross
    else:
        current = base
    period = tds_period(p["date"], mode)
    prior, prior_tax = store.tds_totals(p["party"], category, period, p["date"])
    if opening_base.strip():
        prior += money(opening_base)
        if money(opening_base) > 0 and not opening_tax.strip():
            raise ValueError("Enter TDS already deducted on the opening prior payments (enter 0 if none).")
        prior_tax += money(opening_tax or "0")
    elif not prior and current <= threshold and category != "director":
        raise ValueError("Enter prior payments to this payee for the tax year (0 if none) in the TDS review row.")
    if opening_base.strip() and money(opening_base) < 0:
        raise ValueError("Prior payments cannot be negative.")
    aggregate = prior + current
    if category == "contract":
        applies = current > Decimal("30000") or aggregate > Decimal("100000")
    else:
        applies = aggregate > threshold if threshold else True
    deduction = money(aggregate * rate / 100) - prior_tax if applies else Decimal("0.00")
    if deduction < 0:
        raise ValueError("Prior TDS exceeds the calculated tax; review prior totals.")
    if deduction > gross:
        raise ValueError("Catch-up TDS exceeds this invoice's gross amount. Resolve the earlier payments manually.")
    if p["tds_rate"] not in (None, "0", "0.0") and Decimal(p["tds_rate"]) != rate:
        raise ValueError(f"Description states TDS {p['tds_rate']}%; the matched chart rate is {rate}%. Review nature/payee type.")
    p["tds_rate"] = str(rate) if deduction else "0"
    p["tds_rule_rate"] = str(rate)
    code, old, new = tds_identifiers(category, payee_type)
    p["tds_section"] = f"{old} / {new} (return code {code})" if deduction else ""
    p["tds_base"] = str(current)
    p["tds_amount"] = str(deduction)
    notes.append(f"TDS {category}: {rate}% • threshold {amount_text(threshold)} • prior {amount_text(prior)} • current base {amount_text(current)} • deduction {amount_text(deduction)}. Old {old}; new {new}; return code {code}.")
    if prior > 0 and not prior_tax and deduction:
        notes.append("Deduction includes catch-up tax on previously tracked or declared amounts.")
    event = {"party": p["party"], "category": category, "period": period,
             "base": current, "deducted": deduction}
    return p, event, notes


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.store = JournalStore()
        self.preview_lines = None
        self.preview_key = None
        self.title(APP)
        self.geometry("1100x840")
        self.minsize(860, 680)
        self.configure(bg="#eaf2f8")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#eaf2f8")
        style.configure("TLabel", background="#eaf2f8", foreground="#173a55", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.review = {}
        self._ui()

    def _ui(self):
        head = tk.Frame(self, bg="#123b61")
        head.pack(fill="x")
        tk.Label(head, text=APP, bg="#123b61", fg="white", font=("Segoe UI", 21, "bold")).pack(anchor="w", padx=22, pady=(12, 2))
        tk.Label(head, text="ENTER TRANSACTION  •  REVIEW GST AND TDS  •  POST JOURNAL", bg="#123b61", fg="#a4e6d9", font=("Segoe UI", 10)).pack(anchor="w", padx=23, pady=(0, 13))
        main = ttk.Frame(self, padding=15)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="Transaction input", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))
        table = ttk.Frame(main)
        table.pack(fill="x")
        table.columnconfigure(1, weight=1)
        for col, label in enumerate(("Date (DD/MM/YYYY)", "Description of transaction", "Amount (₹)", "GST rate %")):
            ttk.Label(table, text=label, font=("Segoe UI", 10, "bold")).grid(row=0, column=col, sticky="w", padx=5)
        date_box = ttk.Frame(table)
        date_box.grid(row=1, column=0, sticky="nsew", padx=5, pady=7)
        self.date = ttk.Entry(date_box, width=13)
        self.date.pack(side="left", fill="x", expand=True)
        ttk.Button(date_box, text="Calendar", command=self.select_date).pack(side="left", padx=(3, 0))
        self.description = tk.Text(table, height=3, wrap="word", font=("Segoe UI", 11), bg="white", relief="solid", bd=1, padx=7, pady=6)
        self.description.grid(row=1, column=1, sticky="nsew", padx=5, pady=7)
        self.amount = ttk.Entry(table, width=18)
        self.amount.grid(row=1, column=2, sticky="nsew", padx=5, pady=7)
        self.gst_rate = ttk.Entry(table, width=14)
        self.gst_rate.grid(row=1, column=3, sticky="nsew", padx=5, pady=7)
        ttk.Label(main, text="Example: Professional fees to ABC Ltd on credit, intrastate, ITC eligible. Enter 0 in GST rate when GST does not apply.", wraplength=1020).pack(anchor="w", pady=(1, 10))

        # All missing details are resolved in this window, never in question dialogs.
        details = ttk.LabelFrame(main, text="Review details (complete only when requested below)", padding=8)
        details.pack(fill="x", pady=(0, 10))
        self.details = details
        for col in (1, 3, 5):
            details.columnconfigure(col, weight=1)
        specs = [
            ("party", "Payee / party", None, 0, 0),
            ("payment", "Settlement", ("", "Credit", "Bank", "Cash"), 0, 2),
            ("gst_basis", "GST basis", ("", "Inclusive", "Exclusive"), 0, 4),
            ("gst_location", "GST location", ("", "Intrastate", "Interstate"), 1, 0),
            ("itc", "ITC", ("", "Eligible", "Ineligible"), 1, 2),
            ("gst_separate", "GST shown separately", ("", "Yes", "No"), 1, 4),
            ("opening", "External prior ₹", None, 2, 0),
            ("opening_tax", "External prior TDS ₹", None, 2, 2),
            ("payee_type", "Contractor type", ("", "Individual/HUF", "Other"), 2, 4),
            ("tds_nature", "TDS nature override", ("", "professional", "technical", "director", "rent_property", "rent_machinery", "commission", "contract"), 3, 0),
            ("depreciation_class", "Tax asset class", ("", *DEPRECIATION_RATES), 3, 2),
            ("depreciation_basis", "Depreciation basis", ("Opening WDV", "New asset cost"), 3, 4),
            ("put_to_use", "Date put to use", None, 4, 0),
        ]
        for key, label, choices, row, col in specs:
            ttk.Label(details, text=label).grid(row=row, column=col, sticky="w", padx=4, pady=4)
            var = tk.StringVar()
            widget = ttk.Combobox(details, textvariable=var, values=choices, state="readonly", width=16) if choices else ttk.Entry(details, textvariable=var, width=17)
            widget.grid(row=row, column=col+1, sticky="ew", padx=4, pady=4)
            self.review[key] = var
        self.verified = tk.BooleanVar(value=False)
        ttk.Checkbutton(details, text="Resident payee, valid PAN and deductor status verified", variable=self.verified).grid(row=5, column=0, columnspan=6, sticky="w", pady=3)
        details.pack_forget()

        buttons = ttk.Frame(main)
        self.buttons = buttons
        buttons.pack(fill="x", pady=7)
        for caption, command in (("Generate Entry", self.preview), ("Post Entry", self.post),
                                 ("New / Re-run", self.clear), ("Export Excel", self.export), ("History", self.history)):
            ttk.Button(buttons, text=caption, command=command).pack(side="left", padx=(0, 8))
        self.status = ttk.Label(main, text="Enter date, description and amount, then generate the entry.", wraplength=1030)
        self.status.pack(anchor="w", pady=7)
        ttk.Label(main, text="TDS calculation", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(4, 2))
        self.tds_table = ttk.Treeview(main, columns=("nature", "code", "old", "new", "rate", "threshold", "base", "tds"), show="headings", height=1)
        for key, title, width in (("nature", "Nature", 120), ("code", "Codes to be used in Returns", 175),
                                  ("old", "Old Section", 90), ("new", "New Section (IT Act) 2025", 275),
                                  ("rate", "Rate", 75), ("threshold", "Threshold ₹", 120),
                                  ("base", "TDS base ₹", 130), ("tds", "TDS ₹", 130)):
            self.tds_table.heading(key, text=title)
            self.tds_table.column(key, width=width, anchor="e" if key in {"rate", "threshold", "base", "tds"} else "w")
        self.tds_table.pack(fill="x", pady=3)
        self.tds_status = ttk.Label(main, text="TDS will be evaluated when you click Generate Entry.", wraplength=1030)
        self.tds_status.pack(anchor="w", pady=(0, 5))
        self.table = ttk.Treeview(main, columns=("ledger", "debit", "credit"), show="headings", height=6)
        for key, title, width in (("ledger", "Ledger", 540), ("debit", "Debit ₹", 170), ("credit", "Credit ₹", 170)):
            self.table.heading(key, text=title)
            self.table.column(key, width=width, anchor="w" if key == "ledger" else "e")
        self.table.pack(fill="both", expand=True)
        self.notes = ttk.Label(main, text="", wraplength=1030)
        self.notes.pack(anchor="w", pady=6)

    def select_date(self):
        """Local calendar picker; choosing a day fills the date column."""
        try:
            selected = dt.datetime.strptime(self.date.get().strip(), "%d/%m/%Y").date()
        except ValueError:
            selected = dt.date.today()
        picker = tk.Toplevel(self)
        picker.title("Select transaction date")
        picker.transient(self)
        picker.resizable(False, False)
        header = ttk.Frame(picker, padding=8)
        header.pack(fill="x")
        grid = ttk.Frame(picker, padding=(8, 0, 8, 8))
        grid.pack()

        def render(year, month):
            for child in grid.winfo_children():
                child.destroy()
            title.configure(text=f"{calendar.month_name[month]} {year}")
            for col, name in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
                ttk.Label(grid, text=name).grid(row=0, column=col, padx=5, pady=3)
            for row, week in enumerate(calendar.monthcalendar(year, month), 1):
                for col, day in enumerate(week):
                    if day:
                        def choose(d=day, y=year, m=month):
                            self.date.delete(0, "end")
                            self.date.insert(0, dt.date(y, m, d).strftime("%d/%m/%Y"))
                            picker.destroy()
                        ttk.Button(grid, text=str(day), width=4, command=choose).grid(row=row, column=col, padx=2, pady=2)

        def move(offset):
            nonlocal selected
            year, month = divmod(selected.year * 12 + selected.month - 1 + offset, 12)
            selected = dt.date(year, month + 1, 1)
            render(selected.year, selected.month)

        ttk.Button(header, text="<", width=3, command=lambda: move(-1)).pack(side="left")
        title = ttk.Label(header, font=("Segoe UI", 11, "bold"))
        title.pack(side="left", expand=True, padx=24)
        ttk.Button(header, text=">", width=3, command=lambda: move(1)).pack(side="right")
        render(selected.year, selected.month)

    def key(self):
        return (self.date.get(), self.description.get("1.0", "end-1c"), self.amount.get(), self.gst_rate.get(),
                *(self.review[k].get() for k in sorted(self.review)), self.verified.get())

    def _parse_input(self):
        self.pending = []
        desc = self.description.get("1.0", "end-1c").strip()
        p = parse_description(desc)
        date_cell = self.date.get().strip()
        amount_cell = self.amount.get().strip()
        if date_cell:
            parsed = parse_description("on " + date_cell)["date"]
            if not parsed:
                raise ValueError("Enter a valid date in the Date column (DD/MM/YYYY or YYYY-MM-DD).")
            if p["date"] and parsed != p["date"]:
                raise ValueError("Date in the column differs from the description. Correct one of them.")
            p["date"] = parsed
        if amount_cell:
            value = money(amount_cell)
            if p["amount"] and value != money(p["amount"]):
                raise ValueError("Amount in the column differs from the description. Correct one of them.")
            p["amount"] = str(value)
        if not p["date"] or not p["amount"]:
            raise ValueError("Enter the transaction date and amount in the table above.")
        if not p["type"]:
            raise ValueError("State the nature of the transaction, such as professional fees, rent, contract work, purchase or sale.")
        cell_rate = self.gst_rate.get().strip().removesuffix("%").strip()
        if cell_rate:
            entered = Decimal(cell_rate)
            if not entered.is_finite() or entered < 0 or entered > 100:
                raise ValueError("GST rate must be between 0 and 100%.")
            if p["gst_rate"] is not None and entered != Decimal(p["gst_rate"]):
                raise ValueError("GST rate in the column differs from the description.")
            p["gst_rate"] = str(entered)
        if p["type"] in PARTY_TYPES:
            p["party"] = p["party"] or self.review["party"].get().strip()
            if not p["party"]:
                p["party"] = "Payee to specify"
                self.pending.append("Enter the real payee / party name")
        if p["type"] in INVOICE_TYPES and p["type"] != "Accrued expense":
            p["payment"] = p["payment"] or self.review["payment"].get()
            if p["payment"] not in {"Credit", "Bank", "Cash"}:
                p["payment"] = "Bank" if re.search(r"\bpaid\b", desc, re.I) else "Credit"
                self.pending.append("Confirm settlement (Bank, Cash or Credit)")
            if p["gst_rate"] is None:
                raise ValueError("Enter the GST rate in the visible GST rate column (enter 0 if GST is not applicable).")
            if Decimal(p["gst_rate"]) > 0:
                basis = self.review["gst_basis"].get()
                loc = self.review["gst_location"].get()
                p["inclusive"] = p["inclusive"] if p["inclusive"] is not None else (basis == "Inclusive" if basis else None)
                p["interstate"] = p["interstate"] if p["interstate"] is not None else (loc == "Interstate" if loc else None)
                if p["inclusive"] is None:
                    p["inclusive"] = False
                    self.pending.append("Confirm GST is exclusive or choose Inclusive")
                if p["interstate"] is None:
                    p["interstate"] = False
                    self.pending.append("Confirm intrastate or choose Interstate")
                p["itc"] = p["itc"] or self.review["itc"].get()
                if p["type"] != "Sale" and p["itc"] not in {"Eligible", "Ineligible"}:
                    p["itc"] = "Eligible"
                    self.pending.append("Confirm ITC eligibility")
            if p["tds_rate"] is None:
                p["tds_rate"] = "0"  # matched chart rule determines the rate
        elif p["type"] == "Accrued expense" and p["gst_rate"] is None:
            p["gst_rate"] = "0"
        p["gst_rate"] = p["gst_rate"] or "0"
        p["tds_rate"] = p["tds_rate"] or "0"
        p["tds_category"] = self.review["tds_nature"].get().strip()
        p["inclusive"] = bool(p["inclusive"])
        p["interstate"] = bool(p["interstate"])
        p["itc"] = p["itc"] or "Eligible"
        p["payment"] = p["payment"] or "Bank"
        if p["type"] == "Depreciation":
            p["depreciation_class"] = self.review["depreciation_class"].get()
            p["depreciation_basis"] = self.review["depreciation_basis"].get() or (
                "New asset cost" if re.search(r"\b(?:new asset|newly acquired|purchased this year|bought this year)\b", desc, re.I)
                else "Opening WDV")
            p["put_to_use"] = self.review["put_to_use"].get()
        return p

    def show_tds_analysis(self):
        """Always display TDS independently of unresolved GST/journal details."""
        self.tds_table.delete(*self.tds_table.get_children())
        desc = self.description.get("1.0", "end-1c").strip()
        try:
            p = parse_description(desc)
            raw_date = self.date.get().strip()
            raw_amount = self.amount.get().strip()
            p["date"] = parse_description("on " + raw_date)["date"] if raw_date else p["date"]
            p["amount"] = str(money(raw_amount)) if raw_amount else p["amount"]
            if not p["date"] or not p["amount"]:
                self.tds_status.configure(text="Enter Date and Amount to calculate TDS.")
                return
            p["party"] = p["party"] or self.review["party"].get().strip() or "Payee to specify"
            p["tds_category"] = self.review["tds_nature"].get().strip()
            category = p["tds_category"] or classify_tds(desc, p["type"])
            if not category:
                label = "This description has no matched TDS rule. If withholding applies, specify the expense nature or select TDS nature override."
                self.tds_status.configure(text=label)
                if p["type"] in {"Expense", "Accrued expense"} and not self.details.winfo_manager():
                    self.details.pack(fill="x", pady=(0, 10), before=self.buttons)
                return
            rate_input = self.gst_rate.get().strip().removesuffix("%").strip()
            gst_unresolved = not rate_input and p["gst_rate"] is None
            p["gst_rate"] = rate_input or p["gst_rate"] or "0"
            p["inclusive"] = p["inclusive"] if p["inclusive"] is not None else self.review["gst_basis"].get() == "Inclusive"
            p["interstate"] = p["interstate"] if p["interstate"] is not None else self.review["gst_location"].get() == "Interstate"
            payee_type = self.review["payee_type"].get() or "Other"
            gst_separate = self.review["gst_separate"].get() or "Yes"
            p, event, _ = calculate_tds(p, self.store, self.review["opening"].get() or "0",
                                        self.review["opening_tax"].get(), payee_type, gst_separate)
            _, threshold, _, _ = TDS_RULES[category]
            code, old, new = tds_identifiers(category, payee_type)
            deduction = money(p["tds_amount"])
            self.tds_table.insert("", "end", values=(category.replace("_", " ").title(), code, old, new,
                f"{p['tds_rule_rate']}%",
                f"{threshold:,.2f}", f"{money(p['tds_base']):,.2f}", f"{deduction:,.2f}"))
            provisional = []
            if gst_unresolved:
                provisional.append("GST rate missing; TDS base currently uses entered amount")
            if p["party"] == "Payee to specify":
                provisional.append("payee and prior payments unverified")
            if not self.review["opening"].get().strip():
                provisional.append("external prior payments assumed zero")
            if category == "contract" and not self.review["payee_type"].get():
                provisional.append("contractor type assumed Other")
            if not self.verified.get():
                provisional.append("resident payee, PAN and deductor status pending")
            self.tds_status.configure(text=(f"TDS {'estimate' if provisional else 'calculated'}: {amount_text(deduction)}. "
                + ("Review: " + "; ".join(provisional) + "." if provisional else "Confirm before posting.")))
        except (ValueError, InvalidOperation) as exc:
            self.tds_status.configure(text=f"TDS needs review: {exc}")

    def _show_final_tds(self, p, event):
        if not event:
            return
        category = event["category"]
        _, threshold, _, _ = TDS_RULES[category]
        code, old, new = tds_identifiers(category, self.review["payee_type"].get())
        self.tds_table.delete(*self.tds_table.get_children())
        self.tds_table.insert("", "end", values=(category.replace("_", " ").title(), code, old, new,
            f"{p['tds_rule_rate']}%",
            f"{threshold:,.2f}", f"{event['base']:,.2f}", f"{event['deducted']:,.2f}"))
        self.tds_status.configure(text=f"TDS payable proposed: {amount_text(event['deducted'])}. "
            + ("Complete the highlighted review details before posting." if self.pending else "Ready for journal review."))

    def preview(self):
        self.preview_lines = None
        self.show_tds_analysis()
        try:
            p = self._parse_input()
            category = p.get("tds_category") or classify_tds(p["description"], p["type"])
            if category and not self.verified.get():
                self.pending.append("Verify resident payee, PAN and deductor status")
            if category and not self.review["opening"].get().strip():
                self.pending.append("Confirm external prior payments (enter 0 if none)")
            gst_separate = self.review["gst_separate"].get()
            if category and Decimal(p["gst_rate"]) > 0 and not gst_separate:
                gst_separate = "Yes"
                self.pending.append("Confirm GST is separately shown on invoice (Yes/No)")
            payee_type = self.review["payee_type"].get()
            if category == "contract" and not payee_type:
                payee_type = "Other"
                self.pending.append("Confirm contractor type (Individual/HUF or Other)")
            p, event, tax_notes = calculate_tds(p, self.store,
                self.review["opening"].get() or "0", self.review["opening_tax"].get(),
                payee_type, gst_separate)
            lines, notes = build(p, self.settings)
            notes.extend(tax_notes)
            if self.pending:
                notes.insert(0, "PROVISIONAL ASSUMPTIONS: " + "; ".join(self.pending) + ".")
            self.preview_lines, self.preview_data, self.preview_notes, self.preview_event = lines, p, notes, event
            self.preview_key = self.key()
            self.table.delete(*self.table.get_children())
            for line in lines:
                self.table.insert("", "end", values=(line.ledger,
                    f"{line.debit:,.2f}" if line.debit else "", f"{line.credit:,.2f}" if line.credit else ""))
            status = "PROVISIONAL DRAFT — complete Review details before posting" if self.pending else "BALANCED DRAFT"
            self.status.configure(text=f"{status}  •  {p['type']}  •  {p['date']}  •  Debit = Credit = {amount_text(validate(lines))}")
            self.notes.configure(text="  ".join(notes))
            self._show_final_tds(p, event)
            if self.pending and not self.details.winfo_manager():
                self.details.pack(fill="x", pady=(0, 10), before=self.buttons)
        except (ValueError, InvalidOperation) as exc:
            if not self.details.winfo_manager():
                self.details.pack(fill="x", pady=(0, 10), before=self.buttons)
            self.status.configure(text=f"NEEDS REVIEW: {exc}")
            self.notes.configure(text="Complete the detail in this window and click Generate Entry again.")
            self.table.delete(*self.table.get_children())

    def post(self):
        if self.preview_lines is None or self.key() != self.preview_key:
            self.status.configure(text="Generate the current entry before posting; review fields changed or preview is missing.")
            return
        if self.pending:
            self.status.configure(text="POSTING BLOCKED: " + "; ".join(self.pending) + ". Update Review details, then Generate Entry again.")
            return
        if self.preview_data["type"] == "Depreciation":
            self.status.configure(text="Tax depreciation is a computation preview; book journal posting is disabled. Use the separately determined book depreciation for accounting.")
            return
        try:
            self._check_open_balances(self.preview_data, self.preview_lines)
            p = self.preview_data
            number = self.store.post(p["type"], p["description"], p["party"],
                                     " ".join(self.preview_notes), self.preview_lines, p["date"], self.preview_event)
            self.status.configure(text=f"POSTED  •  Journal #{number}  •  Balanced")
            self.preview_lines = None
        except (sqlite3.Error, ValueError) as exc:
            self.status.configure(text=f"POSTING BLOCKED: {exc}")

    def _check_open_balances(self, p, lines):
        kind, L, part = p["type"], self.settings["ledgers"], p["party"].strip()
        dependent = {
            "Pay supplier": (f"Party: {part}", "credit", "supplier payable"),
            "Receive from customer": (f"Party: {part}", "debit", "customer receivable"),
            "Pay accrued expense": (L["accrued"], "credit", "accrued expense"),
            "Adjust supplier advance": (L["advance_paid"] + " : " + part, "debit", "supplier advance"),
            "Adjust customer advance": (L["advance_received"] + " : " + part, "credit", "customer advance"),
            "Loan principal repaid": (L["loan"] + " : " + part, "credit", "loan payable"),
        }
        if kind in dependent:
            ledger, side, label = dependent[kind]
            balance = self.store.balance(ledger)
            available = balance if side == "debit" else -balance
            if available < money(p["amount"]):
                raise ValueError(f"Insufficient recorded {label}: {amount_text(max(available, Decimal(0)))}.")
        if kind == "RCM tax payment":
            for line in lines:
                if line.debit and self.store.balance(line.ledger) > -line.debit:
                    raise ValueError(f"Insufficient assessed RCM liability in {line.ledger}.")
        if kind in {"RCM ITC claim", "RCM ITC disallowed"}:
            for line in lines:
                if line.credit and self.store.balance(line.ledger) < line.credit:
                    raise ValueError(f"Insufficient pending RCM ITC in {line.ledger}.")
        if kind == "RCM ITC claim":
            for line in lines:
                if not line.debit:
                    continue
                tax = next((x for x in ("IGST", "CGST", "SGST") if x in line.ledger), None)
                if tax:
                    claimed = self.store.rcm_claimed(L[f"input_{tax.lower()}"])
                    assessed = self.store.balance(L[f"rcm_pending_{tax.lower()}"]) + claimed
                    remaining_liability = -self.store.balance(L[f"rcm_{tax.lower()}"])
                    if assessed - remaining_liability - claimed < line.debit:
                        raise ValueError(f"Insufficient paid RCM {tax} for ITC claim.")

    def clear(self):
        self.date.delete(0, "end")
        self.amount.delete(0, "end")
        self.gst_rate.delete(0, "end")
        self.description.delete("1.0", "end")
        for item in self.review.values():
            item.set("")
        self.verified.set(False)
        self.table.delete(*self.table.get_children())
        self.tds_table.delete(*self.tds_table.get_children())
        self.tds_status.configure(text="TDS will be evaluated when you click Generate Entry.")
        self.notes.configure(text="")
        self.status.configure(text="Ready for another transaction.")
        self.preview_lines = None
        self.description.focus_set()
        self.details.pack_forget()

    def export(self):
        try:
            records = self.store.export_rows()
            if not records:
                raise ValueError("No posted journals to export.")
            path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel workbook", "*.xlsx")],
                                                initialfile=f"Accounting_Journal_{dt.date.today():%Y%m%d}.xlsx")
            if path:
                export_xlsx(path, records)
                self.status.configure(text=f"Exported balanced journal to {path}")
        except (ValueError, OSError) as exc:
            self.status.configure(text=f"EXPORT FAILED: {exc}")

    def history(self):
        top = tk.Toplevel(self)
        top.title("Posted journal history")
        top.geometry("970x480")
        columns = ("ID", "Date", "Type", "Description", "Party", "Ledger", "Debit", "Credit")
        tree = ttk.Treeview(top, columns=columns, show="headings")
        for key in columns:
            tree.heading(key, text=key)
            tree.column(key, width=220 if key in {"Description", "Ledger"} else 100)
        tree.pack(fill="both", expand=True)
        for row in self.store.export_rows()[-300:]:
            tree.insert("", "end", values=(row[0], row[10], row[2], row[3], row[4], row[6], row[7], row[8]))


if __name__ == "__main__":
    try:
        App().mainloop()
    except (OSError, ValueError, sqlite3.Error) as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP, f"Could not start application:\n{error}")
        root.destroy()
