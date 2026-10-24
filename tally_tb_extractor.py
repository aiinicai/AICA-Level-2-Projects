# =============================================================================
#  Tally Extractor  -  version 15
#     Tab 1: Trial Balance Extractor     Tab 2: Fixed Asset Additions
# =============================================================================
#  Connects to Tally Prime on this computer. The app looks on a range of ports
#  (default 9000-9005), so several Tally windows can be used at once - each
#  Tally must have its OWN port (F1 > Settings > Connectivity). Every company
#  found is listed as "Company (port 9000)". Connect / Disconnect buttons and a
#  "Connection details" button explain what was found on each port.
#  Pick the company and the period once; both tabs use them.
#
#  TAB 1 - TRIAL BALANCE EXTRACTOR
#    Name of Ledger | Name of Group | Opening Dr | Opening Cr |
#    Period Debit | Period Credit | Closing Dr | Closing Cr
#    - Search box filters the table on screen.
#    - "Show zero-balance ledgers" tick box: ticked = included, unticked =
#      hidden from the table AND from the export.
#
#  TAB 2 - FIXED ASSET ADDITIONS (format: FAM Additions Details)
#    Sl.no | Invoice No | Date Of Put to use | Party Name | Description | GSTN |
#    Taxable Value | CGST | SGST | IGST | Disc | Net Total | ITC Availed |
#    Amount to be Capitalised | Name of Ledger | No. of Days Used
#    - Every DEBIT to a ledger under "Fixed Assets". Tally itself picks out
#      only the vouchers that touch Fixed Asset ledgers (no Day Book scan),
#      month by month, with a progress bar and a Cancel button. If that does
#      not tie to the books, the app re-reads ledger by ledger automatically.
#    - "Test voucher read" checks one month in seconds before a full run.
#    - Editable on screen: Invoice No, Date Of Put to use, Description, Disc,
#      ITC Availed. Edits are not saved between sessions (planned later).
#    - Reconciliation: additions picked up vs period debits to fixed asset
#      ledgers per Tally.
#    - Credits (sales, depreciation) are not handled yet.
#
#  TAB 3 - SALES RECONCILIATION (books vs GSTR-1 / 1A vs GSTR-3B)
#    - Reads every voucher in Sales Accounts / Direct Incomes / Indirect Incomes
#      (and fixed asset sales) into the GST register's Sales Register format.
#    - Reads GSTR-1 / 1A / 3B PDFs (never saved) and reconciles month-wise,
#      with a year-end bridge for items declared in other years' returns.
#    - Exports: a reconciliation workbook, and the Sales Register filled into
#      the user's own GST register template (via Excel, macros kept).
#    - Extra packages:  py -m pip install pdfplumber pywin32
#
#  The tabs export to Excel (and PDF for TB / FA) with a Save As dialog.
#
#  ONE-TIME SETUP
#   1. Command Prompt:   py -m pip install openpyxl reportlab
#   2. In Tally Prime:   F1 (Help) > Settings > Connectivity > Client/Server
#      configuration:  "TallyPrime acts as" = Both,  Port = 9000.
#      Close and reopen Tally after changing.
#   3. Open the company in Tally and keep Tally running.
#
#  HOW THE TRIAL BALANCE FIGURES ARE WORKED OUT
#   - Tally reports a NEGATIVE balance as DEBIT and a POSITIVE one as CREDIT.
#   - Closing   = each ledger's balance as at the "To" date.
#   - Opening   = each ledger's balance as at the day before the "From" date.
#                 Income/expense ledgers start the year at zero.
#   - Period Debit / Credit = total debits and credits posted in the period.
#   - Profit & Loss A/c: Tally adds the year's profit-to-date to this ledger's
#     balance. The income/expense ledgers already show that profit, so the app
#     takes it out of P&L A/c (same figure as Tally's own Trial Balance).
#   - SELF-CHECK: for every ledger, Opening + Period movement must equal
#     Closing. If Tally does not give period totals for a ledger, or they do
#     not tie up, that ledger shows its NET movement and a warning appears.
#
#  Choices made for this version:
#   - The period must be within one financial year.
#   - The default period is the current period set in Tally (Alt+F2), if Tally
#     reports it; otherwise the financial year in which the books begin.
#   - A ledger is "zero-balance" only if opening, period debit, period credit
#     and closing are ALL zero.
#   - Inventory: stock is not a ledger. If the TB does not tally because of
#     it, Opening Stock (per Tally's inventory) is added as a row and the year's
#     change in stock is taken out of P&L A/c. Closing stock is shown in a note.
# =============================================================================

import os
import queue
import re
import subprocess
import threading
import tkinter as tk
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox, ttk
import socket

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    openpyxl = None
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    reportlab_ready = True
except ImportError:
    reportlab_ready = False

SAVE_FOLDER = os.path.dirname(os.path.abspath(__file__))
CHECK_EVERY_MS = 5000
messages = queue.Queue()
last_reply = threading.local()     # Tally's last raw reply (per thread), kept for the troubleshooting file
fa_cancel = threading.Event()      # set by the Cancel button
state = {"companies": {}, "checking": False, "busy": False, "tb": None, "tb_company": "",
         "last_folder": SAVE_FOLDER, "defaults_set_for": ""}

BLUE, BLUE_DARK, ORANGE, GREEN_BTN = "#0B3D91", "#082C6C", "#F28C28", "#2E7D32"
BG, CARD, TEXT, MUTED = "#F4F6FA", "#FFFFFF", "#1F2937", "#6B7280"
GREEN, RED, AMBER = "#15803D", "#B91C1C", "#B45309"
AMOUNT_KEYS = ["op_dr", "op_cr", "pd_dr", "pd_cr", "cl_dr", "cl_cr"]
AMOUNT_TITLES = ["Opening Dr", "Opening Cr", "Period Debit", "Period Credit", "Closing Dr", "Closing Cr"]
STANDARD_REVENUE_GROUPS = {"sales accounts", "purchase accounts", "direct incomes", "direct expenses",
                           "indirect incomes", "indirect expenses"}


# =============================================================================
# PART 1 - SMALL HELPERS (numbers and dates)
# =============================================================================
def indian(amount):
    # 2187950.5 -> "21,87,950.50"
    sign = "-" if amount < 0 else ""
    whole, decimals = ("%.2f" % abs(amount)).split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = ",".join([head[max(i - 2, 0):i] for i in range(len(head), 0, -2)][::-1])
        whole = head + "," + tail
    return sign + whole + "." + decimals


def to_number(value):
    # Tally amounts may arrive as "-1234.50", "1,234.50", "1234.50 Dr", "-\u20b9 1,234.50", "Rs. 1234.50",
    # "(1234.50)", or - for a foreign-currency ledger - "-$100.00 @ \u20b983.00/$ = -\u20b98300.00".
    # Negative / Dr = debit, positive / Cr = credit. Raises ValueError only if no number can be found.
    text = str(value or "").strip()
    if "=" in text:                                   # foreign currency: keep the rupee value after "="
        text = text.rsplit("=", 1)[1].strip()
    text = text.replace(",", "").strip()
    if text in ("", "-"):
        return 0.0
    lower = text.lower()
    debit, credit = lower.endswith("dr"), lower.endswith("cr")
    if debit or credit:
        text = text[:-2].strip()
    match = re.search(r"\d+(?:\.\d+)?|\.\d+", text)
    if not match:
        if not re.search(r"[A-Za-z0-9]", re.sub(r"(?i)rs\.?", "", text)):
            return 0.0                                # only a currency symbol / dash
        raise ValueError("no number in '" + str(value) + "'")
    amount = float(match.group())
    if debit:
        return -amount
    if credit:
        return amount
    negative = "-" in text[:match.start()] or text.startswith("(")
    return -amount if negative else amount


def parse_tally_date(text):
    # Tally sends dates as "20210401", "1-Apr-2021" or "1-Apr-21". Returns a date or None.
    text = (text or "").strip()
    for pattern in ("%Y%m%d", "%d-%b-%Y", "%d-%b-%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def parse_user_date(text):
    # The user types dd-mm-yyyy (also accepts dd/mm/yyyy and dd.mm.yyyy).
    text = (text or "").strip().replace("/", "-").replace(".", "-")
    try:
        return datetime.strptime(text, "%d-%m-%Y").date()
    except ValueError:
        return None


def show_date(day):
    return day.strftime("%d-%m-%Y")


def year_start_for(day, fy_month, fy_day):
    # The first day of the financial year that contains "day".
    start = date(day.year, fy_month, fy_day)
    return start if day >= start else date(day.year - 1, fy_month, fy_day)


def year_end_for(start):
    try:
        return date(start.year + 1, start.month, start.day) - timedelta(days=1)
    except ValueError:                                   # 29 Feb start - very rare
        return date(start.year + 1, start.month, 28)


# =============================================================================
# PART 2 - TALKING TO TALLY (XML over the Tally port)
# =============================================================================
def tally_request(port, xml_text, timeout=10):
    # Sends a request to Tally and returns the reply as an XML tree.
    last_reply.text = ""
    request = urllib.request.Request("http://localhost:" + str(port), data=xml_text.encode("utf-8"),
                                     headers={"Content-Type": "text/xml;charset=utf-8"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    elif raw[1:2] == b"\x00" and raw.count(b"\x00") > len(raw) // 3:
        text = raw.decode("utf-16-le", errors="replace")          # UTF-16 without the marker
    else:
        text = raw.decode("utf-8", errors="replace")
    last_reply.text = text
    # Tally sometimes includes invisible control codes (e.g. &#4; or &#x4;) that XML forbids - remove them.
    text = re.sub(r"&#(0*[0-8]|0*1[1-2]|0*1[4-9]|0*2[0-9]|0*3[01]);", "", text)
    text = re.sub(r"&#x0*([0-8]|[bBcC]|1[0-9a-fA-F]);", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # A bare "&" (e.g. in a narration) breaks XML - escape it.
    text = re.sub(r"&(?!(?:[a-zA-Z][a-zA-Z0-9]*|#[0-9]+|#x[0-9a-fA-F]+);)", "&amp;", text)
    # Custom TDL fields (UDFs, e.g. from add-ons) come as <UDF:NAME> without the "UDF:" being declared,
    # which XML rejects ("unbound prefix"). Rename them to <UDF_NAME> - the app does not use them anyway.
    text = re.sub(r"\sxmlns:[\w.\-]+=(\"[^\"]*\"|'[^']*')", "", text)
    text = re.sub(r"<(/?)([A-Za-z_][\w.\-]*):(?=[A-Za-z_])", r"<\1\2_", text)
    text = re.sub(r"(\s)([A-Za-z_][\w.\-]*):([A-Za-z_][\w.\-]*)(\s*=)", r"\1\2_\3\4", text)
    if not text.strip():
        raise ValueError("Tally sent an empty reply")
    return ET.fromstring(text)


def xml_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def collection_request(collection_type, fields, company="", from_date=None, to_date=None, computed=None):
    # Builds a Tally request for a list of masters, optionally for a period.
    variables = "<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
    if company:
        variables += "<SVCURRENTCOMPANY>" + xml_escape(company) + "</SVCURRENTCOMPANY>"
    if from_date:
        variables += '<SVFROMDATE TYPE="Date">' + from_date.strftime("%Y%m%d") + "</SVFROMDATE>"
    if to_date:
        variables += '<SVTODATE TYPE="Date">' + to_date.strftime("%Y%m%d") + "</SVTODATE>"
    methods = "".join("<NATIVEMETHOD>" + field + "</NATIVEMETHOD>" for field in fields)
    methods += "".join("<COMPUTE>" + item + "</COMPUTE>" for item in (computed or []))
    return ("<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>"
            "<TYPE>Collection</TYPE><ID>PyCollection</ID></HEADER><BODY><DESC><STATICVARIABLES>" + variables +
            "</STATICVARIABLES><TDL><TDLMESSAGE><COLLECTION NAME=\"PyCollection\" ISINITIALIZE=\"Yes\">"
            "<TYPE>" + collection_type + "</TYPE>" + methods + "</COLLECTION></TDLMESSAGE></TDL>"
            "</DESC></BODY></ENVELOPE>")


def item_name(element):
    # A master's name comes as NAME="..." and/or as <NAME.LIST><NAME>...</NAME></NAME.LIST>.
    name = element.get("NAME")
    if not name:
        found = element.find(".//NAME")
        name = found.text if found is not None else ""
    return (name or "").strip()


def child_text(element, tag):
    found = element.find(tag)
    return (found.text or "").strip() if found is not None and found.text else ""


def tally_error(reply):
    for tag in ("LINEERROR", "ERROR"):
        found = reply.find(".//" + tag)
        if found is not None and (found.text or "").strip():
            return found.text.strip()
    return ""


def get_companies(port):
    # Companies open in this Tally: {name: {"books_from", "fy_month", "fy_day", "period_from", "period_to"}}.
    request = collection_request("Company", ["Name", "StartingFrom", "BooksFrom"],
                                 computed=["PyPeriodFrom : $$SystemPeriodFrom", "PyPeriodTo : $$SystemPeriodTo"])
    reply = tally_request(port, request, timeout=4)
    if tally_error(reply) or reply.find(".//COMPANY") is None:
        # Some Tally releases reject the current-period formula - ask again without it.
        reply = tally_request(port, collection_request("Company", ["Name", "StartingFrom", "BooksFrom"]), timeout=4)
    companies = {}
    for element in reply.iter("COMPANY"):
        name = item_name(element)
        if not name:
            continue
        starting = parse_tally_date(child_text(element, "STARTINGFROM"))
        books = parse_tally_date(child_text(element, "BOOKSFROM")) or starting
        companies[name] = {
            "books_from": books,
            "fy_month": starting.month if starting else 4,           # India: April, unless Tally says otherwise
            "fy_day": starting.day if starting else 1,
            "period_from": parse_tally_date(child_text(element, "PYPERIODFROM")),
            "period_to": parse_tally_date(child_text(element, "PYPERIODTO")),
        }
    return companies


def ledger_balances(port, company, from_date, to_date, with_totals):
    # {ledger name: {"group", "reserved", "balance", "debits", "credits", "has_totals"}}
    fields = ["Name", "Parent", "ClosingBalance"] + (["DebitTotals", "CreditTotals"] if with_totals else [])
    reply = tally_request(port, collection_request("Ledger", fields, company, from_date, to_date), timeout=120)
    problem = tally_error(reply)
    if problem:
        raise ValueError("Tally said: " + problem)
    ledgers = {}
    for element in reply.iter("LEDGER"):
        name = item_name(element)
        if not name:
            continue
        debit_text, credit_text = child_text(element, "DEBITTOTALS"), child_text(element, "CREDITTOTALS")
        try:
            ledgers[name] = {"group": child_text(element, "PARENT"),
                             "reserved": element.get("RESERVEDNAME", "") or "",
                             "balance": to_number(child_text(element, "CLOSINGBALANCE")),
                             "debits": abs(to_number(debit_text)), "credits": abs(to_number(credit_text)),
                             "has_totals": bool(debit_text or credit_text)}
        except ValueError:
            raise ValueError("Ledger '" + name + "' has an amount Tally sent in an unexpected form:  balance '" +
                             child_text(element, "CLOSINGBALANCE") + "',  debits '" + debit_text + "',  credits '" +
                             credit_text + "'.  Send this message to get it fixed.")
    return ledgers


def revenue_groups(port, company):
    # Names of all groups/sub-groups that are income or expense groups.
    reply = tally_request(port, collection_request("Group", ["Name", "Parent", "IsRevenue"], company), timeout=60)
    parent_of, flag_of = {}, {}
    for element in reply.iter("GROUP"):
        name = item_name(element)
        if name:
            parent_of[name] = child_text(element, "PARENT")
            flag_of[name] = child_text(element, "ISREVENUE").lower()
    revenue = set()
    for name in parent_of:
        top, steps = name, 0                         # walk up to the primary group
        while parent_of.get(top) in parent_of and steps < 50:
            top, steps = parent_of[top], steps + 1
        if flag_of.get(top) in ("yes", "true"):
            revenue.add(name)
        elif flag_of.get(top, "") == "" and top.lower() in STANDARD_REVENUE_GROUPS:
            revenue.add(name)                        # flag not sent - use the standard group names
    return revenue


def is_profit_and_loss(name, details):
    if details["reserved"].lower().replace(" ", "") == "profit&lossa/c":
        return True
    return name.lower().replace(" ", "") == "profit&lossa/c" and details["group"].lower() in ("primary", "")


def stock_value(port, company, as_at):
    # Total inventory value per Tally as at a date (positive). None if Tally gives no stock items.
    reply = tally_request(port, collection_request("StockItem", ["Name", "ClosingValue"], company, as_at, as_at),
                          timeout=180)
    problem = tally_error(reply)
    if problem:
        raise ValueError("Tally said: " + problem)
    values = [to_number(child_text(item, "CLOSINGVALUE")) for item in reply.iter("STOCKITEM")]
    if not values:
        return None
    return abs(sum(values))


def tb_differences(rows):
    totals = totals_of(rows)
    return (round(totals["op_dr"] - totals["op_cr"], 2), round(totals["cl_dr"] - totals["cl_cr"], 2))


# =============================================================================
# PART 3 - BUILDING THE 6-COLUMN TRIAL BALANCE
# =============================================================================
def split_dr_cr(balance):
    # Negative = Debit, positive = Credit.
    balance = round(balance, 2)
    return (-balance if balance < 0 else 0.0), (balance if balance > 0 else 0.0)


def build_detailed_tb(closing, before, revenue, new_year, period_text, stock=None):
    # closing: balances as at To (with period totals); before: balances as at the day before From.
    # new_year: True when the period starts on the first day of the financial year.
    # stock: None, or inventory values (positive = asset) {"year_open", "before", "close"} - see stock_values().
    #   Tally's P&L A/c balance includes the change in stock, but stock itself is not a ledger. So the
    #   change in stock is taken out of the P&L A/c line and the year's Opening Stock is listed as a row -
    #   the usual (pre-closing) trial balance. Closing stock is reported in the notes.
    revenue_close = sum(d["balance"] for n, d in closing.items() if d["group"] in revenue)
    revenue_before = sum(d["balance"] for n, d in before.items() if d["group"] in revenue)
    notes, rows, net_only = [], [], 0

    for name, details in closing.items():
        is_revenue = details["group"] in revenue
        close = details["balance"]
        if new_year and is_revenue:
            opening = 0.0                                          # income/expense start each year at zero
        else:
            opening = before.get(name, {"balance": 0.0})["balance"]
        if is_profit_and_loss(name, details):
            close -= revenue_close                                 # remove profit-to-date (already in revenue ledgers)
            if not new_year:
                opening -= revenue_before
            if stock:
                close -= stock["close"] - stock["year_open"]       # remove the year's change in stock
                if not new_year:
                    opening -= stock["before"] - stock["year_open"]
            if abs(revenue_close) >= 0.005:
                notes.append("Profit & Loss A/c: the year's net " + ("profit " if revenue_close > 0 else "loss ") +
                             "to date of " + indian(abs(revenue_close)) + " is shown in the income/expense "
                             "ledgers, so it is excluded from the P&L A/c line (as in Tally's own TB).")
        debits, credits = details["debits"], details["credits"]
        # SELF-CHECK: opening (credit +) - debits + credits must equal closing.
        if not details["has_totals"] or abs(opening - debits + credits - close) > 0.01:
            movement = round(close - opening, 2)
            debits, credits = (-movement, 0.0) if movement < 0 else (0.0, movement)
            if abs(movement) >= 0.005 or details["has_totals"]:
                net_only += 1
        op_dr, op_cr = split_dr_cr(opening)
        cl_dr, cl_cr = split_dr_cr(close)
        rows.append({"name": name, "group": details["group"], "op_dr": op_dr, "op_cr": op_cr,
                     "pd_dr": round(debits, 2), "pd_cr": round(credits, 2), "cl_dr": cl_dr, "cl_cr": cl_cr})

    if stock:
        value = round(stock["year_open"], 2)
        rows.append({"name": "Opening Stock (from inventory)", "group": "Stock-in-Hand", "op_dr": value, "op_cr": 0.0,
                     "pd_dr": 0.0, "pd_cr": 0.0, "cl_dr": value, "cl_cr": 0.0})
        notes.append("Stock: Opening Stock " + indian(stock["year_open"]) + " is listed as a row; Closing Stock as at "
                     "the To date is " + indian(stock["close"]) + " (not part of the trial balance - it goes to "
                     "the P&L and Balance Sheet). Values as per Tally's inventory.  Net " +
                     ("profit" if revenue_close + stock["close"] - stock["year_open"] >= 0 else "loss") +
                     " for the year to date after the change in stock: " +
                     indian(abs(revenue_close + stock["close"] - stock["year_open"])) + ".")
    rows.sort(key=lambda r: (r["group"].lower(), r["name"].lower()))
    if net_only:
        notes.append(str(net_only) + " ledger(s) show NET period movement (Tally's period totals were not "
                     "available or did not tie up for them).")
    return {"rows": rows, "notes": notes, "period": period_text}


def is_zero_row(row):
    return all(abs(row[key]) < 0.005 for key in AMOUNT_KEYS)


def totals_of(rows):
    return {key: round(sum(r[key] for r in rows), 2) for key in AMOUNT_KEYS}


def visible_rows(search_text=""):
    # Rows after the zero-balance tick box, and (for the screen only) the search box.
    tb = state["tb"]
    if tb is None:
        return []
    rows = tb["rows"] if show_zero_var.get() else [r for r in tb["rows"] if not is_zero_row(r)]
    search_text = search_text.strip().lower()
    if search_text:
        rows = [r for r in rows if search_text in r["name"].lower() or search_text in r["group"].lower()]
    return rows


# =============================================================================
# PART 4 - EXPORTS
# =============================================================================
def export_excel(path, company, tb, rows):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Trial Balance"
    money = "[>=10000000]##\\,##\\,##\\,##0.00;[>=100000]##\\,##\\,##0.00;##,##0.00"   # Indian grouping
    bold, thin = Font(bold=True), Side(style="thin", color="9CA3AF")
    head_fill, head_font = PatternFill("solid", fgColor="0B3D91"), Font(bold=True, color="FFFFFF")

    sheet["A1"] = "Trial Balance - " + company
    sheet["A1"].font = Font(bold=True, size=14)
    sheet["A2"] = "Period: " + tb["period"] + "     Extracted from Tally on " + datetime.now().strftime("%d-%m-%Y %H:%M")
    sheet["A2"].font = Font(italic=True, color="6B7280")
    line = 3
    for note in tb["notes"]:
        sheet.cell(row=line, column=1, value="Note: " + note).font = Font(italic=True, color="B45309")
        line += 1
    header_row = line + 1
    for column, title in enumerate(["Name of Ledger", "Name of Group"] + AMOUNT_TITLES, start=1):
        cell = sheet.cell(row=header_row, column=column, value=title)
        cell.font, cell.fill = head_font, head_fill
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    first = header_row + 1
    row_number = first
    for r in rows:
        sheet.cell(row=row_number, column=1, value=r["name"])
        sheet.cell(row=row_number, column=2, value=r["group"])
        for offset, key in enumerate(AMOUNT_KEYS):
            sheet.cell(row=row_number, column=3 + offset, value=r[key] or None).number_format = money
        row_number += 1
    last = max(row_number - 1, first)
    total_row = row_number
    sheet.cell(row=total_row, column=1, value="TOTAL").font = bold
    for offset in range(6):
        letter = "CDEFGH"[offset]
        cell = sheet.cell(row=total_row, column=3 + offset,
                          value="=SUM(" + letter + str(first) + ":" + letter + str(last) + ")")
        cell.number_format, cell.font = money, bold
    for column in range(1, 9):
        sheet.cell(row=total_row, column=column).fill = PatternFill("solid", fgColor="E5E7EB")
        sheet.cell(row=total_row, column=column).border = Border(top=thin, bottom=thin)
    sheet.cell(row=total_row + 1, column=1, value="Difference (Dr - Cr)").font = bold
    for dr_letter, cr_letter, column in (("C", "D", 3), ("E", "F", 5), ("G", "H", 7)):
        cell = sheet.cell(row=total_row + 1, column=column,
                          value="=" + dr_letter + str(total_row) + "-" + cr_letter + str(total_row))
        cell.number_format, cell.font = money, bold
    for letter, width in zip("ABCDEFGH", (42, 28, 16, 16, 16, 16, 16, 16)):
        sheet.column_dimensions[letter].width = width
    sheet.freeze_panes = sheet.cell(row=first, column=3)
    sheet.auto_filter.ref = "A" + str(header_row) + ":H" + str(last)
    book.save(path)


def export_pdf(path, company, tb, rows):
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(path, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                                 topMargin=12 * mm, bottomMargin=12 * mm, title="Trial Balance - " + company)
    story = [Paragraph("<b>Trial Balance - " + xml_escape(company) + "</b>", styles["Title"]),
             Paragraph("Period: " + tb["period"] + " &nbsp;&nbsp; Extracted from Tally on " +
                       datetime.now().strftime("%d-%m-%Y %H:%M"), styles["Normal"])]
    for note in tb["notes"]:
        story.append(Paragraph("<i>Note: " + xml_escape(note) + "</i>", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    small = styles["Normal"].clone("small", fontSize=8, leading=9.5)
    data = [["Name of Ledger", "Name of Group"] + AMOUNT_TITLES]
    for r in rows:
        data.append([Paragraph(xml_escape(r["name"]), small), Paragraph(xml_escape(r["group"]), small)] +
                    [indian(r[key]) if r[key] else "" for key in AMOUNT_KEYS])
    totals = totals_of(rows)
    data.append(["TOTAL", ""] + [indian(totals[key]) for key in AMOUNT_KEYS])
    table_pdf = Table(data, repeatRows=1, colWidths=[70 * mm, 50 * mm] + [26 * mm] * 6)
    table_pdf.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BLUE)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F3F4F6")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E5E7EB")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
    ]))
    story.append(table_pdf)

    def page_number(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(landscape(A4)[0] - 10 * mm, 6 * mm, "Page " + str(doc.page))
    document.build(story, onFirstPage=page_number, onLaterPages=page_number)


# =============================================================================
# PART 4B - FIXED ASSET ADDITIONS (Tab 2)
# =============================================================================
#  Where the figures come from:
#   - Vouchers: Tally's Day Book for the period (cancelled and optional
#     vouchers are ignored).
#   - Fixed asset ledgers: every ledger under the "Fixed Assets" group and its
#     sub-groups. Only DEBITS to these ledgers are additions; credits (sales,
#     depreciation) are ignored for now.
#   - One row per voucher per fixed asset ledger.
#   - Repairs or other expense lines in the same voucher are NOT capitalised.
#     The voucher's GST and discount are shared out in proportion to each
#     line's value, so the asset row carries only its own share of tax.
#   - Invoice No = Supplier Invoice No (Tally's "Reference"); if blank, the
#     voucher number. Editable.
#   - Date of put to use = voucher date. Editable.
#   - Party = the creditor in the voucher; for a bank payment the bank ledger;
#     for a journal the other ledger credited.
#   - GSTN = the party ledger's GSTIN; if blank, the GSTIN on the voucher.
#   - Disc = any credit line whose ledger name contains "discount". Editable.
#   - ITC Availed = Yes if the voucher carries GST ledgers, else No. Editable.
#   - Net Total = Taxable + CGST + SGST + IGST - Disc.
#   - Amount Capitalised = Taxable - Disc if ITC = Yes, otherwise Net Total.
#   - No. of days used = (To date of the period - date of put to use) + 1.


FA_VOUCHER_FIELDS = ["Date", "VoucherNumber", "VoucherTypeName", "PartyLedgerName", "Reference", "PartyGSTIN",
                     "IsCancelled", "IsOptional", "MasterID", "Narration", "AllLedgerEntries", "LedgerEntries",
                     "AllInventoryEntries"]


def fa_request(company, from_date, to_date, collection, extra_tdl=""):
    # A voucher request for one period. The dates go inside the request itself, so Tally does not
    # fall back to its own current date (which is what the Day Book did - it sent one day only).
    variables = ("<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
                 "<SVCURRENTCOMPANY>" + xml_escape(company) + "</SVCURRENTCOMPANY>"
                 '<SVFROMDATE TYPE="Date">' + from_date.strftime("%Y%m%d") + "</SVFROMDATE>"
                 '<SVTODATE TYPE="Date">' + to_date.strftime("%Y%m%d") + "</SVTODATE>")
    methods = "".join("<NATIVEMETHOD>" + field + "</NATIVEMETHOD>" for field in FA_VOUCHER_FIELDS)
    return ("<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>"
            "<TYPE>Collection</TYPE><ID>PyFAVouchers</ID></HEADER><BODY><DESC><STATICVARIABLES>" + variables +
            "</STATICVARIABLES><TDL><TDLMESSAGE><COLLECTION NAME=\"PyFAVouchers\" ISINITIALIZE=\"Yes\">" +
            collection + methods + "</COLLECTION>" + extra_tdl + "</TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>")


def fa_filtered_request(company, from_date, to_date):
    # METHOD A: Tally itself keeps only vouchers with a line in a ledger under Fixed Assets
    # (a normal accounting line, or an item line allocated to a fixed asset ledger).
    formulae = ('<SYSTEM TYPE="Formulae" NAME="PyFAOnly">$$FilterCount:AllLedgerEntries:PyFALine &gt; 0 OR '
                "$$FilterCount:AllInventoryEntries:PyFAItem &gt; 0</SYSTEM>"
                '<SYSTEM TYPE="Formulae" NAME="PyFALine">$$IsLedOfGrp:$LedgerName:$$GroupFixedAssets</SYSTEM>'
                '<SYSTEM TYPE="Formulae" NAME="PyFAItem">$$FilterCount:AccountingAllocations:PyFALine &gt; 0'
                "</SYSTEM>")
    return fa_request(company, from_date, to_date, "<TYPE>Voucher</TYPE><FILTER>PyFAOnly</FILTER>", formulae)


def fa_ledger_request(company, ledger, from_date, to_date):
    # METHOD B: the vouchers of ONE ledger - same as opening that ledger in Tally.
    name = ledger.replace('"', "")
    return fa_request(company, from_date, to_date,
                      "<TYPE>Vouchers : Ledger</TYPE><CHILDOF>" + xml_escape('"' + name + '"') + "</CHILDOF>")


def month_chunks(from_date, to_date):
    # [(start, end), ...] one per calendar month, clipped to the period.
    chunks, current = [], from_date
    while current <= to_date:
        next_month = (current.replace(day=1) + timedelta(days=32)).replace(day=1)
        end = min(to_date, next_month - timedelta(days=1))
        chunks.append((current, end))
        current = end + timedelta(days=1)
    return chunks


def voucher_key(voucher):
    # Identifies a voucher so the same one is not counted twice.
    master_id = child_text(voucher, "MASTERID")
    if master_id:
        return "id:" + master_id
    return "|".join([child_text(voucher, "DATE"), child_text(voucher, "VOUCHERTYPENAME"),
                     child_text(voucher, "VOUCHERNUMBER"), str(sorted(voucher_lines(voucher)[0]))])


def group_chain_sets(port, company):
    # {group: top-level parent chain} so we can tell which groups sit under Fixed Assets / Duties & Taxes.
    reply = tally_request(port, collection_request("Group", ["Name", "Parent"], company), timeout=60)
    parent_of = {}
    for element in reply.iter("GROUP"):
        name = item_name(element)
        if name:
            parent_of[name] = child_text(element, "PARENT")

    def under(group, target):
        steps = 0
        while group and steps < 50:
            if group.lower() == target:
                return True
            group, steps = parent_of.get(group, ""), steps + 1
        return False
    return under


def ledger_masters(port, company):
    # {ledger: {"group", "gstin", "tax_type", "duty_head"}}
    reply = tally_request(port, collection_request("Ledger", ["Name", "Parent", "PartyGSTIN", "TaxType",
                                                              "GSTDutyHead"], company), timeout=120)
    masters = {}
    for element in reply.iter("LEDGER"):
        name = item_name(element)
        if name:
            masters[name] = {"group": child_text(element, "PARENT"), "gstin": child_text(element, "PARTYGSTIN"),
                             "tax_type": child_text(element, "TAXTYPE").lower(),
                             "duty_head": child_text(element, "GSTDUTYHEAD").lower()}
    return masters


def tax_kind(ledger, masters):
    # "cgst", "sgst", "igst", "cess" or "" - from Tally's GST settings, else from the ledger name.
    details = masters.get(ledger, {})
    head, name = details.get("duty_head", ""), ledger.lower().replace(" ", "")
    if "central" in head or "cgst" in name:
        return "cgst"
    if "state" in head or "ut tax" in head or "sgst" in name or "utgst" in name:
        return "sgst"
    if "integrated" in head or "igst" in name:
        return "igst"
    if "cess" in head or ("cess" in name and details.get("tax_type") == "gst"):
        return "cess"
    return ""


def lines_in(voucher, tag):
    found = []
    for entry in voucher.iter(tag):
        ledger = child_text(entry, "LEDGERNAME")
        if ledger:
            try:
                found.append((ledger, to_number(child_text(entry, "AMOUNT"))))
            except ValueError:
                pass
    return found


def voucher_lines(voucher):
    # The ledger lines of a voucher. Returns ([(ledger, amount)], balanced?) - negative amount = debit.
    # Tally stores lines in different sections depending on the voucher (accounting entries,
    # invoice-mode ledger entries, stock-item allocations). The same line can appear in more than
    # one section, so the first combination that adds up to zero is used - nothing missed or doubled.
    every = lines_in(voucher, "ALLLEDGERENTRIES.LIST")
    ledger = lines_in(voucher, "LEDGERENTRIES.LIST")
    allocations = lines_in(voucher, "ACCOUNTINGALLOCATIONS.LIST")
    for option in (every + allocations, ledger + allocations, every, ledger, every + ledger + allocations):
        if option and abs(sum(a for l, a in option)) <= 1:
            return option, True
    return (every + allocations) or (ledger + allocations), False


def fa_rows_from_vouchers(reply, masters, is_fixed_asset, from_date, to_date, kind_of=None):
    # Builds one row per voucher per fixed asset ledger debited.
    # Returns (rows, warnings, stats) - stats counts what Tally sent, for the on-screen diagnosis.
    rows, warnings, unbalanced = [], [], 0
    stats = {"vouchers": 0, "in_period": 0, "with_assets": 0, "asset_credits": 0.0, "outside": 0,
             "non_addition_debits": 0.0}
    for voucher in reply.iter("VOUCHER"):
        stats["vouchers"] += 1
        if child_text(voucher, "ISCANCELLED").lower() == "yes" or child_text(voucher, "ISOPTIONAL").lower() == "yes":
            continue
        voucher_date = parse_tally_date(child_text(voucher, "DATE"))
        if not voucher_date or not (from_date <= voucher_date <= to_date):
            stats["outside"] += 1
            continue
        stats["in_period"] += 1
        lines, balanced = voucher_lines(voucher)
        stats["asset_credits"] += sum(a for l, a in lines if a > 0 and is_fixed_asset(l))
        asset_lines = [(l, -a) for l, a in lines if a < 0 and is_fixed_asset(l)]      # debits to fixed assets
        if not asset_lines:
            continue
        if kind_of and is_profit_transfer(lines, kind_of):
            stats["non_addition_debits"] += sum(a for l, a in asset_lines)     # profit on sale moved out - not an addition
            continue
        stats["with_assets"] += 1
        if not balanced:
            unbalanced += 1

        taxes = {"cgst": 0.0, "sgst": 0.0, "igst": 0.0, "cess": 0.0}
        discount, base = 0.0, 0.0
        credits = []
        for ledger, amount in lines:
            kind = tax_kind(ledger, masters)
            if kind:
                taxes[kind] += -amount                                       # debit tax = positive input tax
            elif amount > 0 and "discount" in ledger.lower():
                discount += amount
            elif amount < 0 and "round" not in ledger.lower():
                base += -amount                                              # every debit line that tax relates to
            elif amount > 0 and "round" not in ledger.lower():
                credits.append((ledger, amount))
        has_gst = any(abs(taxes[k]) >= 0.005 for k in ("cgst", "sgst", "igst"))

        # Party: the voucher's party if it is on the credit side, else the biggest credit line.
        party = child_text(voucher, "PARTYLEDGERNAME")
        credit_names = [l for l, a in credits]
        if party not in credit_names:
            party = max(credits, key=lambda c: c[1])[0] if credits else party
        gstn = masters.get(party, {}).get("gstin", "") or child_text(voucher, "PARTYGSTIN")
        voucher_no = child_text(voucher, "VOUCHERNUMBER")
        invoice = child_text(voucher, "REFERENCE") or voucher_no

        for ledger, amount in asset_lines:
            share = amount / base if base else 1.0
            rows.append({"invoice": invoice, "put_date": voucher_date, "party": party, "description": "",
                         "gstn": gstn, "taxable": round(amount, 2),
                         "cgst": round(taxes["cgst"] * share, 2), "sgst": round(taxes["sgst"] * share, 2),
                         "igst": round(taxes["igst"] * share, 2), "disc": round(discount * share, 2),
                         "disc_auto": round(discount * share, 2),
                         "itc": "Yes" if has_gst else "No", "ledger": ledger,
                         "group": masters.get(ledger, {}).get("group", ""),
                         "voucher": child_text(voucher, "VOUCHERTYPENAME") + " " + voucher_no})
    rows.sort(key=lambda r: (r["put_date"], r["invoice"]))
    if unbalanced:
        warnings.append(str(unbalanced) + " voucher(s) did not add up to zero when read - check them in Tally.")
    stats["asset_credits"] = round(stats["asset_credits"], 2)
    return rows, warnings, stats


FA_COLUMNS = [  # (key, heading, width, editable)   - columns A to V follow the FAM Additions template
    ("sl", "Sl.no", 46, False), ("invoice", "Invoice No", 120, True), ("put_date", "Date Of Put to use", 92, True),
    ("party", "Party Name", 170, False), ("description", "Description", 140, True), ("gstn", "GSTN", 140, False),
    ("taxable", "Taxable Value", 100, False), ("cgst", "CGST", 80, False), ("sgst", "SGST", 80, False),
    ("igst", "IGST", 80, False), ("disc", "Disc", 70, True), ("net", "Net Total", 100, False),
    ("itc", "ITC Availed", 72, True), ("capitalised", "Amount to be Capitalised", 120, False),
    ("ledger", "Name of Ledger in Which it is capitalised", 180, False), ("days", "No. of Days Used", 55, False),
    ("asset_class", "Asset Class", 190, True), ("co_rate", "Rate of Depreciation as per Companies Act", 80, True),
    ("co_dep", "Depreciation as per Companies Act", 110, False), ("co_wdv", "WDV as on end of the year", 110, False),
    ("ge180", "Put to use 180 days or more", 110, False), ("lt180", "Put to use less than 180 days", 110, False),
    ("it_rate", "Income-tax Rate (block)", 80, True), ("it_dep", "Income-tax Depreciation on additions", 115, False),
    ("it_wdv", "Income-tax WDV of additions", 110, False)]
FA_MONEY = ["taxable", "cgst", "sgst", "igst", "disc", "net", "capitalised", "co_dep", "co_wdv", "ge180", "lt180",
            "it_dep", "it_wdv"]
FA_KEY_VIEW = ["sl", "invoice", "put_date", "party", "description", "capitalised", "ledger", "days", "asset_class",
               "ge180", "lt180", "co_dep", "it_dep"]

# Asset classes: (name, Companies Act WDV rate %, Income-tax block rate %, words that suggest the class).
# Companies Act rates = WDV rates for the Schedule II useful life with 5% residual value, i.e. 1 - 0.05^(1/life).
# Income-tax rates = Appendix I to the Income-tax Rules (block of assets). Both are editable per row.
ASSET_CLASSES = [
    ("Computers - end user devices (laptops, desktops)", 63.16, 40.0,
     ["computer", "laptop", "desktop", "macbook", "notebook", "printer", "monitor", "scanner", "ipad", "tablet", "cpu"]),
    ("Computers - servers and networks", 39.30, 40.0, ["server", "network", "router", "switch", "firewall", "nas"]),
    ("Computer software", 0.0, 40.0, ["software", "licence", "license", "erp", "tally"]),
    ("Office equipment", 45.07, 15.0,
     ["phone", "mobile", "iphone", "samsung", "purifier", "projector", "xerox", "photocopier", "camera", "cctv",
      "television", "tv", "refrigerator", "fridge", "watch", "speaker", "equipment", "office", "air conditioner",
      "ac", "water dispenser", "biometric", "epabx"]),
    ("Furniture and fittings", 25.89, 10.0,
     ["furniture", "fixture", "fitting", "chair", "table", "sofa", "cupboard",
      "interior", "partition", "rack", "workstation"]),
    ("Electrical installations and equipment", 25.89, 10.0, ["electrical", "wiring", "lighting", "ups"]),
    ("Plant and machinery - general", 18.10, 15.0, ["plant", "machinery", "machine", "tools", "generator", "dg"]),
    ("Motor cars", 31.23, 15.0, ["car", "vehicle", "motor"]),
    ("Motor cycles and scooters", 25.89, 15.0, ["bike", "scooter", "motorcycle", "two wheeler", "activa"]),
    ("Buildings - other than factory", 4.87, 10.0, ["building", "premises", "flat", "office space"]),
    ("Buildings - factory", 9.50, 10.0, ["factory building", "factory shed", "shed"]),
    ("Capital work-in-progress", 0.0, 0.0, ["cwip", "capital work in progress", "work in progress"]),
    ("Not classified", 0.0, 0.0, [])]
CLASS_RATES = {name: (co, it) for name, co, it, words in ASSET_CLASSES}
CLASS_FILE = os.path.join(SAVE_FOLDER, "fa_asset_classes.json")

# ---- Books depreciation depends on the type of entity
ENTITY_TYPES = ["Company (Pvt Ltd / Public / OPC)", "LLP", "Partnership Firm", "Proprietorship"]
METHOD_DAYS = "Days used (pro-rata)"
METHOD_IT = "Income-tax method (half rate if used < 180 days)"
BOOK_METHODS = [METHOD_DAYS, METHOD_IT]


def is_company(entity):
    return (entity or "").startswith("Company")


def guess_entity(company_name):
    # From the company's name in Tally. Only a starting point - the user confirms it.
    name = " " + re.sub(r"[^a-z0-9&]+", " ", (company_name or "").lower()) + " "
    if " llp " in name:
        return "LLP"
    if re.search(r" (private limited|pvt ltd|pvt|limited|ltd|opc) ", name):
        return ENTITY_TYPES[0]
    return "Partnership Firm"


def default_method(entity):
    # Companies: Schedule II, pro-rata for the days used. Firms, LLPs, proprietors: usually the Income-tax method.
    return METHOD_DAYS if is_company(entity) else METHOD_IT


def books_on_companies_act():
    return is_company(state.get("fa_entity")) and state.get("fa_method", METHOD_DAYS) == METHOD_DAYS


def default_books_rate(asset_class):
    # Companies Act (Schedule II) rate only for a company on the days-used method; otherwise the Income-tax rate.
    co, it = CLASS_RATES.get(asset_class, (0.0, 0.0))
    return co if books_on_companies_act() else it


def books_titles():
    # Full headings for the three books columns (template headings for a company on Schedule II).
    if books_on_companies_act():
        return {"co_rate": "Rate of Depreciation as per Companies Act", "co_dep": "Depreciation as per Companies Act",
                "co_wdv": "WDV as on end of the year"}
    basis = "days used" if state.get("fa_method") == METHOD_DAYS else "Income-tax method"
    return {"co_rate": "Rate of Depreciation as per Books (Income-tax rates)",
            "co_dep": "Depreciation as per Books (" + basis + ")", "co_wdv": "WDV as per Books at end of the year"}


def books_warning():
    # A caution where the books choice departs from the usual position for that entity.
    if is_company(state.get("fa_entity")) and state.get("fa_method") == METHOD_IT:
        return ("Caution: a company's books are governed by Schedule II to the Companies Act, 2013 - depreciation over "
                "the useful life, charged pro-rata for the period of use. Income-tax block rates and the half-rate "
                "rule are a tax concept; using them in a company's books needs justification under AS 10 / Ind AS 16 "
                "and may be an audit reporting point.")
    return ""


def load_settings(company):
    import json
    try:
        with open(CLASS_FILE, encoding="utf-8") as handle:
            return json.load(handle).get("__settings__", {}).get(company, {})
    except Exception:
        return {}


def save_settings(company, entity, method):
    import json
    try:
        with open(CLASS_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        data = {}
    data.setdefault("__settings__", {})[company] = {"entity": entity, "method": method}
    try:
        with open(CLASS_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1, ensure_ascii=False)
    except OSError:
        pass


def guess_class(ledger, group):
    # Picks an asset class from the ledger name, then from its group's name. "Not classified" if nothing fits.
    # Longer key words are tried first, so "factory building" wins over "building" and "computer" over "ac".
    pairs = sorted(((word, name) for name, co, it, words in ASSET_CLASSES for word in words), key=lambda p: -len(p[0]))
    for text in (ledger, group):
        plain = " ".join(re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split())
        for word, name in pairs:
            if re.search(r"\b" + re.escape(word) + r"s?\b", plain):
                return name
    return "Not classified"


def load_classes(company):
    # {ledger: class} remembered for this company (only names - no amounts are stored).
    try:
        import json
        with open(CLASS_FILE, encoding="utf-8") as handle:
            return json.load(handle).get(company, {})
    except Exception:
        return {}


def save_class(company, ledger, asset_class):
    import json
    try:
        with open(CLASS_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        data = {}
    data.setdefault(company, {})[ledger] = asset_class
    try:
        with open(CLASS_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1, ensure_ascii=False)
        return True
    except OSError:
        return False


def apply_classes(rows, company):
    # Gives every row its asset class (remembered choice first, else a guess) and the class rates.
    remembered = load_classes(company)
    for row in rows:
        row["asset_class"] = remembered.get(row["ledger"]) or guess_class(row["ledger"], row.get("group", ""))
        if row["asset_class"] not in CLASS_RATES:
            row["asset_class"] = "Not classified"
        row["class_source"] = "saved" if row["ledger"] in remembered else "guessed"
        row["co_rate"], row["it_rate"] = default_books_rate(row["asset_class"]), CLASS_RATES[row["asset_class"]][1]


def fa_compute(row, period_end, fy_days=None):
    # Fills in the worked-out columns for one row (called again after every edit).
    fy_days = fy_days or state.get("fa_fy_days") or 365
    row["net"] = round(row["taxable"] + row["cgst"] + row["sgst"] + row["igst"] - row["disc"], 2)
    row["capitalised"] = round(row["taxable"] - row["disc"], 2) if row["itc"] == "Yes" else row["net"]
    row["days"] = max((period_end - row["put_date"]).days + 1, 0)
    amount, full_year = row["capitalised"], row["days"] >= 180          # Sec 32: half rate if used < 180 days
    row["ge180"], row["lt180"] = (amount, 0.0) if full_year else (0.0, amount)
    row.setdefault("asset_class", "Not classified")
    row.setdefault("co_rate", 0.0)
    row.setdefault("it_rate", 0.0)
    if state.get("fa_method") == METHOD_IT:                              # books on the Income-tax method
        row["co_dep"] = round(amount * row["co_rate"] / 100 * (1 if full_year else 0.5), 2)
    else:                                                                 # books pro-rata by days used
        row["co_dep"] = round(amount * row["co_rate"] / 100 * row["days"] / fy_days, 2)
    row["co_wdv"] = round(amount - row["co_dep"], 2)
    row["it_dep"] = round(amount * row["it_rate"] / 100 * (1 if full_year else 0.5), 2)
    row["it_wdv"] = round(amount - row["it_dep"], 2)
    return row


def fa_reconciliation(rows, tb_debits):
    # tb_debits: total period debits to fixed asset ledgers as reported by Tally (None if not available).
    taxable = round(sum(r["taxable"] for r in rows), 2)
    capitalised = round(sum(r["capitalised"] for r in rows), 2)
    itc_not_availed = round(sum(r["cgst"] + r["sgst"] + r["igst"] for r in rows if r["itc"] == "No"), 2)
    discount = round(sum(r["disc"] for r in rows), 2)
    return {"tb_debits": tb_debits, "taxable": taxable, "capitalised": capitalised,
            "picked_gap": None if tb_debits is None else round(tb_debits - taxable, 2),
            "itc_not_availed": itc_not_availed, "discount": discount,
            "cap_gap": None if tb_debits is None else round(capitalised - tb_debits, 2)}


def fa_cell(row, key):
    # The text shown in the table / exports for one cell.
    value = row.get(key, "")
    if key in FA_MONEY:
        return indian(value) if value else ""
    if key in ("co_rate", "it_rate"):
        return ("%.2f" % value) if value else ""
    if key == "put_date":
        return value.strftime("%d-%m-%Y")
    return str(value)


def fa_notes():
    if books_on_companies_act():
        books = ("Books depreciation (Companies Act) = Amount capitalised x WDV rate x days used / days in the year. "
                 "Rates are the WDV rates for Schedule II useful lives with 5% residual value - confirm the method "
                 "(WDV/SLM) and useful lives the company has adopted.")
    elif state.get("fa_method") == METHOD_DAYS:
        books = ("Books depreciation = Amount capitalised x Income-tax rate x days used / days in the year "
                 "(entity: " + str(state.get("fa_entity")) + ").")
    else:
        books = ("Books depreciation follows the Income-tax method: Income-tax block rate, half the rate where the asset "
                 "is used for less than 180 days (entity: " + str(state.get("fa_entity")) + "). No statute prescribes "
                 "book depreciation for firms, LLPs or proprietors; AS 10 still applies to their accounts.")
    notes = [books,
             "Income-tax depreciation is on the ADDITIONS only, at the block rate; half the rate where the asset is put "
             "to use for less than 180 days in the year (Sec 32(1), second proviso). Block depreciation also needs the "
             "opening WDV and sales of each block, which are not part of this report.",
             "Asset classes are guessed from the ledger / group name unless chosen by the user; check every class and "
             "rate."]
    if books_warning():
        notes.insert(1, books_warning())
    return notes


def fa_class_summary(rows):
    # [(class, co_rate, it_rate, ge180, lt180, co_dep, it_dep)] in the order of ASSET_CLASSES.
    summary = []
    for name, co, it, words in ASSET_CLASSES:
        members = [r for r in rows if r["asset_class"] == name]
        if members:
            summary.append((name, default_books_rate(name), it, sum(r["ge180"] for r in members), sum(r["lt180"] for r in members),
                            sum(r["co_dep"] for r in members), sum(r["it_dep"] for r in members)))
    return summary


def export_fa_excel(path, company, period, rows, recon, period_end=None, fy_days=365):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "FAM Additions Details"
    money = "[>=10000000]##\\,##\\,##\\,##0.00;[>=100000]##\\,##\\,##0.00;##,##0.00"
    bold, thin = Font(bold=True), Side(style="thin", color="9CA3AF")
    header_fill, total_fill = PatternFill("solid", fgColor="0B3D91"), PatternFill("solid", fgColor="E5E7EB")
    sheet["A1"] = "Fixed Assets Additions Report - " + company
    sheet["A1"].font = Font(bold=True, size=14)
    sheet["F1"] = period
    sheet["F1"].font = bold
    sheet["S1"] = "Books: " + str(state.get("fa_entity")) + " - " + str(state.get("fa_method"))
    sheet["S1"].font = bold
    sheet["M1"], sheet["P1"] = "Period end", "Days in year"
    sheet["N1"], sheet["Q1"] = period_end or date.today(), fy_days
    sheet["N1"].number_format = "dd-mm-yyyy"
    for column, (key, title, width, editable) in enumerate(FA_COLUMNS, start=1):
        cell = sheet.cell(row=2, column=column, value=books_titles().get(key, title))
        cell.font, cell.fill = Font(bold=True, color="FFFFFF"), header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        sheet.column_dimensions[get_column_letter(column)].width = max(width / 7, 9)
    sheet.row_dimensions[2].height = 60
    # Columns L, N, P, S to Y are live formulas, so a change typed in Excel flows through.
    formulas = {"net": "=G{r}+H{r}+I{r}+J{r}-K{r}", "capitalised": '=IF(M{r}="Yes",G{r}-K{r},L{r})',
                "days": "=MAX($N$1-C{r}+1,0)", "co_dep": ("=ROUND(N{r}*R{r}/100*IF(P{r}>=180,1,0.5),2)" if state.get("fa_method") == METHOD_IT
                           else "=ROUND(N{r}*R{r}/100*P{r}/$Q$1,2)"), "co_wdv": "=N{r}-S{r}",
                "ge180": "=IF(P{r}>=180,N{r},0)", "lt180": "=IF(P{r}<180,N{r},0)",
                "it_dep": "=ROUND(N{r}*W{r}/100*IF(P{r}>=180,1,0.5),2)", "it_wdv": "=N{r}-X{r}"}
    first = 3
    for number, r in enumerate(rows, start=1):
        line = first + number - 1
        for column, (key, title, width, editable) in enumerate(FA_COLUMNS, start=1):
            if key in formulas:
                value = formulas[key].format(r=line)
            elif key == "sl":
                value = number
            else:
                value = r.get(key)
                if value in (0, 0.0, "") and key not in ("co_rate", "it_rate"):
                    value = None
            cell = sheet.cell(row=line, column=column, value=value)
            if key in FA_MONEY:
                cell.number_format = money
            elif key == "put_date":
                cell.number_format = "dd-mm-yyyy"
            elif key in ("co_rate", "it_rate"):
                cell.number_format = "0.00"
    total_line = first + len(rows)
    last = max(total_line - 1, first)
    sheet.cell(row=total_line, column=4, value="Total").font = bold
    for column, (key, title, width, editable) in enumerate(FA_COLUMNS, start=1):
        cell = sheet.cell(row=total_line, column=column)
        cell.fill, cell.border = total_fill, Border(top=thin, bottom=thin)
        if key in FA_MONEY:
            letter = get_column_letter(column)
            cell.value = "=SUM(" + letter + str(first) + ":" + letter + str(last) + ")"
            cell.number_format, cell.font = money, bold
    line = total_line + 2
    sheet.cell(row=line, column=4, value="Reconciliation with books").font = Font(bold=True, size=12)
    for label, value in fa_recon_lines(recon):
        line += 1
        sheet.cell(row=line, column=4, value=label)
        sheet.cell(row=line, column=7, value=value).number_format = money
    line += 2
    sheet.cell(row=line, column=4, value="Notes").font = bold
    for note in fa_notes():
        line += 1
        sheet.cell(row=line, column=4, value=note)
    sheet.freeze_panes = "C3"

    # Summary sheets - SUMIF formulas on the main sheet, so they follow any change made there.
    main = "'FAM Additions Details'!"
    rng = lambda letter: main + "$" + letter + "$" + str(first) + ":$" + letter + "$" + str(last)
    for title, key_letter, keys in (("Summary by Asset Class", "Q", [c[0] for c in fa_class_summary(rows)]),
                                    ("Summary by Ledger", "O", sorted({r["ledger"] for r in rows}))):
        summary = book.create_sheet(title)
        heads = [title.replace("Summary by ", ""), "Put to use 180 days or more", "Put to use less than 180 days",
                 "Total additions", "Books depreciation", "Income-tax depreciation on additions"]
        if key_letter == "Q":
            heads[1:1] = ["Books rate", "Income-tax rate"]
        summary["A1"] = title + " - " + company + " - " + period
        summary["A1"].font = Font(bold=True, size=13)
        for column, head in enumerate(heads, start=1):
            cell = summary.cell(row=3, column=column, value=head)
            cell.font, cell.fill = Font(bold=True, color="FFFFFF"), header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            summary.column_dimensions[get_column_letter(column)].width = 44 if column == 1 else 17
        summary.row_dimensions[3].height = 45
        for index, key in enumerate(keys):
            r = 4 + index
            summary.cell(row=r, column=1, value=key)
            column = 2
            if key_letter == "Q":
                summary.cell(row=r, column=2, value=default_books_rate(key)).number_format = "0.00"
                summary.cell(row=r, column=3, value=CLASS_RATES[key][1]).number_format = "0.00"
                column = 4
            for letter in ("U", "V"):
                summary.cell(row=r, column=column, value="=SUMIF(" + rng(key_letter) + ",$A" + str(r) + "," +
                             rng(letter) + ")").number_format = money
                column += 1
            summary.cell(row=r, column=column, value="=" + get_column_letter(column - 2) + str(r) + "+" +
                         get_column_letter(column - 1) + str(r)).number_format = money
            column += 1
            for letter in ("S", "X"):
                summary.cell(row=r, column=column, value="=SUMIF(" + rng(key_letter) + ",$A" + str(r) + "," +
                             rng(letter) + ")").number_format = money
                column += 1
        end = 4 + len(keys)
        summary.cell(row=end, column=1, value="Total").font = bold
        for column in range(2 if key_letter == "O" else 4, len(heads) + 1):
            letter = get_column_letter(column)
            cell = summary.cell(row=end, column=column, value="=SUM(" + letter + "4:" + letter + str(end - 1) + ")")
            cell.number_format, cell.font, cell.fill = money, bold, total_fill
        for offset, note in enumerate(fa_notes()[:-1]):
            summary.cell(row=end + 2 + offset, column=1, value=note)
        summary.freeze_panes = "B4"
    for title, heads, body, money_columns in fa_extra_tables():
        extra = book.create_sheet(title)
        extra["A1"] = title + " - " + company + " - " + period
        extra["A1"].font = Font(bold=True, size=13)
        for column, head in enumerate(heads, start=1):
            cell = extra.cell(row=3, column=column, value=head)
            cell.font, cell.fill = Font(bold=True, color="FFFFFF"), header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            extra.column_dimensions[get_column_letter(column)].width = 30 if column <= 6 and title.startswith("Del") or (
                column <= 2 and not title.startswith("Del")) else 16
        extra.row_dimensions[3].height = 45
        for index, values in enumerate(body):
            for column, value in enumerate(values, start=1):
                cell = extra.cell(row=4 + index, column=column, value=value)
                if column - 1 in money_columns and isinstance(value, (int, float)):
                    cell.number_format = money
                elif isinstance(value, date):
                    cell.number_format = "dd-mm-yyyy"
                if index == len(body) - 1:
                    cell.font, cell.fill = bold, total_fill
        for offset, note in enumerate(SCHEDULE_NOTES):
            extra.cell(row=6 + len(body) + offset, column=1, value=note)
        extra.freeze_panes = "A4"
    book.save(path)


def fa_extra_tables():
    # (title, headings, rows, money column indexes, total row?) for deletions, schedule and Income-tax blocks.
    tables = []
    entries = state.get("fa_entries", [])
    if entries:
        heads = ["Date", "Voucher", "Type", "Ledger", "Asset Class", "Other side", "Book value",
                 "Sale value (net of GST)", "GST on sale", "Profit / (Loss)", "Acc. dep. adjusted", "Narration"]
        body = [[e["date"], e["voucher"], e["type"], e["ledger"], e.get("asset_class", ""), e["party"], e["book"],
                 e["consideration"], e["gst"], e["pl"], e["accdep"], e.get("narration", "")] for e in entries]
        assets = [e for e in entries if not e.get("is_accdep") and e["type"] != E_EXCLUDED]
        total = ["", "", "", "Total (excl. acc. dep. and excluded)", "", ""] + [round(sum(e[k] for e in assets), 2) for k in
                                                                 ("book", "consideration", "gst", "pl", "accdep")] + [""]
        tables.append(("Deletions & Other Entries", heads, body + [total], [6, 7, 8, 9, 10]))
    schedule = state.get("fa_schedule", [])
    if schedule:
        heads = [t for k, t, w in SCHEDULE_COLUMNS]
        body = [[x[k] for k, t, w in SCHEDULE_COLUMNS] for x in schedule]
        assets = [x for x in schedule if not x.get("is_accdep")]
        total = ["Total (asset ledgers)", ""] + ["" if k in ("rate", "check") else round(sum((x[k] or 0) for x in assets), 2)
                                                 for k, t, w in SCHEDULE_COLUMNS[2:]]
        heads = [h.replace(" \u270e", "") for h in heads]
        tables.append(("Fixed Asset Sch - Books", heads, body + [total], list(range(2, len(heads) - 1))))
    blocks = state.get("fa_blocks", [])
    if blocks:
        keys = [k for k, t, w in BLOCK_COLUMNS]
        heads = [t.replace(" \u270e", "") for k, t, w in BLOCK_COLUMNS]
        body = [[b[k] for k in keys] for b in blocks]
        total = ["Total", ""] + [round(sum(b[k] for b in blocks), 2) for k in keys[2:-1]] + [""]
        tables.append(("Income-tax Blocks", heads, body + [total], list(range(2, len(heads) - 1))))
    return tables


SCHEDULE_NOTES = [
    "Schedule: Opening + Additions - Deletions - Transfers out - Depreciation booked in Tally = Closing worked out; "
    "this is compared with the closing balance in Tally. A difference means an entry was not read or was classified "
    "differently - check the ledger in Tally.",
    "Each entry is classified by the other side of the voucher: debtor/bank = sale; creditor = purchase return; Profit "
    "& Loss ledger = depreciation (if named so), loss on sale or write-off; Profit & Loss credit against an asset "
    "debit = profit on sale moved out (not an addition); another fixed asset = transfer.",
    "Books depreciation (app) = on the opening balance not sold (full period), on assets sold up to the date of sale "
    "(days method only) and on additions. It assumes the asset ledgers carry WDV (not gross cost).",
    "Income-tax blocks are grouped by type of asset and rate. Opening WDV must come from last year's tax computation / "
    "Form 3CD (entered here and saved); for firms on the Income-tax method it defaults to the books opening. Whether a "
    "block has ceased to exist (Sec 50(2)) cannot be seen from the books - confirm it."]


def fa_recon_lines(recon):
    lines = []
    if recon["tb_debits"] is not None:
        lines.append(("Period debits to Fixed Asset ledgers (as per books)", recon["tb_debits"]))
    lines.append(("Taxable value picked up in this report", recon["taxable"]))
    if recon["picked_gap"] is not None:
        lines.append(("Difference - not picked up (should be nil)", recon["picked_gap"]))
    lines.append(("Add: GST where ITC not availed", recon["itc_not_availed"]))
    lines.append(("Less: Discount", -recon["discount"]))
    lines.append(("Amount to be Capitalised", recon["capitalised"]))
    if recon["cap_gap"] is not None:
        lines.append(("Capitalised minus books (ITC not availed + discount adjustments)", recon["cap_gap"]))
    return lines


def pdf_table(data, widths, money_from, style_extra=()):
    table_pdf = Table(data, repeatRows=1, colWidths=[w * mm for w in widths])
    table_pdf.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BLUE)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (money_from, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F3F4F6")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E5E7EB")), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB"))] + list(style_extra)))
    return table_pdf


def export_fa_pdf(path, company, period, rows, recon, period_end=None, fy_days=365):
    from reportlab.lib.pagesizes import A3
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(path, pagesize=landscape(A3), leftMargin=8 * mm, rightMargin=8 * mm,
                                 topMargin=10 * mm, bottomMargin=10 * mm, title="Fixed Assets Additions - " + company)
    small = styles["Normal"].clone("small", fontSize=7.5, leading=9)
    para = lambda text: Paragraph(xml_escape(str(text)), small)
    head = lambda titles: [Paragraph('<font color="white"><b>' + xml_escape(t) + "</b></font>", small) for t in titles]
    total = lambda key: indian(sum(r[key] for r in rows))
    story = [Paragraph("<b>Fixed Assets Additions Report - " + xml_escape(company) + "</b>", styles["Title"]),
             Paragraph("Period: " + period + "  |  Entity: " + xml_escape(str(state.get("fa_entity"))) +
                       "  |  Books depreciation: " + xml_escape(str(state.get("fa_method"))), styles["Normal"]),
             Spacer(1, 4 * mm)]

    # 1. Additions register (template columns A to P)
    keys = [c[0] for c in FA_COLUMNS[:16]]
    data = [head([c[1] for c in FA_COLUMNS[:16]])]
    for number, r in enumerate(rows, start=1):
        data.append([str(number) if k == "sl" else para(fa_cell(r, k)) if k in ("party", "description", "ledger", "invoice")
                     else fa_cell(r, k) for k in keys])
    data.append(["", "", "", "Total", "", ""] + [total(k) for k in ("taxable", "cgst", "sgst", "igst", "disc", "net")] +
                ["", total("capitalised"), "", ""])
    story.append(pdf_table(data, [10, 30, 20, 42, 38, 30, 24, 19, 19, 19, 16, 24, 15, 26, 46, 14], 6,
                           [("ALIGN", (12, 1), (12, -1), "CENTER"), ("ALIGN", (14, 1), (14, -1), "LEFT")]))

    # 2. Depreciation on additions (template columns Q to V + Income-tax)
    story += [Spacer(1, 6 * mm), Paragraph("<b>Depreciation on additions</b>", styles["Heading3"])]
    keys = ["sl", "invoice", "put_date", "ledger", "asset_class", "capitalised", "days", "ge180", "lt180", "co_rate",
            "co_dep", "co_wdv", "it_rate", "it_dep", "it_wdv"]
    titles = dict({c[0]: c[1] for c in FA_COLUMNS}, **books_titles())
    data = [head([titles[k] for k in keys])]
    for number, r in enumerate(rows, start=1):
        data.append([str(number) if k == "sl" else para(fa_cell(r, k)) if k in ("invoice", "ledger", "asset_class")
                     else fa_cell(r, k) for k in keys])
    data.append(["", "", "", "Total", "", total("capitalised"), "", total("ge180"), total("lt180"), "",
                 total("co_dep"), total("co_wdv"), "", total("it_dep"), total("it_wdv")])
    story.append(pdf_table(data, [10, 32, 20, 52, 58, 27, 15, 27, 27, 17, 27, 27, 17, 27, 27], 5,
                           [("ALIGN", (2, 1), (2, -1), "LEFT")]))

    # 3. Summary by asset class
    story += [Spacer(1, 6 * mm), Paragraph("<b>Summary by asset class</b>", styles["Heading3"])]
    data = [head(["Asset class", "Books rate", "Income-tax rate", "Put to use 180 days or more",
                  "Put to use less than 180 days", "Total additions", "Books depreciation",
                  "Income-tax depreciation on additions"])]
    for name, co, it, ge, lt, cod, itd in fa_class_summary(rows):
        data.append([para(name), "%.2f" % co, "%.2f" % it, indian(ge), indian(lt), indian(ge + lt), indian(cod), indian(itd)])
    data.append(["Total", "", "", total("ge180"), total("lt180"), total("capitalised"), total("co_dep"), total("it_dep")])
    story.append(pdf_table(data, [80, 22, 22, 32, 32, 32, 32, 32], 1))

    # 4. Deletions, schedule and Income-tax blocks
    for title, heads, body, money_columns in fa_extra_tables():
        story += [Spacer(1, 6 * mm), Paragraph("<b>" + title + "</b>", styles["Heading3"])]
        data = [head(heads)]
        for values in body:
            data.append([para(v.strftime("%d-%m-%Y")) if isinstance(v, date) else
                         (indian(v) if v else "-") if i in money_columns and isinstance(v, (int, float)) else
                         para("" if v is None else v) for i, v in enumerate(values)])
        usable = 404.0
        widths = [usable / len(heads)] * len(heads)
        story.append(pdf_table(data, widths, 0, [("ALIGN", (0, 1), (-1, -1), "LEFT")] +
                               [("ALIGN", (i, 1), (i, -1), "RIGHT") for i in money_columns]))

    # 5. Reconciliation and notes
    story += [Spacer(1, 6 * mm), Paragraph("<b>Reconciliation with books</b>", styles["Heading3"])]
    recon_table = Table([[label, indian(value)] for label, value in fa_recon_lines(recon)], colWidths=[120 * mm, 35 * mm],
                        hAlign="LEFT")
    recon_table.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 9),
                                     ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.black)]))
    story += [recon_table, Spacer(1, 4 * mm), Paragraph("<b>Notes</b>", styles["Heading3"])]
    story += [Paragraph(str(n + 1) + ". " + xml_escape(note), styles["Normal"])
              for n, note in enumerate(fa_notes() + SCHEDULE_NOTES)]

    def page_number(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(landscape(A3)[0] - 8 * mm, 5 * mm, "Page " + str(doc.page))
    document.build(story, onFirstPage=page_number, onLaterPages=page_number)


# =============================================================================
# PART 4C - DELETIONS, OPENING-TO-CLOSING SCHEDULE, INCOME-TAX BLOCKS
# =============================================================================
#  Every entry in a fixed asset ledger is read by looking at the OTHER side of
#  the voucher:
#    - Debtor / bank / cash          -> Sale (sale value = that amount less GST)
#    - Creditor                      -> Purchase return / debit note
#    - Profit & Loss ledger (Dr)     -> Depreciation (if the ledger name says
#                                       "depreciation"), else Loss on sale (if the
#                                       asset was also sold) or Write-off / scrap
#    - Profit & Loss ledger (Cr), on a DEBIT to the asset -> Profit on sale
#                                       transfer (NOT an addition)
#    - Another fixed asset ledger    -> Transfer
#    - Accumulated depreciation      -> written back on sale
#    - Anything else                 -> "Other - check" (flagged for the user)
#  Validation per ledger: Opening + Additions - Deletions - Transfers -
#  Depreciation booked = Closing balance in Tally.

E_SALE, E_RETURN, E_TRANSFER, E_ACCDEP = "Sale", "Purchase return / debit note", "Transfer out", "Acc. dep. written back"
E_DEP, E_DEP_REV, E_LOSS, E_WRITEOFF = "Depreciation booked", "Depreciation reversed", "Loss on sale", "Write-off / scrap"
E_PROFIT, E_OTHER = "Profit on sale (transfer)", "Other - check"
E_EXCLUDED = "Excluded - adjusted in additions (Disc)"
ENTRY_TYPES = [E_SALE, E_RETURN, E_EXCLUDED, E_LOSS, E_WRITEOFF, E_PROFIT, E_DEP, E_DEP_REV, E_TRANSFER, E_ACCDEP,
               E_OTHER]
DELETION_TYPES = {E_SALE, E_RETURN, E_LOSS, E_WRITEOFF, E_PROFIT, E_ACCDEP, E_OTHER}    # reduce the asset (book value)
CONSIDERATION_TYPES = {E_SALE, E_OTHER}                                                   # reduce the Income-tax block
ACCDEP_WORDS = re.compile(r"deprec|accumulated|amortis|amortiz", re.I)

# Income-tax "block" = type of asset + rate (Appendix I). Electrical fittings sit with furniture.
IT_TYPE = {"Computers - end user devices (laptops, desktops)": "Plant & machinery",
           "Computers - servers and networks": "Plant & machinery", "Computer software": "Plant & machinery",
           "Office equipment": "Plant & machinery", "Plant and machinery - general": "Plant & machinery",
           "Motor cars": "Plant & machinery", "Motor cycles and scooters": "Plant & machinery",
           "Furniture and fittings": "Furniture & fittings", "Electrical installations and equipment": "Furniture & fittings",
           "Buildings - other than factory": "Buildings", "Buildings - factory": "Buildings",
           "Capital work-in-progress": "CWIP", "Not classified": "Not classified"}


def make_kind_of(masters, asset_ledgers, accdep_ledgers, under, revenue):
    # Returns kind_of(ledger): asset / accdep / tax / pl / bank / debtor / creditor / round / other.
    def kind_of(ledger):
        if ledger in asset_ledgers:
            return "asset"
        if ledger in accdep_ledgers:
            return "accdep"
        if "round" in ledger.lower():
            return "round"
        group = masters.get(ledger, {}).get("group", "")
        if tax_kind(ledger, masters) or under(group, "duties & taxes"):
            return "tax"
        if group in revenue:
            return "pl"
        if any(under(group, g) for g in ("bank accounts", "bank od a/c", "bank occ a/c", "cash-in-hand")):
            return "bank"
        if under(group, "sundry debtors"):
            return "debtor"
        if under(group, "sundry creditors"):
            return "creditor"
        return "other"
    return kind_of


def is_profit_transfer(lines, kind_of):
    # Dr Asset / Cr Profit & Loss ledger only (e.g. profit on sale moved out of the asset) - not an addition.
    debits_asset = any(a < 0 and kind_of(l) == "asset" for l, a in lines)
    credit_kinds = {kind_of(l) for l, a in lines if a > 0 and kind_of(l) != "round"}
    return debits_asset and credit_kinds == {"pl"}


def fa_entries_from_vouchers(reply, kind_of, from_date, to_date):
    # One entry per voucher per fixed asset (or accumulated depreciation) ledger that is NOT an addition.
    entries = []
    for voucher in reply.iter("VOUCHER"):
        if child_text(voucher, "ISCANCELLED").lower() == "yes" or child_text(voucher, "ISOPTIONAL").lower() == "yes":
            continue
        day = parse_tally_date(child_text(voucher, "DATE"))
        if not day or not (from_date <= day <= to_date):
            continue
        lines = voucher_lines(voucher)[0]
        kinds = [(l, a, kind_of(l)) for l, a in lines]
        number = child_text(voucher, "VOUCHERTYPENAME") + " " + child_text(voucher, "VOUCHERNUMBER")
        base = {"date": day, "voucher": number, "narration": child_text(voucher, "NARRATION")}
        debit = lambda *ks: sum(-a for l, a, k in kinds if a < 0 and k in ks)
        credit = lambda *ks: sum(a for l, a, k in kinds if a > 0 and k in ks)
        pl_debit_names = [l for l, a, k in kinds if a < 0 and k == "pl"]
        dep_named = any(ACCDEP_WORDS.search(l) for l in pl_debit_names + [l for l, a, k in kinds if k == "pl"])

        # Debits to an asset with only a P&L ledger on the other side: profit transfer / depreciation reversal.
        if is_profit_transfer(lines, kind_of):
            for l, a, k in kinds:
                if a < 0 and k == "asset":
                    pl_names = [x for x, y, z in kinds if y > 0 and z == "pl"]
                    entries.append(dict(base, type=E_DEP_REV if dep_named else E_PROFIT, ledger=l,
                                        party=", ".join(pl_names), book=round(a, 2), consideration=0.0, gst=0.0,
                                        pl=round(-a, 2), accdep=0.0))

        # Accumulated depreciation ledgers: depreciation credited, or written back on a sale.
        for l, a, k in kinds:
            if k == "accdep":
                kind = E_DEP if a > 0 else E_ACCDEP
                entries.append(dict(base, type=kind, ledger=l, party="", book=round(-a, 2) if a < 0 else round(a, 2),
                                    consideration=0.0, gst=0.0, pl=0.0, accdep=0.0, is_accdep=True))

        credits_to_assets = [(l, a) for l, a, k in kinds if a > 0 and k == "asset"]
        total = sum(a for l, a in credits_to_assets)
        if not total:
            continue
        received, from_creditor, other_side = debit("bank", "debtor"), debit("creditor"), debit("other")
        moved_to_asset, accdep_back, pl_debit = debit("asset"), debit("accdep"), debit("pl")
        gst, pl_net = credit("tax"), credit("pl") - pl_debit
        party_of = lambda ks: max(((l, -a) for l, a, k in kinds if a < 0 and k in ks), key=lambda x: x[1],
                                  default=("", 0))[0]
        if received > 0:
            kind, consideration, party = E_SALE, max(received - gst, 0.0), party_of(("bank", "debtor"))
        elif from_creditor > 0:
            kind, consideration, party = E_RETURN, 0.0, party_of(("creditor",))
        elif other_side > 0:
            kind, consideration, party = E_OTHER, max(other_side - gst, 0.0), party_of(("other",))
        elif moved_to_asset > 0 and not pl_debit:
            kind, consideration, party = E_TRANSFER, 0.0, party_of(("asset",))
        elif accdep_back > 0 and not pl_debit:
            kind, consideration, party = E_ACCDEP, 0.0, party_of(("accdep",))
        elif pl_debit > 0:
            kind = E_DEP if dep_named else E_WRITEOFF        # Write-off becomes "Loss on sale" if the asset was sold
            consideration, party = 0.0, party_of(("pl",))
        else:
            kind, consideration, party = E_OTHER, 0.0, ""
        for ledger, amount in credits_to_assets:
            share = amount / total
            entries.append(dict(base, type=kind, ledger=ledger, party=party, book=round(amount, 2),
                                consideration=round(consideration * share, 2), gst=round(gst * share, 2),
                                pl=round(pl_net * share, 2) if kind in (E_SALE, E_OTHER) else 0.0,
                                accdep=round(accdep_back * share, 2)))
    sold = {e["ledger"] for e in entries if e["type"] == E_SALE}
    for e in entries:
        if e["type"] == E_WRITEOFF and e["ledger"] in sold:
            e["type"] = E_LOSS
        if e["type"] in (E_LOSS, E_WRITEOFF):
            e["pl"] = -e["book"]
    entries.sort(key=lambda e: (e["date"], e["voucher"]))
    return entries


def ledger_class(ledger, group, rows, remembered):
    for r in rows:
        if r["ledger"] == ledger:
            return r["asset_class"]
    name = remembered.get(ledger) or guess_class(ledger, group)
    return name if name in CLASS_RATES else "Not classified"


def fa_schedule(rows, entries, balances, masters, company, from_date, to_date, fy_days):
    # Ledger-wise movement, validation against Tally's closing balance, and depreciation as worked out here.
    remembered = load_classes(company)
    period_days = (to_date - from_date).days + 1
    it_method = state.get("fa_method") == METHOD_IT
    ledgers = sorted(set(balances.get("asset_open", {})) | set(balances.get("asset_close", {})) |
                     {r["ledger"] for r in rows} | {e["ledger"] for e in entries if not e.get("is_accdep")})
    schedule = []
    for ledger in ledgers:
        mine = [e for e in entries if e["ledger"] == ledger and not e.get("is_accdep")]
        asset_class = ledger_class(ledger, masters.get(ledger, {}).get("group", ""), rows, remembered)
        rate = default_books_rate(asset_class)
        opening = balances.get("asset_open", {}).get(ledger, 0.0)
        closing_tally = balances.get("asset_close", {}).get(ledger)
        # A Disc typed by hand (e.g. a purchase return excluded from deletions) reduces the addition in the books.
        manual_disc = round(sum(max(r["disc"] - r.get("disc_auto", r["disc"]), 0) for r in rows if r["ledger"] == ledger), 2)
        additions = round(sum(r["taxable"] for r in rows if r["ledger"] == ledger) - manual_disc, 2)
        excluded = round(sum(e["book"] for e in mine if e["type"] == E_EXCLUDED), 2)
        deletions = round(sum(e["book"] for e in mine if e["type"] in DELETION_TYPES), 2)
        transfers = round(sum(e["book"] for e in mine if e["type"] == E_TRANSFER), 2)
        dep_booked = round(sum(e["book"] for e in mine if e["type"] in (E_DEP, E_DEP_REV)), 2)
        computed = round(opening + additions - deletions - transfers - dep_booked, 2)
        difference = None if closing_tally is None else round(computed - closing_tally, 2)
        # Depreciation as per this working: on the opening balance kept, on assets sold (to the date of sale,
        # days method only) and on additions (already worked out row by row).
        # Assets that left during the year (a purchase return relates to an addition, so it is left out here).
        # A profit moved out of the asset separately reduces the book value of what was sold.
        sold = [e for e in mine if e["type"] in DELETION_TYPES and e["book"] > 0 and e["type"] != E_RETURN]
        gross_sold = sum(e["book"] for e in sold)
        profit_moved = -sum(e["book"] for e in mine if e["type"] == E_PROFIT)
        scale = max(gross_sold - profit_moved, 0.0) / gross_sold if gross_sold else 0.0
        kept = max(opening - gross_sold * scale, 0.0)
        if it_method:
            on_opening, on_sold = kept * rate / 100, 0.0                # Income-tax method: none in year of sale
        else:
            on_opening = kept * rate / 100 * period_days / fy_days
            on_sold = sum(min(e["book"] * scale, opening) * rate / 100 * max((e["date"] - from_date).days, 0) / fy_days
                          for e in sold) if opening > 0 else 0.0
        on_additions = sum(r["co_dep"] for r in rows if r["ledger"] == ledger)
        app_dep = round(on_opening + on_sold + on_additions, 2)
        book_pl = round(sum(e["pl"] for e in mine if e["type"] in (E_SALE, E_OTHER, E_LOSS, E_WRITEOFF, E_PROFIT)), 2)
        app_closing = round(opening + additions - deletions - transfers - app_dep, 2)
        checks = []
        if asset_class == "Not classified":
            checks.append("Asset class not chosen - no depreciation worked out (double-click Asset Class)")
        if app_closing < -0.5:
            checks.append("Closing WDV is NEGATIVE - depreciation / deletions exceed the WDV; check the class, rate "
                          "and deletions")
        if difference is not None and abs(difference) >= 1:
            checks.append("Does not tie to Tally by " + indian(difference) +
                          (" - excluded purchase return " + indian(excluded) + " vs Disc entered " + indian(manual_disc)
                           if excluded or manual_disc else ""))
        elif excluded and abs(excluded - manual_disc) >= 1:
            checks.append("Excluded purchase return " + indian(excluded) + " but Disc entered in additions is " +
                          indian(manual_disc))
        if dep_booked and abs(dep_booked - app_dep) >= 1:
            checks.append("Depreciation booked differs from this working by " + indian(dep_booked - app_dep))
        schedule.append({"check": "; ".join(checks), "negative": app_closing < -0.5,"ledger": ledger, "asset_class": asset_class, "rate": rate, "opening": round(opening, 2),
                         "additions": additions, "deletions": deletions, "transfers": transfers,
                         "dep_booked": dep_booked, "computed": computed, "closing_tally": closing_tally,
                         "difference": difference, "app_dep": app_dep,
                         "dep_gap": round(dep_booked - app_dep, 2) if dep_booked else None,
                         "app_closing": app_closing,
                         "consideration": round(sum(e["consideration"] for e in mine if e["type"] in CONSIDERATION_TYPES), 2),
                         "book_pl": book_pl})
    for ledger in sorted(set(balances.get("accdep_open", {})) | set(balances.get("accdep_close", {}))):
        mine = [e for e in entries if e["ledger"] == ledger and e.get("is_accdep")]
        opening = balances.get("accdep_open", {}).get(ledger, 0.0)        # shown as a reduction (negative)
        booked = round(sum(e["book"] for e in mine if e["type"] == E_DEP), 2)
        back = round(sum(e["book"] for e in mine if e["type"] == E_ACCDEP), 2)
        computed = round(opening - booked + back, 2)
        closing_tally = balances.get("accdep_close", {}).get(ledger)
        schedule.append({"ledger": ledger, "asset_class": "Accumulated depreciation", "rate": 0.0, "opening": opening,
                         "additions": 0.0, "deletions": -back, "transfers": 0.0, "dep_booked": booked,
                         "computed": computed, "closing_tally": closing_tally,
                         "difference": None if closing_tally is None else round(computed - closing_tally, 2),
                         "app_dep": 0.0, "dep_gap": None, "app_closing": computed, "consideration": 0.0,
                         "book_pl": 0.0, "is_accdep": True, "negative": False,
                         "check": "" if closing_tally is None or abs(computed - closing_tally) < 1 else
                                  "Does not tie to Tally by " + indian(computed - closing_tally)})
    return schedule


def it_block_key(asset_class, rate):
    return IT_TYPE.get(asset_class, "Not classified") + " @ " + ("%g" % rate) + "%"


def fa_blocks(rows, entries, schedule, saved_openings):
    # Income-tax block working on the additions, sales and the opening WDV of each block.
    blocks = {}
    class_of = {s["ledger"]: s["asset_class"] for s in schedule}

    def block(asset_class, rate):
        key = it_block_key(asset_class, rate)
        return blocks.setdefault(key, {"block": key, "rate": rate, "opening": None, "ge180": 0.0, "lt180": 0.0,
                                       "returns": 0.0, "sales": 0.0, "book_opening": 0.0})
    for r in rows:
        b = block(r["asset_class"], r["it_rate"])
        b["ge180"] += r["ge180"]
        b["lt180"] += r["lt180"]
    for e in entries:
        if e.get("is_accdep") or e["ledger"] not in class_of:
            continue
        asset_class = class_of[e["ledger"]]
        b = block(asset_class, CLASS_RATES.get(asset_class, (0, 0))[1])
        if e["type"] in CONSIDERATION_TYPES:
            b["sales"] += e["consideration"]
        elif e["type"] == E_RETURN:
            b["returns"] += e["book"]
    for s in schedule:
        if not s.get("is_accdep") and s["opening"]:
            block(s["asset_class"], CLASS_RATES.get(s["asset_class"], (0, 0))[1])["book_opening"] += s["opening"]
    result = []
    for key in sorted(blocks):
        b = blocks[key]
        if key.startswith(("CWIP", "Not classified")):
            continue                     # work-in-progress is not a block; unclassified assets are flagged in the schedule
        if key in saved_openings:
            b["opening"], b["source"] = saved_openings[key], "entered"
        elif not is_company(state.get("fa_entity")) and state.get("fa_method") == METHOD_IT:
            b["opening"], b["source"] = round(b["book_opening"], 2), "books"     # books follow the tax method
        else:
            b["opening"], b["source"] = 0.0, "missing"
        wdv = round(b["opening"] + b["ge180"] + b["lt180"] - b["returns"] - b["sales"], 2)
        b["wdv"] = wdv
        flag = ""
        if wdv < 0:
            b["dep"], b["closing"], b["stcg"] = 0.0, 0.0, -wdv
            flag = "Sec 50(1): sale value exceeds the block - short-term capital gain " + indian(-wdv)
        else:
            half = min(b["lt180"], wdv)
            b["dep"] = round((wdv - half) * b["rate"] / 100 + half * b["rate"] / 200, 2)
            b["closing"], b["stcg"] = round(wdv - b["dep"], 2), 0.0
            if wdv == 0 and b["sales"]:
                flag = "Block nil after sale - check whether the block ceased to exist (Sec 50(2))"
        if b["source"] == "missing":
            flag = ("Enter the opening WDV from last year's tax computation / Form 3CD. " + flag).strip()
        b["flag"] = flag
        result.append(b)
    return result


def load_it_openings(company, period):
    import json
    try:
        with open(CLASS_FILE, encoding="utf-8") as handle:
            return json.load(handle).get("__it_opening__", {}).get(company, {}).get(period, {})
    except Exception:
        return {}


def save_it_opening(company, period, block_key, value):
    import json
    try:
        with open(CLASS_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        data = {}
    data.setdefault("__it_opening__", {}).setdefault(company, {}).setdefault(period, {})[block_key] = value
    try:
        with open(CLASS_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1, ensure_ascii=False)
        return True
    except OSError:
        return False


# ---- Rate master: asset classes and rates can be changed by the user (e.g. when the law changes)
RATE_FILE = os.path.join(SAVE_FOLDER, "fa_rate_master.json")
DEFAULT_MASTER = [{"name": n, "co": co, "it": it, "it_type": IT_TYPE.get(n, "Plant & machinery"), "words": list(w)}
                  for n, co, it, w in ASSET_CLASSES]
FIXED_CLASSES = ("Capital work-in-progress", "Not classified")
IT_TYPES = ["Plant & machinery", "Furniture & fittings", "Buildings", "Intangible assets", "Ships", "CWIP",
            "Not classified"]


def apply_rate_master(master):
    # Replaces the class list and rates used everywhere in the app.
    master = [dict(m) for m in master if m.get("name")]
    for fixed in FIXED_CLASSES:
        if fixed not in [m["name"] for m in master]:
            master.append(next(dict(m) for m in DEFAULT_MASTER if m["name"] == fixed))
    ASSET_CLASSES[:] = [(m["name"], float(m["co"]), float(m["it"]), list(m.get("words", []))) for m in master]
    CLASS_RATES.clear()
    CLASS_RATES.update({m["name"]: (float(m["co"]), float(m["it"])) for m in master})
    IT_TYPE.clear()
    IT_TYPE.update({m["name"]: m.get("it_type") or "Plant & machinery" for m in master})


def current_master():
    return [{"name": n, "co": co, "it": it, "it_type": IT_TYPE.get(n, ""), "words": list(w)}
            for n, co, it, w in ASSET_CLASSES]


def load_rate_master():
    import json
    try:
        with open(RATE_FILE, encoding="utf-8") as handle:
            master = json.load(handle)
        if isinstance(master, list) and master:
            apply_rate_master(master)
    except Exception:
        pass                                            # no file yet (or unreadable) - standard rates are used


def save_rate_master(master):
    import json
    with open(RATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(master, handle, indent=1, ensure_ascii=False)


load_rate_master()


# =============================================================================
# PART 4D - SALES RECONCILIATION (books vs GSTR-1 / 1A vs GSTR-3B)
# =============================================================================
#  Books: every voucher touching a ledger under Sales Accounts, Direct Incomes or
#  Indirect Incomes, plus sales of fixed assets (read with the Fixed Asset
#  logic). One row per invoice, in the column order of the user's GST register
#  ("Sales Register" sheet, columns A to Z).

SR_CATEGORIES = [  # (category, nature of supply, GSTR-9 table) - exactly as in the GST register's lists
    ("B2C", "Taxable supply", "4(A)"), ("B2B", "Taxable supply", "4(B)"),
    ("Export with payment of Tax", "Exports", "4(C)"), ("SEZ with payment of Tax", "Exports", "4(D)"),
    ("Deemed exports(EOU)", "Deemed Exports", "4(E)"),
    ("Inward supplies on which tax is to be paid on the reverse", "Reverse Charge Supplies", "4(G)"),
    ("Registered Credit Note", "Taxable supply", "4(I)"),
    ("Amendments (-) of Supplies with tax payments", "Taxable supply", "4(K)"),
    ("Debit notes", "Taxable supply", "4(J)"), ("Amendments (+) of Supplies with tax payments", "Taxable supply", "4(L)"),
    ("Zero rated supply (Export) without payment of tax", "Exports", "5(A)"),
    ("Supply to SEZs without payment of tax", "Exports", "5(B)"), ("Exempted", "Exempted Supply", "5(D)"),
    ("Nil Rated", "Nil Rated Supply", "5(E)"),
    ("Non-GST supply (includes ‘no supply’)", "Non Taxable supply", "5(F)"),
    ("Credit Note - Exports/Deemed Exports", "Non Taxable supply", "5(H)"),
    ("Amendments (-) of without tax payments", "Non Taxable supply", "5(J)"),
    ("Debit Note - Exports/Deemed Exports", "Non Taxable supply", "5(I)"),
    ("Amendments (+) of without tax payments", "Non Taxable supply", "5(K)"),
    ("Invoice/Debit Note/Amendment(+)  of CY declared in next Financial year", "Taxable supply/Non Taxable supply", 10),
    ("Credit Note/Amendment(-)  of CY declared in next Financial year", "Taxable supply/Non Taxable supply", 11)]
SR_CAT_NAMES = [c[0] for c in SR_CATEGORIES]
SR_GSTR9 = {c[0]: c[2] for c in SR_CATEGORIES}
(C_B2C, C_B2B, C_EXP_WP, C_SEZ_WP, C_DEEMED, C_RCM, C_REG_CN, C_AMD_MINUS, C_DN, C_AMD_PLUS, C_EXP_WOP, C_SEZ_WOP,
 C_EXEMPT, C_NIL, C_NONGST, C_CN_EXP, C_AMD_MINUS_NT, C_DN_EXP, C_AMD_PLUS_NT, C_NEXT_PLUS, C_NEXT_MINUS) = SR_CAT_NAMES
SR_CURRENCIES = ["Euro", "US Dollars", "Swiss Franks", "Australlian Dollars", "New Zealand Dollars", "UAE Dirhams",
                 "Omani Riyals", "Saudi Riyals", "Singaporean Dollars", "Hong Kong Dollars"]
CURRENCY_HINTS = [("euro", "Euro"), ("eur", "Euro"), ("€", "Euro"), ("swiss", "Swiss Franks"), ("chf", "Swiss Franks"),
                  ("austral", "Australlian Dollars"), ("aud", "Australlian Dollars"), ("zealand", "New Zealand Dollars"),
                  ("nzd", "New Zealand Dollars"), ("dirham", "UAE Dirhams"), ("aed", "UAE Dirhams"),
                  ("omani", "Omani Riyals"), ("omr", "Omani Riyals"), ("saudi", "Saudi Riyals"), ("sar", "Saudi Riyals"),
                  ("singapor", "Singaporean Dollars"), ("sgd", "Singaporean Dollars"), ("hong", "Hong Kong Dollars"),
                  ("hkd", "Hong Kong Dollars"), ("us dollar", "US Dollars"), ("usd", "US Dollars"), ("$", "US Dollars")]
RULE42_TAXABLE, RULE42_EXEMPT = "Specific Credit - Taxable Supply", "Exempted"
STANDARD_RATES = [0.1, 0.25, 1, 1.5, 3, 5, 6, 7.5, 12, 18, 28, 40]
STATE_CODES = {"01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
               "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
               "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
               "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
               "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
               "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra", "29": "Karnataka", "30": "Goa",
               "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
               "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
               "97": "Other Territory"}
INCOME_GROUPS = ("sales accounts", "direct incomes", "indirect incomes")
SR_FILE = os.path.join(SAVE_FOLDER, "sales_recon_data.json")

# Columns of the Sales Register (A..Z) - key, heading, width in the app
SR_COLUMNS = [("month_paid", "Month Paid (3B)", 80), ("category", "Category", 190), ("nature", "Nature of Supply", 110),
              ("status", "Invoice Status", 80), ("rejected", "Invoice Rejected Month", 80), ("invoice", "Invoice No", 100),
              ("party", "Party Name", 200), ("gstin", "GSTN of Recipient", 135), ("inv_date", "Date of Invoice", 85),
              ("inv_value", "Invoice Value", 105), ("rate", "Rate of Tax", 60), ("taxable", "Taxable Value", 105),
              ("igst", "IGST", 85), ("cgst", "CGST", 85), ("sgst", "SGST", 85), ("state", "State of supply", 110),
              ("error", "Error Check", 90), ("gstr1", "GSTR1", 50), ("gstr9", "GSTR9", 50),
              ("fx_amount", "Foreign Amount ", 95), ("fx_rate", "Exchange rate", 75), ("fx_currency", "Nature of currency", 105),
              ("orig_no", "Original Invoice No.", 100), ("orig_date", "Original Invoice Date", 90),
              ("rule42", "Rule 42 Categorisation", 170), ("remark", "Remark", 260)]
SR_EXTRA = [("vtype", "Voucher Type", 110), ("ledger", "Sales Ledger in Tally", 180), ("cess", "Cess", 70)]
SR_MONEY = ["inv_value", "taxable", "igst", "cgst", "sgst", "fx_amount", "cess"]


def sr_load(company, fy_label):
    # Saved per company and FY: Month Paid / category changes, party classes, year-bucket items.
    import json
    try:
        with open(SR_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        data = {}
    data.setdefault("template", "")
    book = data.setdefault("companies", {}).setdefault(company, {})
    year = book.setdefault(fy_label, {})
    for key in ("month_paid", "category", "buckets"):
        year.setdefault(key, {} if key != "buckets" else [])
    book.setdefault("party_class", {})
    return data


def sr_save(data):
    import json
    try:
        with open(SR_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1, ensure_ascii=False, default=str)
        return True
    except OSError:
        return False


def sr_request(company, from_date, to_date, collection, fields, extra_tdl=""):
    variables = ("<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
                 "<SVCURRENTCOMPANY>" + xml_escape(company) + "</SVCURRENTCOMPANY>"
                 '<SVFROMDATE TYPE="Date">' + from_date.strftime("%Y%m%d") + "</SVFROMDATE>"
                 '<SVTODATE TYPE="Date">' + to_date.strftime("%Y%m%d") + "</SVTODATE>")
    methods = "".join("<NATIVEMETHOD>" + field + "</NATIVEMETHOD>" for field in fields)
    return ("<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>"
            "<TYPE>Collection</TYPE><ID>PySRVouchers</ID></HEADER><BODY><DESC><STATICVARIABLES>" + variables +
            "</STATICVARIABLES><TDL><TDLMESSAGE><COLLECTION NAME=\"PySRVouchers\" ISINITIALIZE=\"Yes\">" +
            collection + methods + "</COLLECTION>" + extra_tdl + "</TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>")


def sr_filtered_request(company, from_date, to_date, fields):
    # Tally picks out vouchers with a line in a ledger under Sales Accounts / Direct Incomes / Indirect Incomes.
    line = ('$$IsLedOfGrp:$LedgerName:"Sales Accounts" OR $$IsLedOfGrp:$LedgerName:"Direct Incomes" OR '
            '$$IsLedOfGrp:$LedgerName:"Indirect Incomes"')
    formulae = ('<SYSTEM TYPE="Formulae" NAME="PySROnly">$$FilterCount:AllLedgerEntries:PySRLine &gt; 0 OR '
                "$$FilterCount:AllInventoryEntries:PySRItem &gt; 0</SYSTEM>"
                '<SYSTEM TYPE="Formulae" NAME="PySRLine">' + xml_escape(line) + "</SYSTEM>"
                '<SYSTEM TYPE="Formulae" NAME="PySRItem">$$FilterCount:AccountingAllocations:PySRLine &gt; 0</SYSTEM>')
    return sr_request(company, from_date, to_date, "<TYPE>Voucher</TYPE><FILTER>PySROnly</FILTER>", fields, formulae)


def sr_ledger_request(company, ledger, from_date, to_date, fields):
    name = ledger.replace('"', "")
    return sr_request(company, from_date, to_date, "<TYPE>Vouchers : Ledger</TYPE><CHILDOF>" +
                      xml_escape('"' + name + '"') + "</CHILDOF>", fields)


def unknown_method(problem):
    # Name of the field Tally says it does not know, from its error text (or "").
    found = re.search(r"(?:method|field|function)\s*['\"]?([A-Za-z][A-Za-z0-9]*)", problem or "", re.I)
    return found.group(1) if found else ""


def read_adaptive(port, make_request, fields, optional, timeout=120):
    # Sends the request; if Tally rejects an optional field, drops it and tries again.
    # Returns (reply, error, fields actually used). Optional fields are not known in every Tally version.
    fields = list(fields)
    for attempt in range(len(optional) + 2):
        reply, error = read_vouchers(port, make_request(fields), timeout)
        if reply is not None:
            return reply, "", fields
        culprit = unknown_method(error)
        if culprit and culprit in fields and culprit in optional:
            fields.remove(culprit)
            continue
        dropped = [f for f in fields if f in optional]
        if dropped and "Tally said" in error:
            fields = [f for f in fields if f not in optional]                # unknown cause: drop all optional fields
            continue
        return None, error, fields
    return None, "Tally kept rejecting the request", fields


LEDGER_EXTRA = ["GSTRegistrationType", "CountryName", "LedStateName", "CountryOfResidence", "IsOtherTerritoryAssessee",
                "GSTTypeOfSupply", "Taxability", "RateOfTaxCalculation", "GSTNatureOfSupply", "LedGSTRegDetails",
                "LedMailingDetails"]
VOUCHER_EXTRA = ["PlaceOfSupply", "StateName", "CountryOfResidence", "ReferenceDate", "GSTRegistrationType"]


def sr_ledger_masters(port, company):
    # Ledger masters with the GST / address details the classification needs (whatever this Tally provides).
    base = ["Name", "Parent", "PartyGSTIN", "TaxType", "GSTDutyHead"]
    make = lambda fields: collection_request("Ledger", fields, company)
    reply, error, used = read_adaptive(port, make, base + LEDGER_EXTRA, LEDGER_EXTRA, timeout=180)
    if reply is None:
        raise ValueError("Ledger masters could not be read: " + error)
    masters = {}
    for element in reply.iter("LEDGER"):
        name = item_name(element)
        if not name:
            continue
        info = {"group": child_text(element, "PARENT"), "gstin": child_text(element, "PARTYGSTIN"),
                "tax_type": child_text(element, "TAXTYPE").lower(), "duty_head": child_text(element, "GSTDUTYHEAD").lower(),
                "regtype": child_text(element, "GSTREGISTRATIONTYPE"), "country": child_text(element, "COUNTRYNAME") or
                child_text(element, "COUNTRYOFRESIDENCE"), "state": child_text(element, "LEDSTATENAME"),
                "other_territory": child_text(element, "ISOTHTERRITORYASSESSEE").lower() == "yes",
                "taxability": (child_text(element, "TAXABILITY") or child_text(element, "GSTNATUREOFSUPPLY")).lower(),
                "rate": child_text(element, "RATEOFTAXCALCULATION")}
        for detail in element.iter("LEDGSTREGDETAILS.LIST"):            # newer TallyPrime keeps GST details here
            info["regtype"] = info["regtype"] or child_text(detail, "GSTREGISTRATIONTYPE")
            info["gstin"] = info["gstin"] or child_text(detail, "GSTIN")
            info["state"] = info["state"] or child_text(detail, "STATE") or child_text(detail, "PLACEOFSUPPLY")
        for detail in element.iter("LEDMAILINGDETAILS.LIST"):
            info["state"] = info["state"] or child_text(detail, "STATE")
            info["country"] = info["country"] or child_text(detail, "COUNTRY")
        masters[name] = info
    return masters, [f for f in LEDGER_EXTRA if f in used]


def voucher_type_bases(port, company):
    # {voucher type: base type in lower case} - e.g. "Sales GST" -> "sales".
    try:
        reply = tally_request(port, collection_request("VoucherType", ["Name", "Parent"], company), timeout=60)
    except Exception:
        return {}
    parent = {}
    for element in reply.iter("VOUCHERTYPE"):
        name = item_name(element)
        if name:
            parent[name] = child_text(element, "PARENT")
    bases = {}
    for name in parent:
        current, steps = name, 0
        while parent.get(current) and parent.get(current) != current and steps < 20:
            current, steps = parent[current], steps + 1
        bases[name] = current.lower()
    return bases


def currency_names(port, company):
    # {symbol: formal name} from Tally's currency masters.
    names = {}
    try:
        make = lambda fields: collection_request("Currency", fields, company)
        reply, error, used = read_adaptive(port, make, ["Name", "MailingName", "ExpandedSymbol", "OriginalName"],
                                           ["MailingName", "ExpandedSymbol", "OriginalName"], timeout=60)
        for element in (reply.iter("CURRENCY") if reply is not None else []):
            symbol = item_name(element)
            names[symbol] = " ".join(x for x in (child_text(element, "MAILINGNAME"), child_text(element, "EXPANDEDSYMBOL"),
                                                 child_text(element, "ORIGINALNAME")) if x)
    except Exception:
        pass
    return names


FOREX = re.compile(r"(-?)\s*([^\d\s@=-][^\d@=]*?)?\s*([\d,]+(?:\.\d+)?)\s*@\s*[^\d]*([\d,]+(?:\.\d+)?)\s*/\s*([^\s=]+)\s*=")


def parse_forex(text):
    # "-$1,000.00 @ ₹83.00/$ = -₹83,000.00" -> ("$", 1000.0, 83.0); None if not a foreign currency amount.
    if not text or "@" not in text or "=" not in text:
        return None
    found = FOREX.search(text)
    if not found:
        return None
    symbol = (found.group(2) or found.group(5) or "").strip()
    return symbol, float(found.group(3).replace(",", "")), float(found.group(4).replace(",", ""))


def currency_label(symbol, formal):
    text = (formal + " " + symbol).lower()
    for hint, name in CURRENCY_HINTS:
        if hint in text:
            return name
    return formal or symbol


def tax_rates_of(ledgers, masters):
    # Rates from the tax ledgers (master rate, else a "9%" in the name). Returns totals, e.g. {18.0}.
    totals = set()
    for ledger in ledgers:
        kind = tax_kind(ledger, masters)
        if kind not in ("igst", "cgst", "sgst"):
            continue
        rate = 0.0
        try:
            rate = float(str(masters.get(ledger, {}).get("rate", "") or 0))
        except ValueError:
            rate = 0.0
        if not rate:
            found = re.search(r"(\d+(?:\.\d+)?)\s*%", ledger)
            rate = float(found.group(1)) if found else 0.0
        if rate:
            totals.add(round(rate * (2 if kind in ("cgst", "sgst") else 1), 2))
    return totals


def nearest_rate(effective):
    best = min(STANDARD_RATES, key=lambda r: abs(r - effective))
    return best if abs(best - effective) <= 0.15 else None


def month_start(day):
    return date(day.year, day.month, 1)


def party_class_of(party, info, voucher_info, income_ledgers_used, forex_used):
    # B2B / B2C / EXPORT / SEZ / DEEMED from the party master (and the voucher), as far as Tally tells us.
    text = " ".join([info.get("regtype", ""), voucher_info.get("regtype", "")]).lower()
    country = (info.get("country") or voucher_info.get("country") or "").strip().lower()
    place = (voucher_info.get("place") or "").lower()
    names = " ".join(income_ledgers_used).lower()
    if "sez" in text or re.search(r"\bsez\b", names):
        return "SEZ", "registration type / ledger"
    if "deemed" in text:
        return "DEEMED", "registration type"
    if (country and country != "india") or "overseas" in text or "other territory" in place or "outside" in place \
            or info.get("other_territory") or re.search(r"export", names) or forex_used:
        return "EXPORT", "country / place of supply / ledger name / foreign currency"
    gstin = voucher_info.get("gstin") or info.get("gstin")
    if gstin and re.fullmatch(r"\d{2}[A-Z0-9]{13}", gstin.replace(" ", "").upper()):
        return "B2B", "GSTIN"
    return "B2C", "no GSTIN"


def category_for(party_class, doc, has_tax, nontax_kind):
    # doc: "INV", "CN" or "DN". nontax_kind: "Exempted" / "Nil Rated" / "Non-GST" (used when no tax is charged).
    if party_class in ("EXPORT", "SEZ", "DEEMED"):
        if doc == "CN":
            return C_CN_EXP
        if doc == "DN":
            return C_DN_EXP
        if party_class == "EXPORT":
            return C_EXP_WP if has_tax else C_EXP_WOP
        if party_class == "SEZ":
            return C_SEZ_WP if has_tax else C_SEZ_WOP
        return C_DEEMED
    if not has_tax:
        return {"Exempted": C_EXEMPT, "Nil Rated": C_NIL}.get(nontax_kind, C_NONGST)
    if party_class == "B2B":
        return C_REG_CN if doc == "CN" else C_DN if doc == "DN" else C_B2B
    return C_B2C


CLASS_OF_CATEGORY = {C_B2B: "B2B", C_REG_CN: "B2B", C_DN: "B2B", C_B2C: "B2C", C_EXP_WP: "EXPORT", C_EXP_WOP: "EXPORT",
                     C_SEZ_WP: "SEZ", C_SEZ_WOP: "SEZ", C_DEEMED: "DEEMED"}


def gstr1_table(row):
    category = row["category"]
    if category in (C_NEXT_PLUS, C_NEXT_MINUS):
        category = row.get("base_category", category)
    if category == C_B2B:
        return "4A"
    if category == C_B2C:
        return "5A" if row["igst"] and abs(row["inv_value"]) > 100000 and row["inv_value"] > 0 else "7"
    if category in (C_EXP_WP, C_EXP_WOP):
        return "6A"
    if category in (C_SEZ_WP, C_SEZ_WOP):
        return "6B"
    if category == C_DEEMED:
        return "6C"
    if category in (C_REG_CN, C_DN, C_CN_EXP, C_DN_EXP):
        return "9B"
    if category in (C_EXEMPT, C_NIL, C_NONGST):
        return "8"
    if category in (C_AMD_MINUS, C_AMD_PLUS, C_AMD_MINUS_NT, C_AMD_PLUS_NT):
        return "9A"
    return ""


def finish_sr_row(row, fy_end, saved_category=None, saved_month=None):
    # Applies saved choices and works out the columns that depend on category / Month Paid.
    if saved_month:
        try:
            row["month_paid"] = datetime.strptime(saved_month, "%Y-%m").date()
        except ValueError:
            pass
    category = saved_category or row["auto_category"]
    row["base_category"] = category
    if row["month_paid"] > fy_end and category not in (C_NEXT_PLUS, C_NEXT_MINUS):
        category = C_NEXT_MINUS if row["taxable"] < 0 or row["inv_value"] < 0 else C_NEXT_PLUS
    row["category"] = category
    row["nature"] = dict((c[0], c[1]) for c in SR_CATEGORIES).get(category, "")
    row["gstr1"] = gstr1_table(row)
    row["gstr9"] = SR_GSTR9.get(category, "")
    row["rule42"] = RULE42_EXEMPT if row["base_category"] in (C_EXEMPT, C_NIL) else "" if row["base_category"] == C_NONGST \
        else RULE42_TAXABLE
    row["error"] = "Enter Original Invoice" if row["taxable"] < 0 and not row["orig_no"] else ""
    return row


def build_sr_rows(vouchers, masters, kind_of, income_ledgers, bases, currencies, from_date, to_date, fy_end, saved,
                  party_classes):
    # One row per voucher. Returns (rows, warnings).
    rows, warnings, invoice_dates = [], [], {}
    for voucher in vouchers.iter("VOUCHER"):
        if child_text(voucher, "ISCANCELLED").lower() == "yes" or child_text(voucher, "ISOPTIONAL").lower() == "yes":
            continue
        day = parse_tally_date(child_text(voucher, "DATE"))
        if not day or not (from_date <= day <= to_date):
            continue
        lines = voucher_lines(voucher)[0]
        kinds = [(l, a, kind_of(l)) for l, a in lines]
        income = [(l, a) for l, a, k in kinds if l in income_ledgers]
        fa_sale = (any(a > 0 and k == "asset" for l, a, k in kinds) and
                   any(a < 0 and k in ("bank", "debtor") for l, a, k in kinds))
        if not income and not fa_sale:
            continue
        taxable = round(sum(a for l, a, k in kinds if k == "pl" or (fa_sale and k == "asset")), 2)
        taxes = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
        tax_ledgers = []
        for l, a, k in kinds:
            if k == "tax":
                kind = tax_kind(l, masters)
                if kind in taxes:
                    taxes[kind] += a
                    tax_ledgers.append(l)
        round_off = sum(a for l, a, k in kinds if k == "round")
        if abs(taxable) < 0.005 and not any(abs(v) >= 0.005 for v in taxes.values()):
            continue                                                  # e.g. transfer between two income ledgers
        vtype = child_text(voucher, "VOUCHERTYPENAME")
        base = bases.get(vtype, vtype.lower())
        number = child_text(voucher, "VOUCHERNUMBER")
        value = round(taxable + sum(taxes.values()) + round_off, 2)
        doc = "CN" if "credit note" in base else "DN" if "debit note" in base else "INV"
        if doc == "INV" and value < 0:
            doc = "CN"                                                # a journal reducing sales behaves like a credit note
        party = child_text(voucher, "PARTYLEDGERNAME")
        if not party or kind_of(party) in ("pl", "tax", "asset"):
            sides = [(l, abs(a)) for l, a, k in kinds if k in ("debtor", "bank", "creditor", "other")]
            party = max(sides, key=lambda s: s[1])[0] if sides else ""
        info = masters.get(party, {})
        vinfo = {"gstin": child_text(voucher, "PARTYGSTIN").replace(" ", "").upper(),
                 "place": child_text(voucher, "PLACEOFSUPPLY") or child_text(voucher, "STATENAME"),
                 "country": child_text(voucher, "COUNTRYOFRESIDENCE"), "regtype": child_text(voucher, "GSTREGISTRATIONTYPE")}
        gstin = (vinfo["gstin"] or info.get("gstin", "")).replace(" ", "").upper()
        # Foreign currency: any amount written as "$1,000 @ 83/$ = 83,000", the party line first.
        forex = None
        for tag in ("ALLLEDGERENTRIES.LIST", "LEDGERENTRIES.LIST", "ACCOUNTINGALLOCATIONS.LIST"):
            for entry in voucher.iter(tag):
                found = parse_forex(child_text(entry, "AMOUNT"))
                if found and (forex is None or child_text(entry, "LEDGERNAME") == party):
                    forex = found
        used_income = [l for l, a in income] or [l for l, a, k in kinds if k == "asset"]
        party_class, reason = party_class_of(party, info, vinfo, used_income, bool(forex))
        class_saved = party_classes.get(party)
        if class_saved:
            party_class, reason = class_saved, "chosen by you"
        has_tax = any(abs(taxes[k]) >= 0.005 for k in ("igst", "cgst", "sgst"))
        nontax = "Non-GST"
        for ledger, amount in income:
            text = (masters.get(ledger, {}).get("taxability", "") + " " + ledger).lower()
            if "exempt" in text:
                nontax = "Exempted"
            elif "nil" in text and nontax != "Exempted":
                nontax = "Nil Rated"
        flags, remarks = [], []
        auto = category_for(party_class, doc, has_tax, nontax)
        if not has_tax and auto == C_NONGST:
            flags.append("nongst")
            remarks.append("No GST charged - treated as Non-GST supply; check")
        rates = tax_rates_of(tax_ledgers, masters)
        rate = 0.0
        if has_tax:
            if len(rates) > 1:
                rate = "Mixed"
                remarks.append("Rates " + " / ".join("%g%%" % r for r in sorted(rates)))
            elif len(rates) == 1:
                rate = list(rates)[0] / 100
            elif taxable:
                effective = (taxes["igst"] + taxes["cgst"] + taxes["sgst"]) / taxable * 100
                standard = nearest_rate(effective)
                rate = standard / 100 if standard else "Mixed"
                if not standard:
                    remarks.append("Effective rate %.2f%% - more than one rate?" % effective)
        state = ""
        if party_class == "EXPORT":
            state = "Other Territory"
        else:
            state = vinfo["place"] or info.get("state", "") or STATE_CODES.get(gstin[:2], "")
        fx_amount = fx_rate = None
        fx_currency = ""
        if forex:
            symbol, amount, rate_fx = forex
            fx_amount, fx_rate = amount, rate_fx
            fx_currency = currency_label(symbol, currencies.get(symbol, ""))
        elif party_class == "EXPORT":
            flags.append("export_inr")
            remarks.append("Export booked without foreign currency")
        orig_no = orig_date = ""
        if doc in ("CN", "DN"):
            for entry in voucher.iter("ALLLEDGERENTRIES.LIST"):
                if child_text(entry, "LEDGERNAME") == party:
                    for bill in entry.iter("BILLALLOCATIONS.LIST"):
                        if child_text(bill, "BILLTYPE").lower().startswith("agst"):
                            orig_no = child_text(bill, "NAME")
            if not orig_no:
                flags.append("orig_missing")
        ledger = max(income, key=lambda i: abs(i[1]))[0] if income else used_income[0] if used_income else ""
        if fa_sale and not income:
            remarks.append("Sale of fixed asset")
        if reason in ("no GSTIN",) and value > 0 and has_tax and gstin == "":
            pass
        key = day.isoformat() + "|" + vtype + "|" + number
        row = {"key": key, "month_paid": month_start(day), "status": "", "rejected": "", "invoice": number,
               "party": party, "gstin": gstin, "inv_date": day, "inv_value": value, "rate": rate,
               "taxable": taxable, "igst": round(taxes["igst"], 2), "cgst": round(taxes["cgst"], 2),
               "sgst": round(taxes["sgst"], 2), "cess": round(taxes["cess"], 2), "state": state,
               "fx_amount": fx_amount, "fx_rate": fx_rate, "fx_currency": fx_currency, "orig_no": orig_no,
               "orig_date": orig_date, "remark": "; ".join(remarks), "vtype": vtype, "ledger": ledger,
               "doc": doc, "has_tax": has_tax, "flags": flags, "auto_category": auto, "class": party_class,
               "class_reason": reason, "tab": "gst" if has_tax else "nogst"}
        if doc == "INV":
            invoice_dates.setdefault(number, day)
        rows.append(row)
    for row in rows:
        if row["orig_no"] and row["orig_no"] in invoice_dates:
            row["orig_date"] = invoice_dates[row["orig_no"]]
        if saved["category"].get(row["key"]):
            row["flags"] = [f for f in row["flags"] if f != "nongst"]      # category already confirmed by the user
        finish_sr_row(row, fy_end, saved["category"].get(row["key"]), saved["month_paid"].get(row["key"]))
    rows.sort(key=lambda r: (r["month_paid"], r["inv_date"], r["invoice"]))
    return rows, warnings


def sr_month_list(fy_start):
    return [date(fy_start.year + (1 if fy_start.month + i > 12 else 0), (fy_start.month + i - 1) % 12 + 1, 1)
            for i in range(12)]


def comparable(row):
    # Rows that belong in outward taxable supplies of GSTR-1 (all tables except 8 nil/exempt/non-GST).
    return row["gstr1"] not in ("8", "")


def sr_pivots(rows, fy_start, fy_end):
    # Books by invoice month and by Month Paid (3B), table-wise.
    months = sr_month_list(fy_start)
    keys = ("taxable", "igst", "cgst", "sgst", "cess")
    by_invoice = {m: [0.0] * 5 for m in months}
    by_paid = {m: {} for m in months}
    nontax = {m: 0.0 for m in months}
    for row in rows:
        m = month_start(row["inv_date"])
        if comparable(row) and m in by_invoice:
            by_invoice[m] = [a + row[k] for a, k in zip(by_invoice[m], keys)]
        elif m in nontax:
            nontax[m] += row["taxable"]
        p = row["month_paid"]
        if p in by_paid:
            table = row["gstr1"] or "?"
            by_paid[p][table] = [a + row[k] for a, k in zip(by_paid[p].get(table, [0.0] * 5), keys)]
    return months, by_invoice, by_paid, nontax


def sr_bucket_totals(rows, buckets, fy_end):
    # Year-end bridge items: CY items declared next FY (from Month Paid), and the grid items.
    keys = ("taxable", "igst", "cgst", "sgst")
    next_fy = [0.0] * 4
    for row in rows:
        if comparable(row) and row["month_paid"] > fy_end:
            next_fy = [a + row[k] for a, k in zip(next_fy, keys)]
    grid = {}
    for item in buckets:
        bucket = item.get("bucket", "")
        sign = -1 if bucket.startswith(("PY credit", "Amendment (-)")) else 1
        number = lambda v: float(str(v or 0).replace(",", "") or 0)
        values = ([number(item.get(k)) for k in keys] if bucket == "Other reconciling item"     # signed as entered
                  else [sign * abs(number(item.get(k))) for k in keys])
        grid[item.get("bucket", "")] = [a + b for a, b in zip(grid.get(item.get("bucket", ""), [0.0] * 4), values)]
    return next_fy, grid


BUCKETS = ["PY invoice / debit note declared in CY return", "PY credit note declared in CY return",
           "Amendment (+) declared in CY return", "Amendment (-) declared in CY return", "Other reconciling item"]


# ---- GSTR-1 / GSTR-1A / GSTR-3B PDFs (read into memory only - nothing is saved)
MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
               "november", "december"]
WATERMARK = re.compile(r"^[ADEFILN]\s+(?=\S)")
# GSTR-1 table code -> how it is used. "taxable" codes make up the outward taxable supplies compared with books.
R1_TAXABLE_CODES = ["4A", "4B", "5", "6A", "6B", "6C", "7", "9A", "9B-R", "9B-U", "9C", "10"]
R1_LABELS = {"4A": "4A B2B", "4B": "4B B2B (reverse charge)", "5": "5 B2CL", "6A": "6A Exports", "6B": "6B SEZ",
             "6C": "6C Deemed exports", "7": "7 B2CS", "8": "8 Nil / exempt / non-GST", "9A": "9A Amendments (net)",
             "9B-R": "9B Credit/debit notes - registered", "9B-U": "9B Credit/debit notes - unregistered",
             "9C": "9C Amended credit/debit notes (net)", "10": "10 B2CS amendments (net)", "11A": "11A Advances received",
             "11B": "11B Advances adjusted", "TL": "Total liability (as printed)"}


def pdf_number(text):
    text = WATERMARK.sub("", (text or "").strip())
    if text in ("", "-"):
        return 0.0
    try:
        return to_number(text)
    except ValueError:
        return 0.0


def clean_cell(text):
    text = " ".join((text or "").split())
    text = WATERMARK.sub("", text)
    return "" if re.fullmatch(r"[ADEFILN]", text) else text


def pdf_period(texts, path):
    # Returns the first day of the return month, from the PDF text, else from the file name (..._MMYYYY.pdf).
    joined = " ".join(texts)
    year = re.search(r"(?:Financial year|Year)\s+(\d{4})-(\d{2})", joined)
    month = re.search(r"(?:Tax period|Period)\s+([A-Za-z]+)", joined)
    if year and month and month.group(1).lower() in MONTH_NAMES:
        number = MONTH_NAMES.index(month.group(1).lower()) + 1
        first_year = int(year.group(1))
        return date(first_year if number >= 4 else first_year + 1, number, 1)
    found = re.search(r"_(\d{2})(\d{4})\.pdf$", os.path.basename(path), re.I)
    if found:
        return date(int(found.group(2)), int(found.group(1)), 1)
    return None


def parse_gst_pdf(path):
    # {"form", "gstin", "month", "arn", "values": {code: [taxable, igst, cgst, sgst, cess]}, "warnings"}
    import pdfplumber
    rows, texts = [], []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
            for table in page.extract_tables():
                rows.extend([clean_cell(c) for c in row] for row in table)
    head = " ".join(texts[:1])
    form = ("GSTR-3B" if "GSTR-3B" in head or "GSTR3B" in os.path.basename(path).upper() else
            "GSTR-1A" if re.search(r"GSTR-?1A", head + os.path.basename(path), re.I) else "GSTR-1")
    result = {"form": form, "path": path, "gstin": "", "arn": "", "month": pdf_period(texts, path), "values": {},
              "warnings": []}
    for row in rows:
        label = row[0] if row else ""
        cells = [c for c in row if c]
        if len(cells) >= 2 and re.search(r"GSTIN", " ".join(cells[:-1])) and re.fullmatch(r"\d{2}[A-Z0-9]{13}", cells[-1]):
            result["gstin"] = result["gstin"] or cells[-1]
        if len(cells) >= 2 and re.search(r"\bARN$", " ".join(cells[:-1])) and "date" not in " ".join(cells[:-1]).lower():
            result["arn"] = result["arn"] or cells[-1]
    if form == "GSTR-3B":
        keys = {"(a)": "3.1a", "(b)": "3.1b", "(c": "3.1c", "(d)": "3.1d", "(e)": "3.1e"}
        for row in rows:
            label = row[0] if row else ""
            for prefix, key in keys.items():
                if label.startswith(prefix) and "supplies" in label.lower() and key not in result["values"] and len(row) >= 6:
                    result["values"][key] = [pdf_number(c) for c in row[1:6]]
        if "3.1a" not in result["values"]:
            result["warnings"].append("Table 3.1 could not be read from " + os.path.basename(path))
        return result

    # GSTR-1 / 1A: walk the rows in order; a section heading sets the table, its total rows give the figures.
    section, values = "", {}

    def put(code, row, add=False):
        figures = [pdf_number(c) for c in row[3:8]] if len(row) >= 8 else None
        if figures is None:
            return
        if add and code in values:
            values[code] = [a + b for a, b in zip(values[code], figures)]
        elif code not in values:
            values[code] = figures
    for row in rows:
        label = row[0] if row else ""
        low = label.lower()
        heading = re.match(r"^(4A|4B|5|6A|6B|6C|7|8|9A|9B|9C|10|11A\(1\)|11B\(1\)|11A|11B|12|13|14A|14|15A|15)\s*[-–]", label)
        if heading:
            code = heading.group(1)
            section = {"11A(1)": "11A", "11B(1)": "11B"}.get(code, code)
            if code in ("11A", "11B") and not label.startswith(code + "(1)") and "amendment" in low:
                section = code + "-amd"
            if code == "9B":
                section = "9B-U" if "unregistered" in low else "9B-R"
            if code == "9C":
                section = "9C"
            continue
        if low.startswith("total liability"):
            put("TL", row)
            continue
        if section in ("4A", "4B", "5", "6A", "6B", "6C", "7", "8", "11A", "11B") and low.startswith("total"):
            put(section, row)
        elif section in ("9A", "10") and low.startswith("net differential amount"):
            put(section, row, add=True)                       # several 9A sub-tables: add them up
        elif section in ("9B-R", "9B-U") and low.startswith("total - net off"):
            put(section, row)
        elif section == "9C" and low.startswith("net differential amount"):
            put("9C", row, add=True)
    result["values"] = values
    if "4A" not in values and "TL" not in values:
        result["warnings"].append("No GSTR-1 tables could be read from " + os.path.basename(path))
    if form == "GSTR-1A":
        result["warnings"].append("GSTR-1A read with the GSTR-1 layout - no GSTR-1A sample has been checked yet.")
    return result


def r1_outward(values):
    # Outward taxable supplies as per GSTR-1 / 1A (all tables that carry taxable outward supplies, net of notes).
    total = [0.0] * 5
    for code in R1_TAXABLE_CODES:
        total = [a + b for a, b in zip(total, values.get(code, [0.0] * 5))]
    return total


def sr_returns_by_month():
    # {month: {"GSTR-1": values, "GSTR-1A": values, "GSTR-3B": values}} from the loaded PDFs.
    out = {}
    for item in state.get("sr_pdfs", {}).values():
        if item.get("month"):
            out.setdefault(item["month"], {})[item["form"]] = item["values"]
    return out


def add5(a, b):
    return [x + y for x, y in zip(a, b)]


def sr_recon():
    # Everything the Reconciliation view and export need. Amounts are [taxable, igst, cgst, sgst].
    info, rows = state.get("sr_info") or {}, state.get("sr_rows", [])
    fy_start = info.get("fy_start") or state.get("sr_fy_start")
    fy_end = info.get("fy_end") or state.get("sr_fy_end")
    if not fy_start:
        return None
    months, by_invoice, by_paid, nontax = sr_pivots(rows, fy_start, fy_end)
    returns = sr_returns_by_month()
    zero = [0.0] * 5
    monthly, totals = [], {"books": zero, "r1": zero, "r3b": zero}
    loaded_r1 = loaded_3b = 0
    nontaxable = []
    for m in months:
        r = returns.get(m, {})
        r1 = add5(r1_outward(r.get("GSTR-1", {})), r1_outward(r.get("GSTR-1A", {}))) if ("GSTR-1" in r or "GSTR-1A" in r) else None
        r3b = add5(r.get("GSTR-3B", {}).get("3.1a", zero), r.get("GSTR-3B", {}).get("3.1b", zero)) if "GSTR-3B" in r else None
        loaded_r1 += r1 is not None
        loaded_3b += r3b is not None
        books = by_invoice[m]
        monthly.append({"month": m, "books": books, "r1": r1, "r3b": r3b,
                        "d_r1": None if r1 is None else [a - b for a, b in zip(books, r1)],
                        "d_3b": None if r3b is None else [a - b for a, b in zip(books, r3b)],
                        "r1_3b": None if r1 is None or r3b is None else [a - b for a, b in zip(r1, r3b)]})
        totals["books"] = add5(totals["books"], books)
        totals["r1"] = add5(totals["r1"], r1 or zero)
        totals["r3b"] = add5(totals["r3b"], r3b or zero)
        g3 = r.get("GSTR-3B", {})
        nontaxable.append({"month": m, "books": nontax[m],
                           "r1": (r.get("GSTR-1", {}).get("8", zero)[0] + r.get("GSTR-1A", {}).get("8", zero)[0])
                           if ("GSTR-1" in r or "GSTR-1A" in r) else None,
                           "r3b": (g3.get("3.1c", zero)[0] + g3.get("3.1e", zero)[0]) if "GSTR-3B" in r else None})
    year = state.get("sr_year", {})
    next_fy, grid = sr_bucket_totals(rows, year.get("buckets", []), fy_end)
    bridge = [("Outward taxable supplies as per books (invoice date in the year)", totals["books"][:4]),
              ("Less: current-year invoices / notes declared in next FY returns (Month Paid after the year)",
               [-x for x in next_fy])]
    for bucket in BUCKETS:
        if bucket in grid:
            bridge.append(("Add / (less): " + bucket, grid[bucket]))
    expected = [0.0] * 4
    for label, values in bridge:
        expected = [a + b for a, b in zip(expected, values)]
    advances = [{"month": m, "11A": returns.get(m, {}).get("GSTR-1", {}).get("11A", zero),
                 "11B": returns.get(m, {}).get("GSTR-1", {}).get("11B", zero)} for m in months]
    return {"months": months, "monthly": monthly, "totals": totals, "by_paid": by_paid, "nontaxable": nontaxable,
            "bridge": bridge, "expected": expected, "loaded_r1": loaded_r1, "loaded_3b": loaded_3b,
            "gap_r1": [a - b for a, b in zip(expected, totals["r1"][:4])],
            "gap_3b": [a - b for a, b in zip(expected, totals["r3b"][:4])], "returns": returns, "advances": advances,
            "next_fy": next_fy}


def sr_register_values(row, line):
    # The 26 cells (A..Z) of one Sales Register row, in the GST register's order. Formulas as in the register.
    rate = row["rate"]
    remark = row["remark"]
    if row.get("ledger"):
        remark = ("Ledger: " + row["ledger"] + ("; " + remark if remark else ""))
    as_dt = lambda d: datetime(d.year, d.month, d.day) if isinstance(d, date) else d
    return [as_dt(row["month_paid"]), row["category"], "=VLOOKUP(B%d,$B$1:$C$22,2,0)" % line, row["status"] or None,
            row["rejected"] or None, row["invoice"], row["party"], row["gstin"] or None, as_dt(row["inv_date"]),
            row["inv_value"], rate if rate != 0.0 else 0, row["taxable"], row["igst"], row["cgst"], row["sgst"],
            row["state"] or None, '=IF(L%d<0,"Enter Original Invoice","")' % line,
            (int(row["gstr1"]) if row["gstr1"] in ("7", "8") else row["gstr1"]) or None,
            row["gstr9"] or None, row["fx_amount"], row["fx_rate"], row["fx_currency"] or None, row["orig_no"] or None,
            as_dt(row["orig_date"]) if row["orig_date"] else None, row["rule42"] or None, remark or None]


def sr_template_rows():
    rows = sorted(state.get("sr_rows", []), key=lambda r: (r["month_paid"], r["inv_date"], r["invoice"]))
    return rows


def export_sr_template(template, out_path):
    # Fills the "Sales Register" sheet of the user's GST register (from row 25) and saves a copy.
    # Uses Excel itself when available (keeps macros and every drop-down); otherwise openpyxl.
    rows = sr_template_rows()
    notes = []
    try:
        import win32com.client as win32
    except ImportError:
        win32 = None
    if win32 is not None and os.name == "nt":
        excel = win32.DispatchEx("Excel.Application")
        excel.Visible, excel.DisplayAlerts = False, False
        book = None
        try:
            book = excel.Workbooks.Open(os.path.abspath(template))
            sheet = book.Worksheets("Sales Register")
            first_month = sheet.Range("I1").Value
            last = max(sheet.Cells(sheet.Rows.Count, 1).End(-4162).Row, sheet.Cells(sheet.Rows.Count, 6).End(-4162).Row,
                       sheet.Cells(sheet.Rows.Count, 12).End(-4162).Row, 25)
            sheet.Range("A25:Z%d" % last).ClearContents()
            sheet.Range("T25:U%d" % last).Interior.ColorIndex = -4142
            if rows:
                end = 24 + len(rows)
                data = [sr_register_values(r, 25 + i) for i, r in enumerate(rows)]
                sheet.Range("A25:Z%d" % end).Value = [tuple(v) for v in data]
                sheet.Range("C25:C%d" % end).Formula = "=VLOOKUP(B25,$B$1:$C$22,2,0)"
                sheet.Range("Q25:Q%d" % end).Formula = '=IF(L25<0,"Enter Original Invoice","")'
                for i, r in enumerate(rows):
                    if "export_inr" in r["flags"]:
                        sheet.Range("T%d:U%d" % (25 + i, 25 + i)).Interior.Color = 206 * 65536 + 199 * 256 + 255
            book.SaveAs(os.path.abspath(out_path), FileFormat=52 if out_path.lower().endswith(".xlsm") else 51)
            notes.append("Filled with Excel - macros, drop-downs and formats kept.")
            if first_month is not None and hasattr(first_month, "year") and state.get("sr_fy_start") and \
                    (first_month.year, first_month.month) != (state["sr_fy_start"].year, state["sr_fy_start"].month):
                notes.append("Your template's month list starts " + str(first_month)[:7] + ", not the extracted year - use "
                             "the template for the right year so the Set Off sheet picks up the months.")
        finally:
            if book is not None:
                book.Close(False)
            excel.Quit()
        return notes
    # Fallback without Excel.
    book = openpyxl.load_workbook(template, keep_vba=template.lower().endswith(".xlsm"))
    sheet = book["Sales Register"]
    first_month = sheet["I1"].value
    if hasattr(first_month, "year") and state.get("sr_fy_start") and \
            (first_month.year, first_month.month) != (state["sr_fy_start"].year, state["sr_fy_start"].month):
        notes.append("Your template's month list starts " + first_month.strftime("%b-%Y") + ", not the extracted year - "
                     "use the template for the right year so the Set Off sheet picks up the months.")
    for line in range(25, max(sheet.max_row, 25) + 1):
        for column in range(1, 27):
            sheet.cell(row=line, column=column).value = None
    red = PatternFill("solid", fgColor="FFC7CE")
    for i, r in enumerate(rows):
        line = 25 + i
        for column, value in enumerate(sr_register_values(r, line), start=1):
            sheet.cell(row=line, column=column).value = value
        if "export_inr" in r["flags"]:
            sheet.cell(row=line, column=20).fill = red
            sheet.cell(row=line, column=21).fill = red
    book.save(out_path)
    notes.append("Excel was not available on this PC, so the file was filled without it. Macros are kept, but "
                 "drop-downs that point to other sheets may be missing - install pywin32 and use a PC with Excel "
                 "for a perfect copy.")
    return notes


def export_sr_excel(path, company, period):
    # The app's own working: voucher-level sheets, pivots, returns, reconciliation, year-bucket items, advances.
    recon = sr_recon()
    book = openpyxl.Workbook()
    money = "[>=10000000]##\\,##\\,##\\,##0.00;[>=100000]##\\,##\\,##0.00;##,##0.00"
    bold, header_fill = Font(bold=True), PatternFill("solid", fgColor="0B3D91")
    red, amber, grey = (PatternFill("solid", fgColor=c) for c in ("FFC7CE", "FEF3C7", "E5E7EB"))

    def heading(sheet, line, titles):
        for column, title in enumerate(titles, start=1):
            cell = sheet.cell(row=line, column=column, value=title)
            cell.font, cell.fill = Font(bold=True, color="FFFFFF"), header_fill
            cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")

    def put(sheet, line, values, money_from=0):
        for column, value in enumerate(values, start=1):
            cell = sheet.cell(row=line, column=column, value=value)
            if isinstance(value, float) and column > money_from:
                cell.number_format = money
            elif isinstance(value, date):
                cell.number_format = "dd-mm-yyyy"
    first = True
    for title, tab in (("Books - GST charged", "gst"), ("Books - No GST", "nogst")):
        sheet = book.active if first else book.create_sheet(title)
        sheet.title, first = title, False
        sheet["A1"] = title + " - " + company + " - " + period
        sheet["A1"].font = Font(bold=True, size=13)
        keys = [k for k, t, w in SR_COLUMNS] + [k for k, t, w in SR_EXTRA]
        heading(sheet, 3, [t for k, t, w in SR_COLUMNS] + [t for k, t, w in SR_EXTRA])
        line = 4
        for r in [x for x in state.get("sr_rows", []) if x["tab"] == tab]:
            values = []
            for k in keys:
                value = r.get(k)
                if k == "month_paid":
                    value = r["month_paid"]
                values.append(value if value not in (None, "") else None)
            put(sheet, line, values)
            sheet.cell(row=line, column=1).number_format = "mmm-yy"
            sheet.cell(row=line, column=11).number_format = "0%"
            if "export_inr" in r["flags"]:
                for column in (20, 21):
                    sheet.cell(row=line, column=column).fill = red
            elif r["flags"]:
                sheet.cell(row=line, column=2).fill = amber
            if r["category"] in (C_NEXT_PLUS, C_NEXT_MINUS):
                sheet.cell(row=line, column=2).fill = grey
            line += 1
        for column, (k, t, w) in enumerate(SR_COLUMNS + SR_EXTRA, start=1):
            sheet.column_dimensions[get_column_letter(column)].width = max(w / 7, 9)
        sheet.freeze_panes = "B4"
    if recon:
        sheet = book.create_sheet("Books - Monthly")
        sheet["A1"] = "Books by Month Paid (3B) and GSTR-1 table - " + company
        sheet["A1"].font = Font(bold=True, size=13)
        tables = ["4A", "5A", "6A", "6B", "6C", "7", "9B", "9A", "8"]
        heading(sheet, 3, ["Month Paid (3B)"] + ["Table " + t + " taxable" for t in tables] +
                ["Total taxable (excl. 8)", "IGST", "CGST", "SGST"])
        for line, m in enumerate(recon["months"], start=4):
            data = recon["by_paid"][m]
            comparable_total = [0.0] * 5
            for t, values in data.items():
                if t != "8":
                    comparable_total = add5(comparable_total, values)
            put(sheet, line, [m] + [data.get(t, [0.0])[0] for t in tables] + comparable_total[:4])
            sheet.cell(row=line, column=1).number_format = "mmm-yy"

        sheet = book.create_sheet("GST Returns")
        sheet["A1"] = "GSTR-1 / 1A / 3B as read from the PDFs - " + company
        sheet["A1"].font = Font(bold=True, size=13)
        codes = ["4A", "4B", "5", "6A", "6B", "6C", "7", "9A", "9B-R", "9B-U", "9C", "10", "8"]
        heading(sheet, 3, ["Month"] + ["R1 " + R1_LABELS[c] for c in codes] +
                ["R1 outward taxable", "R1 IGST", "R1 CGST", "R1 SGST", "1A outward taxable", "3B 3.1(a) taxable",
                 "3B IGST", "3B CGST", "3B SGST", "3B 3.1(b)", "3B 3.1(c)", "3B 3.1(d) RCM", "3B 3.1(e)"])
        for line, m in enumerate(recon["months"], start=4):
            r = recon["returns"].get(m, {})
            g1, g1a, g3 = r.get("GSTR-1", {}), r.get("GSTR-1A", {}), r.get("GSTR-3B", {})
            out = r1_outward(g1)
            put(sheet, line, [m] + [g1.get(c, [0.0])[0] for c in codes] + out[:4] + [r1_outward(g1a)[0]] +
                g3.get("3.1a", [0.0] * 5)[:4] + [g3.get(k, [0.0])[0] for k in ("3.1b", "3.1c", "3.1d", "3.1e")])
            sheet.cell(row=line, column=1).number_format = "mmm-yy"

        sheet = book.create_sheet("Reconciliation")
        sheet["A1"] = "Sales - Books vs GSTR-1 (+1A) vs GSTR-3B - " + company + " - " + period
        sheet["A1"].font = Font(bold=True, size=13)
        heading(sheet, 3, ["Month", "Books taxable", "Books IGST", "Books CGST", "Books SGST", "GSTR-1+1A taxable",
                           "IGST", "CGST", "SGST", "GSTR-3B taxable", "IGST", "CGST", "SGST", "Books - R1 taxable",
                           "IGST", "CGST", "SGST", "Books - 3B taxable", "IGST", "CGST", "SGST", "R1 - 3B taxable"])
        line = 4
        for item in recon["monthly"]:
            blank = [None] * 4
            put(sheet, line, [item["month"]] + item["books"][:4] + (item["r1"] or blank)[:4] + (item["r3b"] or blank)[:4] +
                (item["d_r1"] or blank)[:4] + (item["d_3b"] or blank)[:4] + [(item["r1_3b"] or [None])[0]])
            sheet.cell(row=line, column=1).number_format = "mmm-yy"
            for column in (14, 15, 16, 17, 18, 19, 20, 21, 22):
                value = sheet.cell(row=line, column=column).value
                if isinstance(value, float) and abs(value) >= 1:
                    sheet.cell(row=line, column=column).fill = red
            line += 1
        t = recon["totals"]
        put(sheet, line, ["Total"] + t["books"][:4] + t["r1"][:4] + t["r3b"][:4] +
            [a - b for a, b in zip(t["books"][:4], t["r1"][:4])] + [a - b for a, b in zip(t["books"][:4], t["r3b"][:4])] +
            [t["r1"][0] - t["r3b"][0]])
        for column in range(1, 23):
            sheet.cell(row=line, column=column).font = bold
        line += 3
        sheet.cell(row=line, column=1, value="Year-end bridge (books to returns)").font = Font(bold=True, size=12)
        heading(sheet, line + 1, ["Particulars", "Taxable", "IGST", "CGST", "SGST"])
        line += 2
        for label, values in recon["bridge"]:
            put(sheet, line, [label] + [round(v, 2) for v in values])
            line += 1
        for label, values, strong in (("Expected as per returns", recon["expected"], True),
                                      ("GSTR-1 + 1A for the year (" + str(recon["loaded_r1"]) + " of 12 months loaded)",
                                       recon["totals"]["r1"][:4], False),
                                      ("Unexplained difference vs GSTR-1", recon["gap_r1"], True),
                                      ("GSTR-3B for the year (" + str(recon["loaded_3b"]) + " of 12 months loaded)",
                                       recon["totals"]["r3b"][:4], False),
                                      ("Unexplained difference vs GSTR-3B", recon["gap_3b"], True)):
            put(sheet, line, [label] + [round(v, 2) for v in values])
            if strong:
                for column in range(1, 6):
                    sheet.cell(row=line, column=column).font = bold
            line += 1
        line += 2
        sheet.cell(row=line, column=1, value="Nil rated, exempted and non-GST supplies").font = Font(bold=True, size=12)
        heading(sheet, line + 1, ["Month", "Books", "GSTR-1 table 8", "GSTR-3B 3.1(c)+(e)"])
        line += 2
        for item in recon["nontaxable"]:
            put(sheet, line, [item["month"], item["books"], item["r1"], item["r3b"]])
            sheet.cell(row=line, column=1).number_format = "mmm-yy"
            line += 1
        sheet.column_dimensions["A"].width = 70
        for column in range(2, 23):
            sheet.column_dimensions[get_column_letter(column)].width = 15
        sheet.freeze_panes = "B4"

        sheet = book.create_sheet("Year-bucket items")
        heading(sheet, 1, [t for k, t, w in BUCKET_COLUMNS])
        for line, item in enumerate(state.get("sr_year", {}).get("buckets", []), start=2):
            put(sheet, line, [item.get(k) for k, t, w in BUCKET_COLUMNS])
        sheet = book.create_sheet("Advances 11A-11B")
        sheet["A1"] = "Advances as per GSTR-1 (basic - voucher-level tracking to be added later)"
        heading(sheet, 3, ["Month", "11A taxable", "11A IGST", "11A CGST", "11A SGST", "11B taxable", "11B IGST",
                           "11B CGST", "11B SGST"])
        for line, item in enumerate(recon["advances"], start=4):
            put(sheet, line, [item["month"]] + item["11A"][:4] + item["11B"][:4])
            sheet.cell(row=line, column=1).number_format = "mmm-yy"
    book.save(path)


BUCKET_COLUMNS = [("bucket", "Bucket", 260), ("return_month", "Return month (mm-yyyy)", 110), ("invoice", "Invoice / note no.", 110),
                  ("inv_date", "Date (dd-mm-yyyy)", 100), ("party", "Party", 180), ("gstin", "GSTIN", 135),
                  ("taxable", "Taxable", 100), ("igst", "IGST", 85), ("cgst", "CGST", 85), ("sgst", "SGST", 85),
                  ("remark", "Remark", 220)]


# =============================================================================
# PART 5 - BACKGROUND JOBS (so the window never freezes)
# =============================================================================
def probe_port(port):
    # Asks one port whether a Tally is there. Returns (status, companies, plain-English detail).
    try:
        companies = get_companies(port)
        if companies:
            return "tally", companies, str(len(companies)) + " company(ies) open: " + ", ".join(companies)
        return "no_company", {}, "Tally is running but no company is open - open a company in this Tally."
    except urllib.error.URLError as error:
        reason = getattr(error, "reason", error)
        if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason).lower():
            return "busy", {}, ("Something is listening but did not answer in time. If this is Tally, close any "
                                "open screen or pop-up in Tally (e.g. the Settings screen) and wait.")
        if isinstance(reason, ConnectionRefusedError) or "refused" in str(reason).lower() or "10061" in str(reason):
            return "nothing", {}, "Nothing is listening on this port."
        return "error", {}, "Could not connect: " + str(reason)
    except (socket.timeout, TimeoutError):
        return "busy", {}, ("Something is listening but did not answer in time. If this is Tally, close any open "
                            "screen or pop-up in Tally (e.g. the Settings screen) and wait.")
    except ET.ParseError:
        return "not_tally", {}, "A program answered on this port, but it is not Tally."
    except Exception as error:
        return "error", {}, "Unexpected reply: " + str(error)


def check_connection_job(ports):
    results = [(port,) + probe_port(port) for port in ports]
    messages.put(("connection", results))


def extract_job(port, company, info, from_date, to_date):
    try:
        try:
            closing = ledger_balances(port, company, from_date, to_date, with_totals=True)
        except ValueError:
            closing = ledger_balances(port, company, from_date, to_date, with_totals=False)   # totals not supported
        day_before = from_date - timedelta(days=1)
        before = ledger_balances(port, company, day_before, day_before, with_totals=False)
        revenue = revenue_groups(port, company)
        if not closing:
            raise ValueError("Tally returned no ledgers. Check that the company is open in Tally.")
        year_start = year_start_for(from_date, info["fy_month"], info["fy_day"])
        new_year = from_date == year_start
        period_text = show_date(from_date) + " to " + show_date(to_date)
        tb = build_detailed_tb(closing, before, revenue, new_year, period_text)
        open_gap, close_gap = tb_differences(tb["rows"])
        if abs(open_gap) > 1 or abs(close_gap) > 1:
            # Usual cause: the company keeps inventory. Stock is not a ledger, so it is missing from the list.
            try:
                year_open = stock_value(port, company, year_start - timedelta(days=1))
                stock = None
                if year_open is not None:
                    stock = {"year_open": year_open,
                             "before": year_open if new_year else stock_value(port, company, day_before),
                             "close": stock_value(port, company, to_date)}
                    with_stock = build_detailed_tb(closing, before, revenue, new_year, period_text, stock)
                    new_open, new_close = tb_differences(with_stock["rows"])
                    if abs(new_open) <= 1 and abs(new_close) <= 1:
                        tb = with_stock
                    else:
                        tb["notes"].append("Inventory found (opening stock " + indian(year_open) + ", closing stock " +
                                           indian(stock["close"]) + ") but it does not explain the difference.")
                else:
                    tb["notes"].append("No stock items found in Tally, so the difference is not due to inventory.")
            except Exception as error:
                tb["notes"].append("Could not read inventory values to explain the difference (" + str(error) + ").")
            open_gap, close_gap = tb_differences(tb["rows"])
            if abs(open_gap) > 1:
                tb["notes"].append("Opening difference of " + indian(abs(open_gap)) + " remains - check Tally's own Trial "
                                   "Balance for the same date for a 'Difference in opening balances' line.")
        messages.put(("extracted", tb, company))
    except urllib.error.URLError:
        messages.put(("failed", "Could not reach Tally on port " + str(port) + ". Is Tally open?"))
    except Exception as error:
        messages.put(("failed", str(error)))


class FACancelled(Exception):
    pass


def fa_setup(port, company):
    # Returns (masters, fixed asset ledgers, context). Accumulated-depreciation ledgers kept under the
    # Fixed Assets group are NOT assets - they are listed separately.
    under = group_chain_sets(port, company)
    masters = ledger_masters(port, company)
    in_group = {name for name, d in masters.items() if under(d["group"], "fixed assets")}
    accdep_ledgers = {name for name in in_group if ACCDEP_WORDS.search(name)}
    asset_ledgers = in_group - accdep_ledgers
    if not asset_ledgers:
        raise ValueError("No ledgers were found under the Fixed Assets group in this company.")
    try:
        revenue = revenue_groups(port, company)
    except Exception:
        revenue = set()
    context = {"accdep": accdep_ledgers,
               "kind_of": make_kind_of(masters, asset_ledgers, accdep_ledgers, under, revenue)}
    return masters, asset_ledgers, context


def fa_balances(port, company, asset_ledgers, accdep_ledgers, from_date, to_date):
    # Opening (day before From) and closing (To) balances, as positive = debit (asset value).
    closing = ledger_balances(port, company, from_date, to_date, with_totals=False)
    day_before = from_date - timedelta(days=1)
    opening = ledger_balances(port, company, day_before, day_before, with_totals=False)
    pick = lambda data, names: {l: round(-data[l]["balance"], 2) for l in names if l in data}
    return {"asset_open": pick(opening, asset_ledgers), "asset_close": pick(closing, asset_ledgers),
            "accdep_open": pick(opening, accdep_ledgers), "accdep_close": pick(closing, accdep_ledgers)}


def fa_progress(text, percent):
    messages.put(("fa_progress", text, percent))


def read_vouchers(port, request, timeout):
    # Returns (reply, "") or (None, reason). Never raises, except when the user cancels.
    if fa_cancel.is_set():
        raise FACancelled()
    try:
        reply = tally_request(port, request, timeout=timeout)
    except ET.ParseError as error:
        return None, "Tally's reply could not be read (" + str(error) + ")"
    except (TimeoutError, socket.timeout):
        return None, "Tally did not answer within " + str(timeout) + " seconds"
    except urllib.error.URLError as error:
        return None, "could not reach Tally (" + str(error.reason) + ")"
    except (OSError, ValueError) as error:
        return None, str(error)
    problem = tally_error(reply)
    if problem:
        return None, "Tally said '" + problem + "'"
    return reply, ""


def add_unique(target, reply, seen):
    for voucher in reply.iter("VOUCHER"):
        key = voucher_key(voucher)
        if key not in seen:
            seen.add(key)
            target.append(voucher)


def method_filtered(port, company, from_date, to_date, low=10, high=60):
    # METHOD A - Tally picks out the fixed asset vouchers, one month at a time.
    # Returns (vouchers, error, raw_reply_on_error).
    found, seen = ET.Element("VOUCHERS"), set()
    chunks = month_chunks(from_date, to_date)
    for number, (start, end) in enumerate(chunks):
        fa_progress("Reading fixed asset vouchers for " + start.strftime("%b-%Y") + "  (" + str(number + 1) +
                    " of " + str(len(chunks)) + ")...", low + (high - low) * number / len(chunks))
        reply, error = read_vouchers(port, fa_filtered_request(company, start, end), timeout=120)
        if reply is None:
            return None, start.strftime("%b-%Y") + ": " + error, getattr(last_reply, "text", "")
        add_unique(found, reply, seen)
    return found, "", ""


def method_ledgerwise(port, company, ledgers, from_date, to_date, low=60, high=95):
    # METHOD B - each fixed asset ledger's own vouchers (as in the ledger's display in Tally).
    found, seen, failures, raw = ET.Element("VOUCHERS"), set(), [], ""
    ledgers = sorted(ledgers)
    for number, ledger in enumerate(ledgers):
        fa_progress("Reading ledger by ledger: " + ledger + "  (" + str(number + 1) + " of " + str(len(ledgers)) +
                    ")...", low + (high - low) * number / len(ledgers))
        reply, error = read_vouchers(port, fa_ledger_request(company, ledger, from_date, to_date), timeout=120)
        if reply is None:
            failures.append(ledger + ": " + error)
            raw = raw or getattr(last_reply, "text", "")
            continue
        add_unique(found, reply, seen)
    if failures and len(failures) == len(ledgers):
        return None, failures, raw
    return found, failures, raw


books_errors = []


def fa_books_figures(port, company, asset_ledgers, from_date, to_date):
    # Period debits to fixed asset ledgers per Tally: (direct debit totals or None, net movement or None).
    direct = movement = None
    books_errors.clear()
    try:
        balances = ledger_balances(port, company, from_date, to_date, with_totals=True)
        if all(balances[l]["has_totals"] or abs(balances[l]["balance"]) < 0.005 for l in asset_ledgers if l in balances):
            direct = round(sum(balances[l]["debits"] for l in asset_ledgers if l in balances), 2)
    except Exception as error:
        books_errors.append("debit totals: " + str(error))
    if direct is None:
        try:
            closing = ledger_balances(port, company, from_date, to_date, with_totals=False)
            day_before = from_date - timedelta(days=1)
            opening = ledger_balances(port, company, day_before, day_before, with_totals=False)
            movement = -sum(closing.get(l, {"balance": 0})["balance"] - opening.get(l, {"balance": 0})["balance"]
                            for l in asset_ledgers)          # Tally: debit balances are negative
        except Exception as error:
            books_errors.append("balances: " + str(error))
    return direct, movement


def save_troubleshooting(raw_replies):
    # Keeps Tally's raw reply when something went wrong. It contains client data.
    raw_replies = [(name, text) for name, text in raw_replies if text]
    if not raw_replies:
        return ""
    path = os.path.join(SAVE_FOLDER, "FA_troubleshooting_reply.xml")
    try:
        with open(path, "w", encoding="utf-8") as debug_file:
            for name, text in raw_replies:
                debug_file.write("<!-- " + name + " -->\n" + text[:5000000] + "\n")
        return path
    except OSError:
        return ""


def fa_extract_job(port, company, from_date, to_date):
    started = datetime.now()
    try:
        fa_progress("Reading ledgers and groups from Tally...", 3)
        masters, asset_ledgers, context = fa_setup(port, company)
        kind_of = context["kind_of"]
        is_asset = lambda ledger: ledger in asset_ledgers
        fa_progress("Reading the books figure for fixed asset ledgers...", 6)
        direct, movement = fa_books_figures(port, company, asset_ledgers, from_date, to_date)

        def evaluate(vouchers):
            rows, warnings, stats = fa_rows_from_vouchers(vouchers, masters, is_asset, from_date, to_date, kind_of)
            if direct is not None:
                expected = round(direct - stats["non_addition_debits"], 2)
            elif movement is not None:
                expected = round(movement + stats["asset_credits"] - stats["non_addition_debits"], 2)
            else:
                expected = None
            picked = sum(r["taxable"] for r in rows)
            gap = None if expected is None else abs(expected - picked)
            return {"rows": rows, "warnings": warnings, "stats": stats, "expected": expected, "gap": gap,
                    "vouchers": vouchers}

        def describe(name, result):
            s = result["stats"]
            return (name + ": " + str(s["in_period"]) + " voucher(s) in the period, " + str(s["with_assets"]) +
                    " with fixed asset debits")

        tried, raw_replies, chosen, chosen_name = [], [], None, ""
        # METHOD A - Tally's own filter, month by month.
        vouchers, error, raw = method_filtered(port, company, from_date, to_date)
        result_a = evaluate(vouchers) if vouchers is not None else None
        if result_a is None:
            tried.append("Tally filter: failed - " + error)
            raw_replies.append(("Tally filter", raw))
        else:
            tried.append(describe("Tally filter", result_a))
            chosen, chosen_name = result_a, "Tally filter (month by month)"

        # METHOD B - ledger by ledger, only if A failed or does not tie to the books.
        need_b = (result_a is None or (result_a["gap"] is not None and result_a["gap"] > 1)
                  or (result_a["gap"] is None and not result_a["rows"]))
        if need_b:
            vouchers, failures, raw = method_ledgerwise(port, company, asset_ledgers | context["accdep"],
                                                        from_date, to_date)
            if vouchers is None:
                tried.append("Ledger by ledger: failed - " + failures[0])
                raw_replies.append(("Ledger by ledger", raw))
            else:
                result_b = evaluate(vouchers)
                tried.append(describe("Ledger by ledger", result_b) +
                             (" (" + str(len(failures)) + " ledger(s) could not be read)" if failures else ""))
                if failures:
                    result_b["warnings"].append("These ledgers could not be read: " + "; ".join(failures[:5]))
                    raw_replies.append(("Ledger by ledger", raw))
                better = (chosen is None or
                          (result_b["gap"] is not None and (chosen["gap"] is None or result_b["gap"] < chosen["gap"])) or
                          (result_b["gap"] is None and len(result_b["rows"]) > len(chosen["rows"])))
                if better:
                    chosen, chosen_name = result_b, "ledger by ledger"

        if chosen is None:
            path = save_troubleshooting(raw_replies)
            raise ValueError("Tally did not send the vouchers.  " + "  |  ".join(tried) +
                             ("\nTally's reply was saved to " + path + " (client data - delete it afterwards)."
                              if path else "") +
                             "\nClose any open screen or pop-up in Tally and try again, or use 'Test voucher read'.")

        rows, warnings, stats = chosen["rows"], chosen["warnings"], chosen["stats"]
        apply_classes(rows, company)
        for row in rows:
            fa_compute(row, to_date)
        unclassified = sorted({r["ledger"] for r in rows if r["asset_class"] == "Not classified"})
        if unclassified:
            warnings.append(str(len(unclassified)) + " ledger(s) could not be classified - pick the Asset Class "
                            "(double-click): " + ", ".join(unclassified[:8]) + ("..." if len(unclassified) > 8 else ""))
        tb_debits = chosen["expected"]
        if stats["non_addition_debits"]:
            warnings.append("Debits of " + indian(stats["non_addition_debits"]) + " to fixed asset ledgers are profit on "
                            "sale moved out of the asset (or depreciation reversed) - not additions; the books figure "
                            "excludes them.")
        # Deletions and every other non-addition entry, opening / closing balances for the schedule.
        fa_progress("Working out deletions and the opening-to-closing schedule...", 97)
        entries = fa_entries_from_vouchers(chosen["vouchers"], kind_of, from_date, to_date)
        try:
            balances = fa_balances(port, company, asset_ledgers, context["accdep"], from_date, to_date)
        except Exception as error:
            balances = {}
            warnings.append("Opening / closing balances could not be read, so the schedule cannot be validated (" +
                            str(error) + ").")
        if context["accdep"]:
            warnings.append("Accumulated depreciation ledger(s) found under Fixed Assets: " +
                            ", ".join(sorted(context["accdep"])) + ". Asset ledgers are then at GROSS cost - the "
                            "depreciation worked out on opening balances in the schedule assumes WDV; check it.")
        extra = {"entries": entries, "balances": balances, "masters": masters,
                 "from": from_date, "accdep": sorted(context["accdep"])}
        if stats["outside"]:
            warnings.append("Tally sent " + str(stats["outside"]) + " voucher(s) dated outside the period - "
                            "they were ignored.")
        if direct is not None:
            warnings.insert(0, "Books figure = Tally's period debit totals.")
        elif movement is not None:
            warnings.insert(0, "Books figure = movement in fixed asset balances (" + indian(movement) +
                            ") + credits to fixed asset ledgers (" + indian(stats["asset_credits"]) + ").")
        else:
            warnings.append("The books figure could not be worked out from Tally (" + "; ".join(books_errors) + ").")
        seconds = int((datetime.now() - started).total_seconds())
        warnings.insert(0, "Read by " + chosen_name + " in " + str(seconds) + " seconds.  " + "  |  ".join(tried))
        if not rows and tb_debits:
            path = save_troubleshooting(raw_replies)
            if path:
                warnings.append("Tally's reply was saved to " + path + " (client data - delete it afterwards).")
        fa_progress("Done.", 100)
        messages.put(("fa_extracted", rows, tb_debits, warnings, company,
                      show_date(from_date) + " to " + show_date(to_date), to_date, len(asset_ledgers), extra))
    except FACancelled:
        messages.put(("fa_failed", "Cancelled. Nothing was changed - click Extract to start again.", AMBER))
    except urllib.error.URLError:
        messages.put(("fa_failed", "Could not reach Tally on port " + str(port) + ". Is Tally open?"))
    except Exception as error:
        messages.put(("fa_failed", str(error)))


def fa_test_job(port, company, from_date, to_date):
    # Quick check on the FIRST month of the period: does each method work, how fast, and are the dates right?
    try:
        fa_progress("Test: reading ledgers and groups...", 5)
        masters, asset_ledgers, context = fa_setup(port, company)
        start, end = month_chunks(from_date, to_date)[0]
        month = start.strftime("%b-%Y")
        lines, raw_replies, all_ok = ["Test voucher read for " + month + "  (" + str(len(asset_ledgers)) +
                                      " fixed asset ledgers found):"], [], True
        for name, runner in (("A. Tally filter", lambda: method_filtered(port, company, start, end, 10, 50)),
                             ("B. Ledger by ledger", lambda: method_ledgerwise(port, company, asset_ledgers,
                                                                               start, end, 50, 95))):
            begun = datetime.now()
            vouchers, error, raw = runner()
            seconds = round((datetime.now() - begun).total_seconds(), 1)
            if vouchers is None:
                all_ok = False
                lines.append(name + ": FAILED after " + str(seconds) + " s - " +
                             (error if isinstance(error, str) else error[0]))
                raw_replies.append((name, raw))
                continue
            rows, w, s = fa_rows_from_vouchers(vouchers, masters, lambda l: l in asset_ledgers, start, end)
            text = (name + ": OK in " + str(seconds) + " s - " + str(s["vouchers"]) + " voucher(s) received, " +
                    str(s["with_assets"]) + " with fixed asset debits, total " +
                    indian(sum(r["taxable"] for r in rows)) + ".")
            if s["outside"]:
                all_ok = False
                text += "  WARNING: " + str(s["outside"]) + " dated outside " + month + " (Tally ignored the dates)."
            if not isinstance(error, str) and error:
                text += "  " + str(len(error)) + " ledger(s) could not be read."
            lines.append(text)
        path = save_troubleshooting(raw_replies) if raw_replies else ""
        if path:
            lines.append("Tally's reply was saved to " + path + " (client data - delete it afterwards).")
        direct, movement = fa_books_figures(port, company, asset_ledgers, start, end)
        if direct is not None:
            lines.append("Books (Tally's debit totals) for " + month + ": " + indian(direct) + ".")
        elif movement is not None:
            lines.append("Books (net movement in fixed asset ledgers) for " + month + ": " + indian(movement) +
                         " - equals the total above unless an asset was sold or depreciated that month.")
        lines.append("Both methods should give the same total as the books (nil is fine if no asset was bought in " +
                     month + "). If they do, run the full Extract.")
        fa_progress("Test finished.", 100)
        messages.put(("fa_test", "\n".join(lines), all_ok))
    except FACancelled:
        messages.put(("fa_failed", "Test cancelled.", AMBER))
    except urllib.error.URLError:
        messages.put(("fa_failed", "Could not reach Tally on port " + str(port) + ". Is Tally open?"))
    except Exception as error:
        messages.put(("fa_failed", str(error)))


def sr_progress(text, percent):
    messages.put(("sr_progress", text, percent))


def sr_extract_job(port, company, from_date, to_date, fy_start, fy_end, fy_label):
    started = datetime.now()
    try:
        sr_progress("Reading groups and ledger masters...", 3)
        under = group_chain_sets(port, company)
        masters, extras = sr_ledger_masters(port, company)
        try:
            revenue = revenue_groups(port, company)
        except Exception:
            revenue = set()
        income_ledgers = {l for l, d in masters.items() if any(under(d["group"], g) for g in INCOME_GROUPS)}
        if not income_ledgers:
            raise ValueError("No ledgers were found under Sales Accounts, Direct Incomes or Indirect Incomes.")
        in_fa = {l for l, d in masters.items() if under(d["group"], "fixed assets")}
        accdep = {l for l in in_fa if ACCDEP_WORDS.search(l)}
        assets = in_fa - accdep
        kind_of = make_kind_of(masters, assets, accdep, under, revenue)
        bases = voucher_type_bases(port, company)
        currencies = currency_names(port, company)
        warnings = []

        # Vouchers: Tally's filter month by month; if that fails, ledger by ledger.
        found, seen, used_fields = ET.Element("VOUCHERS"), set(), []
        fields = FA_VOUCHER_FIELDS + VOUCHER_EXTRA
        chunks = month_chunks(from_date, to_date)
        failed = ""
        for number, (start, end) in enumerate(chunks):
            sr_progress("Reading sales vouchers for " + start.strftime("%b-%Y") + "  (" + str(number + 1) + " of " +
                        str(len(chunks)) + ")...", 5 + 55 * number / len(chunks))
            reply, error, fields = read_adaptive(port, lambda f, s=start, e=end: sr_filtered_request(company, s, e, f),
                                                 fields, VOUCHER_EXTRA)
            if reply is None:
                failed = start.strftime("%b-%Y") + ": " + error
                break
            add_unique(found, reply, seen)
        method = "Tally filter (month by month)"
        if failed:
            found, seen, method = ET.Element("VOUCHERS"), set(), "ledger by ledger"
            warnings.append("Tally filter failed (" + failed + ") - read ledger by ledger instead.")
            ledgers = sorted(income_ledgers)
            for number, ledger in enumerate(ledgers):
                sr_progress("Reading ledger by ledger: " + ledger + "  (" + str(number + 1) + " of " + str(len(ledgers)) +
                            ")...", 5 + 55 * number / len(ledgers))
                reply, error, fields = read_adaptive(port, lambda f, l=ledger: sr_ledger_request(company, l, from_date,
                                                                                                  to_date, f),
                                                     fields, VOUCHER_EXTRA)
                if reply is None:
                    warnings.append("Ledger '" + ledger + "' could not be read: " + error)
                    continue
                add_unique(found, reply, seen)
        # Sales of fixed assets - the Fixed Asset logic: vouchers touching a fixed asset ledger.
        if assets:
            for number, (start, end) in enumerate(chunks):
                sr_progress("Reading fixed asset vouchers (asset sales) for " + start.strftime("%b-%Y") + "...",
                            60 + 25 * number / len(chunks))
                reply, error = read_vouchers(port, fa_filtered_request(company, start, end), timeout=120)
                if reply is None:
                    warnings.append("Fixed asset vouchers for " + start.strftime("%b-%Y") + " could not be read (" + error +
                                    ") - asset sales of that month may be missing.")
                    continue
                add_unique(found, reply, seen)

        sr_progress("Classifying invoices...", 88)
        data = sr_load(company, fy_label)
        year = data["companies"][company][fy_label]
        party_classes = data["companies"][company]["party_class"]
        rows, more = build_sr_rows(found, masters, kind_of, income_ledgers, bases, currencies, from_date, to_date,
                                   fy_end, year, party_classes)
        warnings += more

        # Tie-out: income ledgers' movement in Tally vs the income lines read from the vouchers.
        picked = 0.0
        for voucher in found.iter("VOUCHER"):
            if child_text(voucher, "ISCANCELLED").lower() == "yes" or child_text(voucher, "ISOPTIONAL").lower() == "yes":
                continue
            day = parse_tally_date(child_text(voucher, "DATE"))
            if day and from_date <= day <= to_date:
                picked += sum(a for l, a in voucher_lines(voucher)[0] if l in income_ledgers)
        books = None
        try:
            sr_progress("Reading income ledger balances for the tie-out...", 94)
            closing = ledger_balances(port, company, from_date, to_date, with_totals=False)
            if from_date == fy_start:
                books = sum(closing[l]["balance"] for l in income_ledgers if l in closing)
            else:
                day_before = from_date - timedelta(days=1)
                opening = ledger_balances(port, company, day_before, day_before, with_totals=False)
                books = sum(closing[l]["balance"] - opening.get(l, {"balance": 0})["balance"]
                            for l in income_ledgers if l in closing)
        except Exception as error:
            warnings.append("Income ledger balances could not be read for the tie-out (" + str(error) + ").")
        missing = [f for f in VOUCHER_EXTRA if f not in fields] + [f for f in LEDGER_EXTRA if f not in extras]
        info = {"company": company, "from": from_date, "to": to_date, "fy_start": fy_start, "fy_end": fy_end,
                "fy_label": fy_label, "books_income": None if books is None else round(books, 2),
                "picked_income": round(picked, 2), "method": method, "seconds": int((datetime.now() - started).total_seconds()),
                "missing_fields": missing, "income_ledgers": len(income_ledgers)}
        sr_progress("Done.", 100)
        messages.put(("sr_extracted", rows, warnings, info))
    except FACancelled:
        messages.put(("sr_failed", "Cancelled. Nothing was changed.", AMBER))
    except urllib.error.URLError:
        messages.put(("sr_failed", "Could not reach Tally on port " + str(port) + ". Is Tally open?"))
    except Exception as error:
        messages.put(("sr_failed", str(error)))


def sr_pdf_job(paths):
    # Reads the GSTR PDFs (in memory only).
    results, problems = [], []
    try:
        import pdfplumber  # noqa: F401
    except ImportError:
        messages.put(("sr_pdfs", [], ["Reading PDFs needs pdfplumber. In Command Prompt run:  py -m pip install pdfplumber"]))
        return
    for number, path in enumerate(paths):
        sr_progress("Reading " + os.path.basename(path) + "  (" + str(number + 1) + " of " + str(len(paths)) + ")...",
                    100 * number / max(len(paths), 1))
        try:
            results.append(parse_gst_pdf(path))
        except Exception as error:
            problems.append(os.path.basename(path) + ": could not be read (" + str(error) + ")")
    messages.put(("sr_pdfs", results, problems))


# =============================================================================
# PART 6 - THE WINDOW
# =============================================================================
def current_ports():
    # "9000-9005" or "9000, 9001" -> [9000, 9001, ...]  (at most 20 ports). [] if the text is not valid.
    ports = []
    for part in port_box.get().replace(" ", "").split(","):
        if not part:
            continue
        bounds = part.split("-")
        if not all(b.isdigit() for b in bounds) or len(bounds) > 2:
            return []
        low, high = int(bounds[0]), int(bounds[-1])
        if not (0 < low <= high < 65536):
            return []
        ports.extend(range(low, high + 1))
    ports = sorted(set(ports))
    return ports if 0 < len(ports) <= 20 else []


def schedule_check():
    # Checks the ports every few seconds - only while "Connect" is on.
    if state["connect_on"] and not state["checking"] and not state["busy"]:
        ports = current_ports()
        if ports:
            state["checking"] = True
            threading.Thread(target=check_connection_job, args=(ports,), daemon=True).start()
        else:
            set_status(False, "Enter the Tally port(s) as e.g. 9000 or 9000-9005 (at most 20 ports).")
    window.after(CHECK_EVERY_MS, schedule_check)


def on_connect_toggle():
    state["connect_on"] = not state["connect_on"]
    if state["connect_on"]:
        connect_button.configure(text="Disconnect", bg="#6B7280", activebackground="#4B5563")
        set_status(False, "Connecting - looking for Tally on port(s) " + port_box.get().strip() + "...")
        status_dot.configure(fg=AMBER)
        state["checking"] = False
        schedule_now()
    else:
        connect_button.configure(text="Connect", bg=BLUE, activebackground=BLUE_DARK)
        state["companies"], state["defaults_set_for"] = {}, ""
        company_box.configure(values=[])
        company_box.set("")
        set_status(False, "Disconnected. Click Connect to look for Tally again.")


def schedule_now():
    ports = current_ports()
    if ports and not state["busy"]:
        state["checking"] = True
        threading.Thread(target=check_connection_job, args=(ports,), daemon=True).start()


def on_details():
    if not state["probe"]:
        return messagebox.showinfo("Connection details", "No check has run yet. Click Connect first.")
    lines = ["Port " + str(port) + ":  " + detail for port, status, companies, detail in state["probe"]]
    lines.append("")
    lines.append("If Tally is open but not listed:")
    lines.append("1. In Tally: F1 (Help) > Settings > Connectivity > Client/Server configuration.")
    lines.append("   TallyPrime acts as = Both, Port = 9000. Save with Ctrl+A.")
    lines.append("2. Close Tally completely and open it again - the setting starts only after a restart.")
    lines.append("3. Running more than one Tally? Each needs its OWN port (e.g. 9000 and 9001).")
    lines.append("   A second Tally on the same port gets no connection, without any warning.")
    lines.append("4. Close any open settings screen or pop-up in Tally while connecting.")
    messagebox.showinfo("Connection details", "\n".join(lines))


def set_status(connected, text):
    status_dot.configure(fg=GREEN if connected else RED)
    status_text.configure(text=text)


def show_note(text, colour):
    tb_strip.show(text, colour)


def show_fa_note(text, colour):
    fa_strip.show(text, colour)


def financial_years(info):
    # ("FY 2021-22", first day) from the year the books begin up to this year.
    first = year_start_for(info["books_from"] or date.today(), info["fy_month"], info["fy_day"])
    last = year_start_for(date.today(), info["fy_month"], info["fy_day"])
    years, start = [], first
    while start <= last:
        years.append(("FY " + str(start.year) + "-" + str(start.year + 1)[2:], start))
        start = date(start.year + 1, start.month, start.day)
    return years


def on_company_changed(event=None):
    company = company_box.get()
    info = state["companies"].get(company)
    if not info:
        return
    year_box.configure(values=[label for label, start in financial_years(info)])
    if state.get("books_loaded_for") != info["name"]:
        state["books_loaded_for"] = info["name"]
        load_books_choice(info["name"])
    if state["defaults_set_for"] != company:              # fill default dates once per company
        state["defaults_set_for"] = company
        if info["period_from"] and info["period_to"]:
            start, end = info["period_from"], info["period_to"]       # Tally's current period (Alt+F2)
        else:
            start = year_start_for(info["books_from"] or date.today(), info["fy_month"], info["fy_day"])
            end = year_end_for(start)
        set_dates(start, end)
        year_box.set("")


def on_year_chosen(event=None):
    info = state["companies"].get(company_box.get())
    for label, start in (financial_years(info) if info else []):
        if label == year_box.get():
            set_dates(start, year_end_for(start))


def set_dates(start, end):
    from_box.delete(0, "end")
    from_box.insert(0, show_date(start))
    to_box.delete(0, "end")
    to_box.insert(0, show_date(end))


def read_inputs(note):
    # Checks company and period. Returns (port, company, info, from, to) or None after showing why.
    info = state["companies"].get(company_box.get().strip())
    from_date, to_date = parse_user_date(from_box.get()), parse_user_date(to_box.get())
    port, company = (info["port"], info["name"]) if info else (None, "")
    if not state["connect_on"]:
        note("Not connected. Click Connect at the top.", RED)
    elif not info:
        note("No company selected. Open a company in Tally - it appears in the list within a few seconds.", RED)
    elif not from_date or not to_date:
        note("Enter the period as dd-mm-yyyy, e.g. 01-04-2021 to 31-03-2022.", RED)
    elif from_date > to_date:
        note("The From date is after the To date.", RED)
    elif (year_start_for(from_date, info["fy_month"], info["fy_day"]) !=
          year_start_for(to_date, info["fy_month"], info["fy_day"])):
        note("The period must be within one financial year.", RED)
    else:
        return port, company, info, from_date, to_date
    return None


def start_busy(button):
    state["busy"] = True
    button.configure(state="disabled", bg="#F8C9A0")
    progress.configure(mode="indeterminate")
    progress.start(12)


def stop_busy():
    state["busy"] = False
    progress.stop()
    progress.configure(mode="determinate", value=0)
    extract_button.configure(state="normal", bg=ORANGE)
    fa_extract_button.configure(state="normal", bg=ORANGE)
    fa_test_button.configure(state="normal", bg=BLUE)
    fa_cancel_button.configure(state="disabled")
    for button in (sr_extract_button, sr_pdf_button):
        button.configure(state="normal", bg=ORANGE if button is sr_extract_button else BLUE)
    sr_cancel_button.configure(state="disabled")


def on_extract():
    if state["busy"]:
        return
    inputs = read_inputs(show_note)
    if not inputs:
        return
    port, company, info, from_date, to_date = inputs
    start_busy(extract_button)
    show_note("Reading ledgers from Tally for " + show_date(from_date) + " to " + show_date(to_date) + "...", MUTED)
    threading.Thread(target=extract_job, args=inputs, daemon=True).start()


def refresh_table(*ignore):
    # Redraws the TB table and the three checks from the extracted TB, tick box and search box.
    table.delete(*table.get_children())
    tb = state["tb"]
    if tb is None:
        return
    export_rows = visible_rows()
    rows = visible_rows(search_box.get())
    for index, r in enumerate(rows):
        table.insert("", "end", values=[r["name"], r["group"]] + [indian(r[k]) if r[k] else "" for k in AMOUNT_KEYS],
                     tags=("odd" if index % 2 else "even",))
    totals = totals_of(export_rows)
    table.insert("", "end", values=["TOTAL (rows to be exported)", ""] + [indian(totals[k]) for k in AMOUNT_KEYS],
                 tags=("total",))
    hidden = len(tb["rows"]) - len(export_rows)
    count_label.configure(text=str(len(rows)) + " shown  |  " + str(len(export_rows)) + " will be exported" +
                          ("  |  " + str(hidden) + " zero-balance hidden" if hidden else ""))
    for label, dr_key, cr_key in ((open_check, "op_dr", "op_cr"), (period_check, "pd_dr", "pd_cr"),
                                  (close_check, "cl_dr", "cl_cr")):
        difference = round(totals[dr_key] - totals[cr_key], 2)
        label.configure(text=indian(difference), fg=GREEN if abs(difference) < 0.01 else RED)


def ask_save_path(kind, prefix, company, period):
    extension = ".xlsx" if kind == "Excel" else ".pdf"
    safe_company = re.sub(r'[\\/:*?"<>|]', "_", company).strip(" .")[:60] or "Company"
    suggested = prefix + "_" + safe_company + "_" + period.replace(" to ", "_to_") + extension
    return filedialog.asksaveasfilename(title="Export to " + kind, initialdir=state["last_folder"],
                                        initialfile=suggested, defaultextension=extension,
                                        filetypes=[(kind + " file", "*" + extension)])


def open_file(path):
    try:
        if os.name == "nt":
            os.startfile(path)                      # open the exported file straight away
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def packages_ready(kind, note):
    if kind == "Excel" and openpyxl is None:
        note("Excel export needs openpyxl. In Command Prompt run:  py -m pip install openpyxl", RED)
        return False
    if kind == "PDF" and not reportlab_ready:
        note("PDF export needs reportlab. In Command Prompt run:  py -m pip install reportlab", RED)
        return False
    return True


def on_export(kind):
    tb = state["tb"]
    if tb is None:
        return show_note("Extract a Trial Balance first.", RED)
    if not packages_ready(kind, show_note):
        return
    path = ask_save_path(kind, "TB", state["tb_company"], tb["period"])
    if not path:
        return
    rows = visible_rows()
    try:
        if kind == "Excel":
            export_excel(path, state["tb_company"], tb, rows)
        else:
            export_pdf(path, state["tb_company"], tb, rows)
    except PermissionError:
        return show_note("Could not save - the file is open in another program. Close it and try again.", RED)
    except Exception as error:
        return show_note("Could not save the " + kind + " file: " + str(error), RED)
    state["last_folder"] = os.path.dirname(path)
    show_note("Exported " + str(len(rows)) + " ledgers to " + kind + ":  " + path, GREEN)
    open_file(path)


# ----------------------------------------------------------------------------- Tab 2 actions
def on_fa_extract(test=False):
    if state["busy"]:
        return
    inputs = read_inputs(show_fa_note)
    if not inputs:
        return
    port, company, info, from_date, to_date = inputs
    year_start = year_start_for(from_date, info["fy_month"], info["fy_day"])
    state["fa_fy_days"] = (year_end_for(year_start) - year_start).days + 1      # 365 or 366
    fa_cancel.clear()
    start_busy(fa_test_button if test else fa_extract_button)
    fa_extract_button.configure(state="disabled")
    fa_test_button.configure(state="disabled")
    fa_cancel_button.configure(state="normal")
    if test:
        show_fa_note("Testing the voucher read on the first month of the period...", MUTED)
    else:
        show_fa_note("Reading fixed asset vouchers for " + show_date(from_date) + " to " + show_date(to_date) +
                     " - month by month...", MUTED)
    job = fa_test_job if test else fa_extract_job
    threading.Thread(target=job, args=(port, company, from_date, to_date), daemon=True).start()


def on_fa_cancel():
    fa_cancel.set()
    fa_cancel_button.configure(state="disabled")
    show_fa_note("Cancelling - stopping after the request Tally is working on now...", AMBER)


def set_books_choice(entity, method):
    # Shows the choice in the two boxes and keeps it in state (used by the calculations and exports).
    state["fa_entity"], state["fa_method"] = entity, method
    entity_box.set(entity)
    method_box.set(method)
    basis_label.configure(text="Books rate: " + ("Companies Act (Schedule II)" if books_on_companies_act()
                                                 else "Income-tax rates") + ("   \u26a0 see note" if books_warning() else ""),
                          fg=AMBER if books_warning() else MUTED)


def load_books_choice(company):
    saved = load_settings(company)
    entity = saved.get("entity") if saved.get("entity") in ENTITY_TYPES else guess_entity(company)
    method = saved.get("method") if saved.get("method") in BOOK_METHODS else default_method(entity)
    set_books_choice(entity, method)
    state["fa_entity_guessed"] = not saved


def on_entity_chosen(event=None):
    entity = entity_box.get()
    apply_books_choice(entity, default_method(entity))       # each entity starts on its usual method


def on_method_chosen(event=None):
    apply_books_choice(entity_box.get(), method_box.get())


def apply_books_choice(entity, method):
    # Re-works books depreciation for every row straight away. Books % goes back to the standard rate.
    set_books_choice(entity, method)
    state["fa_entity_guessed"] = False
    info = state["companies"].get(company_box.get().strip())
    if info:
        save_settings(info["name"], entity, method)
    for row in state["fa_rows"]:
        row["co_rate"] = default_books_rate(row["asset_class"])
        fa_compute(row, state["fa_end"])
    if state["fa_rows"] or state.get("fa_entries"):
        refresh_fa_table()
    headline = (("\u26a0 " if books_warning() else "\u2714 ") + "Books depreciation: " + entity + " - " + method +
                (".  Recalculated for all rows (Books % typed by hand was reset)." if state["fa_rows"] else ".") +
                ("  Read the caution in Notes." if books_warning() else ""))
    old_notes = [line for line in fa_strip.full.split("\n")[1:]
                 if line.strip() and not line.startswith(("Caution: a company", "Books depreciation:"))]
    notes = ([books_warning()] if books_warning() else []) + old_notes
    fa_strip.show("\n".join([headline] + notes), AMBER if books_warning() else GREEN, open_notes=bool(books_warning()))


def set_fa_view(view):
    # "key" shows the main columns only; "all" shows every column of the working.
    state["fa_view"] = view
    fa_table.configure(displaycolumns=FA_KEY_VIEW if view == "key" else "#all")


def fa_shown_keys():
    shown = fa_table["displaycolumns"]
    return [key for key, t, w, e in FA_COLUMNS] if not shown or shown[0] == "#all" else list(shown)


def refresh_fa_table():
    fa_table.delete(*fa_table.get_children())
    rows = state["fa_rows"]
    search = fa_search_box.get().strip().lower()
    shown = []
    for index, r in enumerate(rows):
        haystack = " ".join(str(r.get(k, "")) for k in ("invoice", "party", "description", "ledger", "asset_class",
                                                          "gstn")).lower()
        if search and search not in haystack:
            continue
        shown.append(r)
        values = [str(index + 1) if key == "sl" else fa_cell(r, key) for key, title, width, editable in FA_COLUMNS]
        tag = ("unclassified" if r.get("asset_class") == "Not classified" else "itc_no" if r["itc"] == "No"
               else "odd" if len(shown) % 2 else "even")
        fa_table.insert("", "end", iid=str(index), values=values, tags=(tag,))
    if rows:
        totals = {k: sum(r[k] for r in shown) for k in FA_MONEY}
        values = [("TOTAL (filtered)" if search else "TOTAL") if key == "party" else
                  indian(totals[key]) if key in FA_MONEY else "" for key, t, w, e in FA_COLUMNS]
        fa_table.insert("", "end", iid="total", values=values, tags=("total",))
    recon = fa_reconciliation(rows, state["fa_tb_debits"])
    state["fa_recon"] = recon
    books_value.configure(text=indian(recon["tb_debits"]) if recon["tb_debits"] is not None else "n/a")
    picked_value.configure(text=indian(recon["taxable"]))
    if recon["picked_gap"] is None:
        gap_value.configure(text="-", fg=MUTED)
    else:
        ok = abs(recon["picked_gap"]) < 0.01
        gap_value.configure(text=indian(recon["picked_gap"]) + ("  ✔" if ok else "  ✖"), fg=GREEN if ok else RED)
    fa_rebuild()


ENTRY_COLUMNS = [("sl", "Sl", 40), ("date", "Date", 90), ("voucher", "Voucher", 120), ("type", "Type ✎", 190),
                 ("ledger", "Ledger", 200), ("asset_class", "Asset Class", 170), ("party", "Other side", 190),
                 ("book", "Book value", 110), ("consideration", "Sale value (net of GST)", 130), ("gst", "GST on sale", 90),
                 ("pl", "Profit / (Loss)", 110), ("accdep", "Acc. dep. adjusted", 110), ("narration", "Narration", 280)]
SCHEDULE_COLUMNS = [("ledger", "Ledger", 220), ("asset_class", "Asset Class \u270e", 190), ("opening", "Opening", 110),
                    ("additions", "Additions", 110), ("deletions", "Deletions", 110), ("transfers", "Transfers out", 100),
                    ("dep_booked", "Dep. booked in Tally", 120), ("computed", "Closing (worked out)", 125),
                    ("closing_tally", "Closing in Tally", 120), ("difference", "Difference", 100), ("rate", "Books %", 65),
                    ("app_dep", "Books dep. (app)", 115), ("dep_gap", "Booked - app", 100),
                    ("app_closing", "Closing WDV (app)", 125), ("consideration", "Sale value", 100),
                    ("book_pl", "Profit / (Loss) on sale", 125), ("check", "Check", 520)]
BLOCK_COLUMNS = [("block", "Block", 230), ("rate", "Rate %", 60), ("opening", "Opening WDV ✎", 120),
                 ("ge180", "Additions ≥180 days", 125), ("lt180", "Additions <180 days", 125),
                 ("returns", "Purchase returns", 105), ("sales", "Sale value", 110), ("wdv", "WDV before dep.", 120),
                 ("dep", "Depreciation", 110), ("closing", "Closing WDV", 120), ("stcg", "Sec 50 STCG", 100),
                 ("flag", "Check", 480)]


def money_text(value):
    return "" if value is None else indian(value) if value else "-"


def fa_rebuild():
    # Re-works the deletions view, the schedule and the Income-tax blocks from the current rows and entries.
    rows, entries = state["fa_rows"], state.get("fa_entries", [])
    if not state.get("fa_balances_from"):
        return
    schedule = fa_schedule(rows, entries, state.get("fa_balances", {}), state.get("fa_masters", {}),
                           state["fa_company"], state["fa_balances_from"], state["fa_end"], state["fa_fy_days"])
    class_of = {x["ledger"]: x["asset_class"] for x in schedule}
    for e in entries:
        e["asset_class"] = class_of.get(e["ledger"], "Accumulated depreciation" if e.get("is_accdep") else "")
    blocks = fa_blocks(rows, entries, schedule, load_it_openings(state["fa_company"], state["fa_period"]))
    state["fa_schedule"], state["fa_blocks"] = schedule, blocks
    search = fa_search_box.get().strip().lower()

    entry_table.delete(*entry_table.get_children())
    for index, e in enumerate(entries):
        if search and search not in " ".join(str(e.get(k, "")) for k in ("ledger", "party", "type", "voucher",
                                                                           "narration")).lower():
            continue
        values = [str(index + 1) if k == "sl" else e["date"].strftime("%d-%m-%Y") if k == "date" else
                  money_text(e.get(k)) if k in ("book", "consideration", "gst", "pl", "accdep") else str(e.get(k, ""))
                  for k, t, w in ENTRY_COLUMNS]
        tag = ("bad" if e["type"] == E_OTHER else "check" if e["type"] in (E_WRITEOFF, E_RETURN) else
               "excluded" if e["type"] == E_EXCLUDED else "accdep" if e.get("is_accdep") else "even")
        entry_table.insert("", "end", iid=str(index), values=values, tags=(tag,))
    if entries:
        visible = [entries[int(i)] for i in entry_table.get_children()]
        totals = ["", "", "", "TOTAL (excl. acc. dep. and excluded)", "", "", ""] + [
            money_text(sum(e[k] for e in visible if not e.get("is_accdep") and e["type"] != E_EXCLUDED))
            for k in ("book", "consideration", "gst", "pl", "accdep")] + [""]
        entry_table.insert("", "end", iid="total", values=totals, tags=("total",))

    schedule_table.delete(*schedule_table.get_children())
    for index, x in enumerate(schedule):
        values = [x[k] if k in ("ledger", "asset_class", "check") else ("%.2f" % x[k] if x[k] else "-") if k == "rate"
                  else money_text(x[k]) for k, t, w in SCHEDULE_COLUMNS]
        bad = ((x["difference"] is not None and abs(x["difference"]) >= 1) or x["asset_class"] == "Not classified"
               or x.get("negative"))
        tag = ("bad" if bad else "accdep" if x.get("is_accdep") else
               "check" if x["dep_gap"] and abs(x["dep_gap"]) >= 1 else "even")
        schedule_table.insert("", "end", iid=str(index), values=values, tags=(tag,))
    assets = [x for x in schedule if not x.get("is_accdep")]
    if assets:
        totals = ["TOTAL (asset ledgers)", ""] + ["" if k in ("rate", "check") else
                                                 money_text(sum((x[k] or 0) for x in assets if x[k] is not None))
                                                 for k, t, w in SCHEDULE_COLUMNS[2:]]
        schedule_table.insert("", "end", iid="total", values=totals, tags=("total",))

    block_table.delete(*block_table.get_children())
    block_keys = ("opening", "ge180", "lt180", "returns", "sales", "wdv", "dep", "closing", "stcg")
    for index, b in enumerate(blocks):
        values = [b["block"], "%g" % b["rate"]] + [money_text(b[k]) for k in block_keys] + [b["flag"]]
        tag = "bad" if b["stcg"] else "check" if b["flag"] else "even"
        block_table.insert("", "end", iid=str(index), values=values, tags=(tag,))
    if blocks:
        totals = ["TOTAL", ""] + [money_text(sum(b[k] for b in blocks)) for k in block_keys] + [""]
        block_table.insert("", "end", iid="total", values=totals, tags=("total",))

    checked = [x for x in schedule if x["difference"] is not None]
    tied = [x for x in checked if abs(x["difference"]) < 1]
    deletions_value.configure(text=indian(sum(x["deletions"] for x in assets)))
    if checked:
        all_ok = len(tied) == len(checked)
        tied_value.configure(text=str(len(tied)) + " / " + str(len(checked)) + ("  ✔" if all_ok else "  ✖"),
                             fg=GREEN if all_ok else RED)
    else:
        tied_value.configure(text="n/a", fg=MUTED)
    co_dep_value.configure(text=indian(sum(x["app_dep"] for x in assets)))
    it_dep_value.configure(text=indian(sum(b["dep"] for b in blocks)))


def on_entry_double_click(event):
    # Only the Type can be changed - e.g. confirm a write-off, or classify an "Other - check" entry.
    row_id, column_id = entry_table.identify_row(event.y), entry_table.identify_column(event.x)
    if not row_id or row_id == "total" or not column_id:
        return
    key = ENTRY_COLUMNS[int(column_id.replace("#", "")) - 1][0]
    if key != "type":
        return fa_strip.flash("Only the Type can be changed here (double-click it).", AMBER)
    entry = state["fa_entries"][int(row_id)]
    box = entry_table.bbox(row_id, column_id)
    if not box:
        return
    editor = ttk.Combobox(entry_table, values=ENTRY_TYPES, state="readonly", font=("Segoe UI", 10))
    editor.set(entry["type"])
    editor.place(x=box[0], y=box[1], width=max(box[2], 230), height=box[3])
    editor.focus_set()

    def done(event=None):
        if not editor.winfo_exists():
            return
        new = editor.get()
        editor.destroy()
        reclassify_entry(entry, new)
    editor.bind("<<ComboboxSelected>>", done)
    editor.bind("<FocusOut>", done)


def reclassify_entry(entry, new):
    if not new or new == entry["type"]:
        return
    entry.setdefault("original_consideration", entry["consideration"])
    entry["type"] = new
    entry["consideration"] = entry["original_consideration"] if new in CONSIDERATION_TYPES else 0.0
    if new in (E_LOSS, E_WRITEOFF):
        entry["pl"] = -entry["book"]
    refresh_fa_table()
    fa_strip.flash("Entry re-classified as '" + new + "'. Schedule and Income-tax blocks recalculated "
                   "(not saved for the next extraction).", GREEN)


def on_block_double_click(event):
    # Opening WDV of a block - from last year's tax computation. Saved for this company and period.
    row_id, column_id = block_table.identify_row(event.y), block_table.identify_column(event.x)
    if not row_id or row_id == "total" or not column_id:
        return
    if BLOCK_COLUMNS[int(column_id.replace("#", "")) - 1][0] != "opening":
        return fa_strip.flash("Only the Opening WDV can be changed here (double-click it).", AMBER)
    block = state["fa_blocks"][int(row_id)]
    box = block_table.bbox(row_id, column_id)
    if not box:
        return
    editor = tk.Entry(block_table, font=("Segoe UI", 10), relief="solid", bd=1)
    editor.insert(0, "%.2f" % (block["opening"] or 0))
    editor.select_range(0, "end")
    editor.place(x=box[0], y=box[1], width=max(box[2], 120), height=box[3])
    editor.focus_set()

    def done(event=None):
        if not editor.winfo_exists():
            return
        text = editor.get()
        editor.destroy()
        set_block_opening(block, text)
    editor.bind("<Return>", done)
    editor.bind("<Escape>", lambda e: editor.destroy())
    editor.bind("<FocusOut>", done)


def set_block_opening(block, text):
    try:
        value = round(float(str(text).replace(",", "").strip() or 0), 2)
    except ValueError:
        return fa_strip.flash("Opening WDV not changed - type a number.", RED)
    save_it_opening(state["fa_company"], state["fa_period"], block["block"], value)
    refresh_fa_table()
    fa_strip.flash("Opening WDV for '" + block["block"] + "' set to " + indian(value) + " and saved for this company "
                   "and period.", GREEN)


FA_EDITABLE_TEXT = "Invoice No, Put to use date, Description, Disc, ITC, Asset Class, Books % and IT %"


def on_fa_double_click(event):
    # Edits a cell in place. Asset Class applies to every row of that ledger and is remembered.
    row_id = fa_table.identify_row(event.y)
    column_id = fa_table.identify_column(event.x)
    if not row_id or row_id == "total" or not column_id:
        return
    key = fa_shown_keys()[int(column_id.replace("#", "")) - 1]
    title = {k: t for k, t, w, e in FA_COLUMNS}[key]
    if not {k: e for k, t, w, e in FA_COLUMNS}[key]:
        fa_strip.flash("'" + title + "' is worked out by the app or comes from Tally. You can edit: " +
                     FA_EDITABLE_TEXT + ".", AMBER)
        return
    fa_table.see(row_id)
    box = fa_table.bbox(row_id, column_id)
    if not box:
        return
    x, y, w, h = box
    row = state["fa_rows"][int(row_id)]
    if key in ("itc", "asset_class"):
        choices = ["Yes", "No"] if key == "itc" else [name for name, co, it, words in ASSET_CLASSES]
        editor = ttk.Combobox(fa_table, values=choices, state="readonly", font=("Segoe UI", 10))
        editor.set(row[key])
        editor.bind("<<ComboboxSelected>>", lambda e: commit_edit(editor, row, key))
        width = 90 if key == "itc" else 300
    else:
        editor = tk.Entry(fa_table, font=("Segoe UI", 10), relief="solid", bd=1)
        current = "%.2f" % row[key] if key in ("disc", "co_rate", "it_rate") else fa_cell(row, key)
        editor.insert(0, current)
        editor.select_range(0, "end")
        editor.bind("<Return>", lambda e: commit_edit(editor, row, key))
        editor.bind("<Escape>", lambda e: editor.destroy())
        width = 90
    editor.place(x=x, y=y, width=max(w, width), height=h)
    editor.focus_set()
    editor.bind("<FocusOut>", lambda e: commit_edit(editor, row, key))


def use_master(master):
    # Applies a new rate master and recalculates every row (rates typed by hand are reset).
    apply_rate_master(master)
    for row in state["fa_rows"]:
        if row["asset_class"] not in CLASS_RATES:
            row["asset_class"] = "Not classified"
        row["co_rate"], row["it_rate"] = default_books_rate(row["asset_class"]), CLASS_RATES[row["asset_class"]][1]
        fa_compute(row, state["fa_end"])
    set_books_choice(state.get("fa_entity", ENTITY_TYPES[0]), state.get("fa_method", METHOD_DAYS))
    if state["fa_rows"] or state.get("fa_entries"):
        refresh_fa_table()


def open_rate_master():
    # Small window to edit the asset classes and their Companies Act / Income-tax rates.
    win = tk.Toplevel(window)
    win.title("Asset class and depreciation rate master")
    win.geometry("1060x540")
    win.configure(bg=BG)
    win.transient(window)
    work = current_master()
    tk.Label(win, text="Update here when the law changes. Companies Act % = WDV rate for the Schedule II useful life; "
                       "Income-tax % = block rate (Appendix I). Key words help the app guess the class from ledger "
                       "names. Saved in fa_rate_master.json next to the app.\nRenaming or deleting a class makes "
                       "ledgers already mapped to it 'Not classified' - they will show in red.",
             bg=BG, fg=MUTED, font=("Segoe UI", 9), justify="left", anchor="w", wraplength=1020).pack(fill="x", padx=10,
                                                                                                    pady=(8, 4))
    columns = [("name", "Asset class", 280), ("co", "Companies Act %", 110), ("it", "Income-tax %", 100),
               ("it_type", "Income-tax block type", 170), ("words", "Key words (comma separated)", 360)]
    frame = tk.Frame(win, bg=BG)
    frame.pack(fill="both", expand=True, padx=10)
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings", style="TB.Treeview")
    for key, title, width in columns:
        tree.heading(key, text=title + " ✎")
        tree.column(key, width=width, anchor="e" if key in ("co", "it") else "w", stretch=key == "words")
    scroll_bar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll_bar.set)
    scroll_bar.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    note = tk.Label(win, text="Double-click a cell to change it.", bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w")

    def show():
        tree.delete(*tree.get_children())
        for index, m in enumerate(work):
            tree.insert("", "end", iid=str(index), values=[m["name"], "%.2f" % float(m["co"]), "%.2f" % float(m["it"]),
                                                          m["it_type"], ", ".join(m["words"])])

    def edit(event):
        row_id, column_id = tree.identify_row(event.y), tree.identify_column(event.x)
        if not row_id or not column_id:
            return
        key = columns[int(column_id.replace("#", "")) - 1][0]
        item = work[int(row_id)]
        if key == "name" and item["name"] in FIXED_CLASSES:
            return note.configure(text="'" + item["name"] + "' is used by the app and cannot be renamed.", fg=AMBER)
        x, y, w, h = tree.bbox(row_id, column_id)
        if key == "it_type":
            editor = ttk.Combobox(tree, values=IT_TYPES, font=("Segoe UI", 10))
            editor.set(item["it_type"])
        else:
            editor = tk.Entry(tree, font=("Segoe UI", 10), relief="solid", bd=1)
            editor.insert(0, ", ".join(item["words"]) if key == "words" else
                          ("%.2f" % float(item[key])) if key in ("co", "it") else item[key])
            editor.select_range(0, "end")
        editor.place(x=x, y=y, width=max(w, 160), height=h)
        editor.focus_set()

        def done(event=None):
            if not editor.winfo_exists():
                return
            text = editor.get().strip()
            editor.destroy()
            if key in ("co", "it"):
                try:
                    value = float(text.replace("%", ""))
                    if not 0 <= value <= 100:
                        raise ValueError
                except ValueError:
                    return note.configure(text="Rate not changed - type a number between 0 and 100.", fg=RED)
                item[key] = round(value, 2)
            elif key == "words":
                item["words"] = [w.strip().lower() for w in text.split(",") if w.strip()]
            elif key == "name":
                if not text or any(m is not item and m["name"] == text for m in work):
                    return note.configure(text="Name not changed - it must be filled in and different from the others.",
                                          fg=RED)
                item["name"] = text
            else:
                item[key] = text
            note.configure(text="Changed - click Save to apply.", fg=AMBER)
            show()
        editor.bind("<Return>", done)
        editor.bind("<Escape>", lambda e: editor.destroy())
        editor.bind("<FocusOut>", done)
        if key == "it_type":
            editor.bind("<<ComboboxSelected>>", done)

    def add():
        work.insert(len(work) - 2, {"name": "New class " + str(len(work)), "co": 0.0, "it": 0.0,
                                    "it_type": "Plant & machinery", "words": []})
        show()
        note.configure(text="New class added above CWIP - double-click to name it and set the rates.", fg=AMBER)

    def delete():
        chosen = tree.selection()
        if not chosen:
            return note.configure(text="Select a class first.", fg=AMBER)
        item = work[int(chosen[0])]
        if item["name"] in FIXED_CLASSES:
            return note.configure(text="'" + item["name"] + "' is used by the app and cannot be deleted.", fg=AMBER)
        work.remove(item)
        show()
        note.configure(text="Deleted - click Save to apply.", fg=AMBER)

    def reset():
        work[:] = [dict(m, words=list(m["words"])) for m in DEFAULT_MASTER]
        show()
        note.configure(text="Standard classes and rates restored - click Save to apply.", fg=AMBER)

    def save():
        try:
            save_rate_master(work)
        except OSError as error:
            return note.configure(text="Could not save: " + str(error), fg=RED)
        use_master(work)
        fa_strip.flash("Rate master saved. All rows recalculated with the new rates (rates typed by hand were reset).",
                       GREEN)
        win.destroy()

    tree.bind("<Double-1>", edit)
    note.pack(fill="x", padx=10, pady=(4, 0))
    buttons = tk.Frame(win, bg=BG)
    buttons.pack(fill="x", padx=10, pady=8)
    colour_button(buttons, "Add class", add, BLUE, BLUE_DARK).pack(side="left")
    colour_button(buttons, "Delete class", delete, "#6B7280", "#4B5563").pack(side="left", padx=6)
    colour_button(buttons, "Reset to standard rates", reset, "#6B7280", "#4B5563").pack(side="left")
    colour_button(buttons, "Cancel", win.destroy, "#6B7280", "#4B5563").pack(side="right")
    colour_button(buttons, "Save", save, GREEN_BTN, "#1B5E20").pack(side="right", padx=6)
    show()
    state["rate_window"] = win
    return win


def set_ledger_class(ledger, asset_class):
    # One class per ledger: applied to every addition row of the ledger and remembered for next time.
    same = [r for r in state["fa_rows"] if r["ledger"] == ledger]
    for other in same:
        other["asset_class"], other["class_source"] = asset_class, "saved"
        other["co_rate"], other["it_rate"] = default_books_rate(asset_class), CLASS_RATES[asset_class][1]
        fa_compute(other, state["fa_end"])
    saved = save_class(state["fa_company"], ledger, asset_class)
    return ("Asset class '" + asset_class + "' set for ledger '" + ledger + "' (" + str(len(same)) + " addition row(s)), "
            "with its standard rates. " + ("It will be remembered next time." if saved else
                                           "Could not save the choice for next time (folder is read-only)."))


def on_schedule_double_click(event):
    row_id, column_id = schedule_table.identify_row(event.y), schedule_table.identify_column(event.x)
    if not row_id or row_id == "total" or not column_id:
        return
    if SCHEDULE_COLUMNS[int(column_id.replace("#", "")) - 1][0] != "asset_class":
        return fa_strip.flash("Only the Asset Class can be changed here (double-click it).", AMBER)
    line = state["fa_schedule"][int(row_id)]
    if line.get("is_accdep"):
        return fa_strip.flash("Accumulated depreciation ledgers have no asset class.", AMBER)
    box = schedule_table.bbox(row_id, column_id)
    if not box:
        return
    editor = ttk.Combobox(schedule_table, values=[c[0] for c in ASSET_CLASSES], state="readonly", font=("Segoe UI", 10))
    editor.set(line["asset_class"])
    editor.place(x=box[0], y=box[1], width=max(box[2], 300), height=box[3])
    editor.focus_set()

    def done(event=None):
        if not editor.winfo_exists():
            return
        chosen = editor.get()
        editor.destroy()
        if chosen in CLASS_RATES and chosen != line["asset_class"]:
            message = set_ledger_class(line["ledger"], chosen)
            refresh_fa_table()
            fa_strip.flash(message, GREEN)
    editor.bind("<<ComboboxSelected>>", done)
    editor.bind("<FocusOut>", done)


def commit_edit(editor, row, key):
    if not editor.winfo_exists():
        return
    text = editor.get().strip()
    editor.destroy()
    message = "Updated. Capitalised value, 180-day split, depreciation and the totals have been recalculated."
    if key == "put_date":
        new_date = parse_user_date(text)
        if not new_date:
            return fa_strip.flash("Date not changed - type it as dd-mm-yyyy.", RED)
        if new_date > state["fa_end"]:
            return fa_strip.flash("Date not changed - it is after the end of the period.", RED)
        row["put_date"] = new_date
    elif key in ("disc", "co_rate", "it_rate"):
        try:
            value = float(text.replace(",", "").replace("%", "") or 0)
        except ValueError:
            return fa_strip.flash("Not changed - type a number.", RED)
        limit = row["taxable"] + row["cgst"] + row["sgst"] + row["igst"] if key == "disc" else 100
        if value < 0 or value > limit:
            return fa_strip.flash("Not changed - it must be between 0 and " + indian(limit) + ".", RED)
        row[key] = round(value, 2)
    elif key == "itc":
        row["itc"] = "Yes" if text == "Yes" else "No"
    elif key == "asset_class":
        if text not in CLASS_RATES:
            return
        message = set_ledger_class(row["ledger"], text)
    elif key == "invoice":
        row["invoice"] = text or row["invoice"]
    else:
        row[key] = text
    fa_compute(row, state["fa_end"])
    refresh_fa_table()
    fa_strip.flash(message, GREEN)


def on_fa_export(kind):
    if not state["fa_rows"] and not state.get("fa_entries") and not state.get("fa_schedule"):
        return show_fa_note("Extract the Fixed Asset Additions first.", RED)
    if not packages_ready(kind, show_fa_note):
        return
    path = ask_save_path(kind, "FA_Working", state["fa_company"], state["fa_period"])
    if not path:
        return
    try:
        if kind == "Excel":
            export_fa_excel(path, state["fa_company"], state["fa_period"], state["fa_rows"], state["fa_recon"],
                            state["fa_end"], state["fa_fy_days"])
        else:
            export_fa_pdf(path, state["fa_company"], state["fa_period"], state["fa_rows"], state["fa_recon"],
                          state["fa_end"], state["fa_fy_days"])
    except PermissionError:
        return show_fa_note("Could not save - the file is open in another program. Close it and try again.", RED)
    except Exception as error:
        return show_fa_note("Could not save the " + kind + " file: " + str(error), RED)
    state["last_folder"] = os.path.dirname(path)
    show_fa_note("Exported " + str(len(state["fa_rows"])) + " additions to " + kind + ":  " + path, GREEN)
    open_file(path)


def check_messages():
    try:
        while True:
            message = messages.get_nowait()
            if message[0] == "connection":
                state["checking"] = False
                if not state["connect_on"]:
                    continue                                   # disconnected while the check was running
                results = message[1]
                state["probe"] = results
                companies = {}
                for port, status, found, detail in results:
                    for name, info in found.items():
                        companies[name + "   (port " + str(port) + ")"] = dict(info, port=port, name=name)
                tallies = [r for r in results if r[1] in ("tally", "no_company")]
                if companies:
                    labels = list(companies)
                    if labels != list(state["companies"]):
                        company_box.configure(values=labels)
                    state["companies"] = companies
                    if company_box.get() not in labels:
                        company_box.set(labels[0])
                    on_company_changed()
                    summary = "   |   ".join("Port " + str(p) + ": " + d for p, st, f, d in results if st in ("tally", "no_company", "busy"))
                    set_status(True, "Connected to " + str(len(tallies)) + " Tally   |   " + summary)
                else:
                    state["companies"] = {}
                    company_box.configure(values=[])
                    company_box.set("")
                    busy = [r for r in results if r[1] == "busy"]
                    if tallies:
                        set_status(False, "Tally is running but no company is open - open a company in Tally.")
                    elif busy:
                        set_status(False, "Port " + str(busy[0][0]) + " is not answering - close any open screen or "
                                   "pop-up in Tally.  Click 'Connection details' for help.")
                    else:
                        set_status(False, "No Tally found on port(s) " + port_box.get().strip() +
                                   ".  Click 'Connection details' for help.")
            elif message[0] in ("extracted", "failed"):
                stop_busy()
                if message[0] == "failed":
                    show_note(message[1], RED)
                    continue
                state["tb"], state["tb_company"] = message[1], message[2]
                refresh_table()
                totals = totals_of(visible_rows())
                agrees = all(abs(totals[a] - totals[b]) < 0.01
                             for a, b in (("op_dr", "op_cr"), ("pd_dr", "pd_cr"), ("cl_dr", "cl_cr")))
                text = (state["tb_company"] + "  |  " + state["tb"]["period"] + "  |  " +
                        str(len(state["tb"]["rows"])) + " ledgers read. " +
                        ("Opening, period and closing all agree." if agrees else
                         "Difference found - compare with Tally's own Trial Balance."))
                for note in state["tb"]["notes"]:
                    text += "\n" + note
                net_warning = any("NET period movement" in note for note in state["tb"]["notes"])
                show_note(text, RED if not agrees else AMBER if net_warning else GREEN)
                export_excel_button.configure(state="normal")
                export_pdf_button.configure(state="normal")
            elif message[0] == "sr_progress":
                if state["busy"]:
                    progress.stop()
                    progress.configure(mode="determinate", value=message[2])
                    sr_strip.flash(message[1], MUTED)
            elif message[0] == "sr_pdfs":
                stop_busy()
                handle_sr_pdfs(message[1], list(message[2]))
            elif message[0] in ("sr_extracted", "sr_failed"):
                stop_busy()
                if message[0] == "sr_failed":
                    show_sr_note(message[1], message[2] if len(message) > 2 else RED)
                else:
                    handle_sr_extracted(message[1], message[2], message[3])
            elif message[0] == "fa_progress":
                if state["busy"]:
                    progress.stop()
                    progress.configure(mode="determinate", value=message[2])
                    show_fa_note(message[1], MUTED)
            elif message[0] == "fa_test":
                stop_busy()
                fa_strip.show(message[1], GREEN if message[2] else AMBER, open_notes=True)
            elif message[0] in ("fa_extracted", "fa_failed"):
                stop_busy()
                if message[0] == "fa_failed":
                    show_fa_note(message[1], message[2] if len(message) > 2 else RED)
                    continue
                rows, tb_debits, warnings, company, period, period_end, ledger_count = message[1:8]
                extra = message[8] if len(message) > 8 else {}
                state.update({"fa_rows": rows, "fa_tb_debits": tb_debits, "fa_company": company,
                              "fa_period": period, "fa_end": period_end, "fa_entries": extra.get("entries", []),
                              "fa_balances": extra.get("balances", {}), "fa_masters": extra.get("masters", {}),
                              "fa_balances_from": extra.get("from")})
                refresh_fa_table()
                recon = state["fa_recon"]
                gap_ok = recon["picked_gap"] is None or abs(recon["picked_gap"]) < 0.01
                real_warnings = [w for w in warnings if not w.startswith(("Read by", "Books figure"))]
                headline = (("\u2714 " if gap_ok and rows and not real_warnings else "\u26a0 ") + str(len(rows)) +
                            " addition(s) from " + str(ledger_count) + " fixed asset ledger(s)  \u00b7  " + period +
                            ("  \u00b7  ties to books" if recon["picked_gap"] is not None and gap_ok else
                             "  \u00b7  books figure not available" if recon["picked_gap"] is None else
                             "  \u00b7  " + indian(recon["picked_gap"]) + " NOT picked up - see notes") +
                            ("  \u00b7  " + str(len(real_warnings)) + " point(s) to check" if real_warnings else ""))
                schedule = [x for x in state.get("fa_schedule", []) if x["difference"] is not None]
                untied = [x["ledger"] for x in schedule if abs(x["difference"]) >= 1]
                others = [e for e in state["fa_entries"] if e["type"] == E_OTHER]
                headline += "  \u00b7  " + str(len([e for e in state["fa_entries"] if e["type"] in DELETION_TYPES
                                                    and not e.get("is_accdep")])) + " deletion entr(ies)"
                if schedule:
                    headline += ("  \u00b7  schedule ties to Tally" if not untied else
                                 "  \u00b7  " + str(len(untied)) + " ledger(s) do not tie to Tally")
                if untied:
                    real_warnings.append("Schedule: " + str(len(untied)) + " ledger(s) do not tie to Tally's closing "
                                         "balance - see the Schedule tab (red rows): " + ", ".join(untied[:6]))
                if others:
                    real_warnings.append(str(len(others)) + " entr(ies) could not be classified - see 'Deletions & other "
                                         "entries' (red rows) and set the Type.")
                text = headline + "\n" + "\n".join(real_warnings + [w for w in warnings if w not in real_warnings])
                text += "\nBooks depreciation: " + state["fa_entity"] + " - " + state["fa_method"] + (
                    "  (entity guessed from the company name - confirm it in the Entity box)"
                    if state.get("fa_entity_guessed") else "")
                if books_warning():
                    text += "\n" + books_warning()
                text += "\nDouble-click a \u270e column to edit (" + FA_EDITABLE_TEXT + ")."
                show_fa_note(text, GREEN if gap_ok and rows and not real_warnings else AMBER if rows else RED)
                fa_excel_button.configure(state="normal")
                fa_pdf_button.configure(state="normal")
    except queue.Empty:
        pass
    window.after(150, check_messages)


# ----------------------------------------------------------------------------- Tab 3 - Sales reconciliation
def show_sr_note(text, colour):
    sr_strip.show(text, colour)


def on_sr_extract():
    if state["busy"]:
        return
    inputs = read_inputs(show_sr_note)
    if not inputs:
        return
    port, company, info, from_date, to_date = inputs
    fy_start = year_start_for(from_date, info["fy_month"], info["fy_day"])
    fy_end = year_end_for(fy_start)
    fy_label = "FY " + str(fy_start.year) + "-" + str(fy_start.year + 1)[2:]
    data = sr_load(company, fy_label)
    state.update({"sr_data": data, "sr_year": data["companies"][company][fy_label], "sr_company": company,
                  "sr_fy_start": fy_start, "sr_fy_end": fy_end, "sr_fy_label": fy_label,
                  "sr_party_class": data["companies"][company]["party_class"]})
    fa_cancel.clear()
    start_busy(sr_extract_button)
    sr_cancel_button.configure(state="normal")
    show_sr_note("Reading sales, credit notes and other income for " + show_date(from_date) + " to " + show_date(to_date) +
                 " - month by month...", MUTED)
    threading.Thread(target=sr_extract_job, args=(port, company, from_date, to_date, fy_start, fy_end, fy_label),
                     daemon=True).start()


def on_sr_cancel():
    fa_cancel.set()
    sr_cancel_button.configure(state="disabled")
    show_sr_note("Cancelling - stopping after the request Tally is working on now...", AMBER)


def on_sr_load(folder=False):
    if state["busy"]:
        return
    if folder:
        chosen = filedialog.askdirectory(title="Folder with the GSTR-1 / 1A / 3B PDFs",
                                         initialdir=state.get("sr_pdf_folder") or state["last_folder"])
        if not chosen:
            return
        names = sorted(n for n in os.listdir(chosen) if n.lower().endswith(".pdf"))
        gst_names = [n for n in names if n.upper().startswith("GSTR")]
        paths = [os.path.join(chosen, n) for n in (gst_names or names)]
        state["sr_pdf_folder"] = chosen
    else:
        paths = list(filedialog.askopenfilenames(title="Choose GSTR-1 / 1A / 3B PDFs", filetypes=[("PDF files", "*.pdf")],
                                                 initialdir=state.get("sr_pdf_folder") or state["last_folder"]))
        if paths:
            state["sr_pdf_folder"] = os.path.dirname(paths[0])
    if not paths:
        return show_sr_note("No PDF files found.", AMBER)
    start_busy(sr_pdf_button)
    show_sr_note("Reading " + str(len(paths)) + " PDF(s) - nothing is saved...", MUTED)
    threading.Thread(target=sr_pdf_job, args=(paths,), daemon=True).start()


def sr_visible(tab):
    search = sr_search_box.get().strip().lower()
    out = []
    for index, row in enumerate(state.get("sr_rows", [])):
        if row["tab"] != tab:
            continue
        if search and search not in " ".join(str(row.get(k, "")) for k in ("party", "invoice", "gstin", "category",
                                                                          "ledger", "vtype", "remark")).lower():
            continue
        out.append((index, row))
    return out


def sr_cell(row, key):
    value = row.get(key)
    if key in ("month_paid",):
        return value.strftime("%b-%y") if value else ""
    if key in ("inv_date", "orig_date"):
        return value.strftime("%d-%m-%Y") if isinstance(value, date) else (value or "")
    if key == "rate":
        return value if isinstance(value, str) else ("%g%%" % (value * 100) if value else "0%")
    if key == "fx_rate":
        return "%g" % value if value else ""
    if key in SR_MONEY:
        return indian(value) if value else ""
    return "" if value is None else str(value)


def refresh_sr():
    keys = [k for k, t, w in SR_COLUMNS] + [k for k, t, w in SR_EXTRA]
    for table, tab in ((sr_gst_table, "gst"), (sr_nogst_table, "nogst")):
        table.delete(*table.get_children())
        shown = sr_visible(tab)
        for index, row in shown:
            tag = ("bad" if "export_inr" in row["flags"] else "excluded" if row["category"] in (C_NEXT_PLUS, C_NEXT_MINUS)
                   else "check" if row["flags"] or row["rate"] == "Mixed" else "even")
            table.insert("", "end", iid=str(index), values=[sr_cell(row, k) for k in keys], tags=(tag,))
        if shown:
            total = {k: sum(r[k] or 0 for i, r in shown) for k in ("inv_value", "taxable", "igst", "cgst", "sgst", "cess")}
            table.insert("", "end", iid="total", values=["", "TOTAL (" + str(len(shown)) + ")"] +
                         [indian(total[k]) if k in total else "" for k in keys[2:]], tags=("total",))
    recon = sr_recon()
    for table in (sr_month_table, sr_returns_table, sr_recon_table, sr_bridge_table, sr_adv_table):
        table.delete(*table.get_children())
    if recon:
        tables = ["4A", "5A", "6A", "6B", "6C", "7", "9B", "9A", "8"]
        for m in recon["months"]:
            data = recon["by_paid"][m]
            comparable_total = [0.0] * 5
            for t, values in data.items():
                if t != "8":
                    comparable_total = add5(comparable_total, values)
            sr_month_table.insert("", "end", values=[m.strftime("%b-%y")] + [money_text(data.get(t, [0.0])[0])
                                                                            for t in tables] +
                                  [money_text(v) for v in comparable_total[:4]])
        codes = ["4A", "5", "6A", "6B", "6C", "7", "9A", "9B-R", "9B-U", "9C", "10", "8"]
        for m in recon["months"]:
            r = recon["returns"].get(m, {})
            g1, g1a, g3 = r.get("GSTR-1"), r.get("GSTR-1A"), r.get("GSTR-3B")
            out = r1_outward(g1 or {})
            values = [m.strftime("%b-%y"), "✔" if g1 is not None else "-", "✔" if g1a is not None else "-",
                      "✔" if g3 is not None else "-"]
            values += [money_text(out[i]) if g1 is not None else "" for i in range(4)]
            values += [money_text((g1 or {}).get(c, [0.0])[0]) if g1 is not None else "" for c in codes]
            values += [money_text(r1_outward(g1a)[0]) if g1a is not None else ""]
            values += [money_text(g3.get("3.1a", [0.0] * 5)[i]) if g3 is not None else "" for i in range(4)]
            values += [money_text(g3.get(k, [0.0])[0]) if g3 is not None else "" for k in ("3.1b", "3.1c", "3.1d", "3.1e")]
            sr_returns_table.insert("", "end", values=values)
        for item in recon["monthly"]:
            row = [item["month"].strftime("%b-%y")] + [money_text(v) for v in item["books"][:4]]
            for key in ("r1", "r3b", "d_r1", "d_3b"):
                row += [money_text(v) for v in item[key][:4]] if item[key] else [""] * 4
            row += [money_text(item["r1_3b"][0]) if item["r1_3b"] else ""]
            bad = any(item[k] and any(abs(v) >= 1 for v in item[k][:4]) for k in ("d_r1", "d_3b"))
            sr_recon_table.insert("", "end", values=row, tags=("bad" if bad else "even",))
        t = recon["totals"]
        sr_recon_table.insert("", "end", values=["TOTAL"] + [money_text(v) for v in t["books"][:4] + t["r1"][:4] + t["r3b"][:4]] +
                              [money_text(a - b) for a, b in zip(t["books"][:4], t["r1"][:4])] +
                              [money_text(a - b) for a, b in zip(t["books"][:4], t["r3b"][:4])] +
                              [money_text(t["r1"][0] - t["r3b"][0])], tags=("total",))
        for label, values in recon["bridge"]:
            sr_bridge_table.insert("", "end", values=[label] + [money_text(v) for v in values])
        sr_bridge_table.insert("", "end", values=["Expected as per returns"] + [money_text(v) for v in recon["expected"]],
                               tags=("total",))
        if recon["loaded_r1"] < 12 or recon["loaded_3b"] < 12:
            sr_bridge_table.insert("", "end", values=["Note: not all 12 months of returns are loaded - the unexplained "
                                                      "difference includes the months still missing."] + [""] * 4,
                                   tags=("check",))
        sr_bridge_table.insert("", "end", values=["GSTR-1 + 1A for the year (" + str(recon["loaded_r1"]) + " of 12 months)"] +
                               [money_text(v) for v in recon["totals"]["r1"][:4]])
        sr_bridge_table.insert("", "end", values=["Unexplained difference vs GSTR-1"] + [money_text(v) for v in recon["gap_r1"]],
                               tags=("bad" if any(abs(v) >= 1 for v in recon["gap_r1"]) else "total",))
        sr_bridge_table.insert("", "end", values=["GSTR-3B for the year (" + str(recon["loaded_3b"]) + " of 12 months)"] +
                               [money_text(v) for v in recon["totals"]["r3b"][:4]])
        sr_bridge_table.insert("", "end", values=["Unexplained difference vs GSTR-3B"] + [money_text(v) for v in recon["gap_3b"]],
                               tags=("bad" if any(abs(v) >= 1 for v in recon["gap_3b"]) else "total",))
        for item in recon["advances"]:
            sr_adv_table.insert("", "end", values=[item["month"].strftime("%b-%y")] +
                                [money_text(v) for v in item["11A"][:4] + item["11B"][:4]])
        sr_books_value.configure(text=indian(t["books"][0]))
        sr_r1_value.configure(text=indian(t["r1"][0]) if recon["loaded_r1"] else "not loaded")
        sr_3b_value.configure(text=indian(t["r3b"][0]) if recon["loaded_3b"] else "not loaded")
        for label, gap, loaded in ((sr_gap1_value, recon["gap_r1"], recon["loaded_r1"]),
                                   (sr_gap3_value, recon["gap_3b"], recon["loaded_3b"])):
            if not loaded:
                label.configure(text="-", fg=MUTED)
            else:
                ok = abs(gap[0]) < 1
                label.configure(text=indian(gap[0]) + ("  ✔" if ok else "  ✖"), fg=GREEN if ok else RED)
        sr_months_value.configure(text=str(recon["loaded_r1"]) + " R1 / " + str(recon["loaded_3b"]) + " 3B of 12")
    sr_bucket_table.delete(*sr_bucket_table.get_children())
    for index, item in enumerate(state.get("sr_year", {}).get("buckets", [])):
        sr_bucket_table.insert("", "end", iid=str(index), values=[item.get(k, "") for k, t, w in BUCKET_COLUMNS])
    info = state.get("sr_info") or {}
    if info.get("books_income") is not None:
        gap = round(info["books_income"] - info["picked_income"], 2)
        sr_tie_value.configure(text=("tied ✔" if abs(gap) < 1 else indian(gap) + "  ✖"),
                               fg=GREEN if abs(gap) < 1 else RED)


def sr_save_now():
    if state.get("sr_data") and not sr_save(state["sr_data"]):
        sr_strip.flash("Could not save your changes (folder is read-only).", RED)


def on_sr_double_click(table, event):
    row_id, column_id = table.identify_row(event.y), table.identify_column(event.x)
    if not row_id or row_id == "total" or not column_id:
        return
    keys = [k for k, t, w in SR_COLUMNS] + [k for k, t, w in SR_EXTRA]
    key = keys[int(column_id.replace("#", "")) - 1]
    if key not in ("month_paid", "category"):
        return sr_strip.flash("You can change Month Paid (3B) and Category here (double-click them).", AMBER)
    row = state["sr_rows"][int(row_id)]
    box = table.bbox(row_id, column_id)
    if not box:
        return
    if key == "category":
        editor = ttk.Combobox(table, values=SR_CAT_NAMES, state="readonly", font=("Segoe UI", 10))
        editor.set(row["category"])
        width = 380
    else:
        editor = tk.Entry(table, font=("Segoe UI", 10), relief="solid", bd=1)
        editor.insert(0, row["month_paid"].strftime("%m-%Y"))
        editor.select_range(0, "end")
        width = 100
    editor.place(x=box[0], y=box[1], width=max(box[2], width), height=box[3])
    editor.focus_set()

    def done(event=None):
        if not editor.winfo_exists():
            return
        text = editor.get().strip()
        editor.destroy()
        set_sr_value(row, key, text)
    editor.bind("<Return>", done)
    editor.bind("<Escape>", lambda e: editor.destroy())
    editor.bind("<FocusOut>", done)
    if key == "category":
        editor.bind("<<ComboboxSelected>>", done)


def set_sr_value(row, key, text):
    year, fy_end = state["sr_year"], state["sr_fy_end"]
    if key == "month_paid":
        try:
            month = datetime.strptime(text, "%m-%Y").date()
        except ValueError:
            return sr_strip.flash("Month Paid not changed - type it as mm-yyyy, e.g. 04-2026.", RED)
        year["month_paid"][row["key"]] = month.strftime("%Y-%m")
        finish_sr_row(row, fy_end, year["category"].get(row["key"]), year["month_paid"][row["key"]])
        message = ("Month Paid (3B) set to " + month.strftime("%b-%Y") +
                   (" - after the year end, so it now counts as declared in next FY." if month > fy_end else "."))
    else:
        if text not in SR_CAT_NAMES:
            return
        if text == row["category"]:
            if not row["flags"]:
                return
            year["category"][row["key"]] = text                     # confirmed - clear the "check" mark
            row["flags"] = [f for f in row["flags"] if f not in ("nongst",)]
            sr_save_now()
            refresh_sr()
            return sr_strip.flash("Category '" + text + "' confirmed for this row.", GREEN)
        new_class = CLASS_OF_CATEGORY.get(text)
        if new_class and new_class != row["class"]:
            # A party-type choice (B2B / B2C / export / SEZ / deemed): remembered for the party, applied to all its rows.
            state["sr_party_class"][row["party"]] = new_class
            same = [r for r in state["sr_rows"] if r["party"] == row["party"]]
            for other in same:
                other["class"], other["class_reason"] = new_class, "chosen by you"
                other["auto_category"] = category_for(new_class, other["doc"], other["has_tax"],
                                                      "Non-GST" if other["auto_category"] == C_NONGST else
                                                      "Exempted" if other["auto_category"] == C_EXEMPT else
                                                      "Nil Rated" if other["auto_category"] == C_NIL else "Non-GST")
                year["category"].pop(other["key"], None)
                other["flags"] = [f for f in other["flags"] if f != "nongst"]
                finish_sr_row(other, fy_end, None, year["month_paid"].get(other["key"]))
            message = ("Party '" + row["party"] + "' treated as " + new_class + " - applied to its " + str(len(same)) +
                       " row(s) and remembered.")
        else:
            year["category"][row["key"]] = text
            row["flags"] = [f for f in row["flags"] if f != "nongst"]
            finish_sr_row(row, fy_end, text, year["month_paid"].get(row["key"]))
            message = "Category set to '" + text + "' for this row and remembered."
    sr_save_now()
    refresh_sr()
    sr_strip.flash(message, GREEN)


def on_bucket_add():
    if not state.get("sr_year") and not state.get("sr_company"):
        return sr_strip.flash("Extract the sales first - items are saved per company and year.", AMBER)
    state["sr_year"]["buckets"].append({"bucket": BUCKETS[0], "return_month": "", "invoice": "", "inv_date": "",
                                        "party": "", "gstin": "", "taxable": 0, "igst": 0, "cgst": 0, "sgst": 0,
                                        "remark": ""})
    sr_save_now()
    refresh_sr()
    sr_strip.flash("Item added - double-click its cells to fill it in. Amounts are entered as positive figures; "
                   "the bucket decides add or less ('Other' is taken with its sign).", GREEN)


def on_bucket_delete():
    chosen = sr_bucket_table.selection()
    if not chosen:
        return sr_strip.flash("Select an item first.", AMBER)
    state["sr_year"]["buckets"].pop(int(chosen[0]))
    sr_save_now()
    refresh_sr()


def on_bucket_double_click(event):
    row_id, column_id = sr_bucket_table.identify_row(event.y), sr_bucket_table.identify_column(event.x)
    if not row_id or not column_id:
        return
    key = BUCKET_COLUMNS[int(column_id.replace("#", "")) - 1][0]
    item = state["sr_year"]["buckets"][int(row_id)]
    box = sr_bucket_table.bbox(row_id, column_id)
    if not box:
        return
    if key == "bucket":
        editor = ttk.Combobox(sr_bucket_table, values=BUCKETS, state="readonly", font=("Segoe UI", 10))
        editor.set(item.get("bucket", BUCKETS[0]))
    else:
        editor = tk.Entry(sr_bucket_table, font=("Segoe UI", 10), relief="solid", bd=1)
        editor.insert(0, str(item.get(key, "")))
        editor.select_range(0, "end")
    editor.place(x=box[0], y=box[1], width=max(box[2], 300 if key == "bucket" else 110), height=box[3])
    editor.focus_set()

    def done(event=None):
        if not editor.winfo_exists():
            return
        text = editor.get().strip()
        editor.destroy()
        if key in ("taxable", "igst", "cgst", "sgst"):
            try:
                text = round(float(text.replace(",", "") or 0), 2)
            except ValueError:
                return sr_strip.flash("Not changed - type a number.", RED)
        item[key] = text
        sr_save_now()
        refresh_sr()
    editor.bind("<Return>", done)
    editor.bind("<Escape>", lambda e: editor.destroy())
    editor.bind("<FocusOut>", done)
    if key == "bucket":
        editor.bind("<<ComboboxSelected>>", done)


def on_sr_export(kind):
    if not state.get("sr_rows") and not state.get("sr_pdfs"):
        return show_sr_note("Extract the sales (and/or load the GSTR PDFs) first.", RED)
    if not packages_ready("Excel", show_sr_note):
        return
    company, label = state.get("sr_company") or "Company", state.get("sr_fy_label") or "FY"
    if kind == "recon":
        path = ask_save_path("Excel", "Sales_Recon", company, label)
        if not path:
            return
        try:
            export_sr_excel(path, company, label)
        except PermissionError:
            return show_sr_note("Could not save - the file is open in another program. Close it and try again.", RED)
        except Exception as error:
            return show_sr_note("Could not save the Excel file: " + str(error), RED)
        state["last_folder"] = os.path.dirname(path)
        show_sr_note("Reconciliation exported:  " + path, GREEN)
        return open_file(path)
    if not state.get("sr_rows"):
        return show_sr_note("Extract the sales first.", RED)
    data = state.get("sr_data") or sr_load(company, label)
    template = data.get("template", "")
    if not template or not os.path.exists(template):
        template = filedialog.askopenfilename(title="Choose your GST register template (the .xlsm with the Sales Register sheet)",
                                              filetypes=[("Excel workbook", "*.xlsm *.xlsx")],
                                              initialdir=state["last_folder"])
        if not template:
            return
        data["template"] = template
        sr_save_now()
    extension = os.path.splitext(template)[1].lower()
    safe = re.sub(r'[\\/:*?"<>|]', "_", company).strip(" .")[:60]
    path = filedialog.asksaveasfilename(title="Save the filled GST register as", initialdir=state["last_folder"],
                                        initialfile="GST_Register_" + safe + "_" + label.replace(" ", "_") + extension,
                                        defaultextension=extension, filetypes=[("Excel workbook", "*" + extension)])
    if not path:
        return
    if os.path.abspath(path) == os.path.abspath(template):
        return show_sr_note("Choose a different name - your template itself is never overwritten.", RED)
    show_sr_note("Filling your GST register... (Excel works in the background - this can take a minute)", MUTED)
    window.update()
    try:
        notes = export_sr_template(template, path)
    except PermissionError:
        return show_sr_note("Could not save - the file is open in another program. Close it and try again.", RED)
    except Exception as error:
        return show_sr_note("Could not fill the GST register: " + str(error), RED)
    state["last_folder"] = os.path.dirname(path)
    show_sr_note("Sales Register filled (" + str(len(state["sr_rows"])) + " rows):  " + path + "\n" + "\n".join(notes),
                 GREEN if len(notes) == 1 and notes[0].startswith("Filled with Excel") else AMBER)
    open_file(path)


def on_sr_change_template():
    template = filedialog.askopenfilename(title="Choose your GST register template", filetypes=[("Excel workbook", "*.xlsm *.xlsx")],
                                          initialdir=state["last_folder"])
    if template:
        data = state.get("sr_data") or sr_load(state.get("sr_company") or "Company", state.get("sr_fy_label") or "FY")
        data["template"] = template
        state["sr_data"] = data
        sr_save_now()
        sr_strip.flash("Template set: " + template, GREEN)


def handle_sr_pdfs(results, problems):
    store = state.setdefault("sr_pdfs", {})
    replaced, lines = 0, []
    for item in results:
        if not item.get("month"):
            problems.append(os.path.basename(item["path"]) + ": the return period could not be read")
            continue
        key = item["form"] + "|" + item["month"].isoformat()
        replaced += key in store
        store[key] = item
        problems.extend(item.get("warnings", []))
    gstins = sorted({i["gstin"] for i in store.values() if i.get("gstin")})
    if len(gstins) > 1:
        problems.insert(0, "PDFs from more than one GSTIN are loaded: " + ", ".join(gstins) + " - check you picked the "
                        "right client.")
    fy_start, fy_end = state.get("sr_fy_start"), state.get("sr_fy_end")
    if fy_start:
        outside = sorted({i["form"] + " " + i["month"].strftime("%b-%Y") for i in store.values()
                          if not (fy_start <= i["month"] <= fy_end)})
        if outside:
            problems.append("Returns outside " + state.get("sr_fy_label", "the year") + " are loaded but not used in the "
                            "monthly reconciliation: " + ", ".join(outside[:8]))
    else:
        # No extraction yet: take the year from the returns themselves.
        months = sorted(i["month"] for i in store.values())
        if months:
            first = months[0]
            start = date(first.year if first.month >= 4 else first.year - 1, 4, 1)
            state.update({"sr_fy_start": start, "sr_fy_end": year_end_for(start),
                          "sr_fy_label": "FY " + str(start.year) + "-" + str(start.year + 1)[2:]})
    forms = {}
    for item in store.values():
        forms[item["form"]] = forms.get(item["form"], 0) + 1
    refresh_sr()
    headline = (("✔ " if not problems else "⚠ ") + str(len(results)) + " PDF(s) read  ·  loaded now: " +
                ", ".join(f + " x" + str(n) for f, n in sorted(forms.items())) +
                ("  ·  " + str(replaced) + " replaced an earlier copy" if replaced else "") +
                ("  ·  GSTIN " + gstins[0] if len(gstins) == 1 else ""))
    show_sr_note("\n".join([headline] + problems + ["The PDFs are read into memory only - nothing is saved."]),
                 GREEN if not problems else AMBER)
    sr_sub.select(sr_pages["Reconciliation"] if state.get("sr_rows") else sr_pages["GST Returns (PDF)"])


def handle_sr_extracted(rows, warnings, info):
    state.update({"sr_rows": rows, "sr_info": info})
    refresh_sr()
    gst = [r for r in rows if r["tab"] == "gst"]
    exports_inr = [r for r in rows if "export_inr" in r["flags"]]
    nongst = [r for r in rows if "nongst" in r["flags"]]
    orig = [r for r in rows if "orig_missing" in r["flags"]]
    mixed = [r for r in rows if r["rate"] == "Mixed"]
    next_fy = [r for r in rows if r["category"] in (C_NEXT_PLUS, C_NEXT_MINUS)]
    notes = []
    tie = None
    if info.get("books_income") is not None:
        tie = round(info["books_income"] - info["picked_income"], 2)
        notes.append("Income tie-out: income ledgers in Tally " + indian(info["books_income"]) + " vs read from vouchers " +
                     indian(info["picked_income"]) + (" - tied." if abs(tie) < 1 else " - DIFFERENCE " + indian(tie) +
                                                    " (some vouchers were not read)."))
    if exports_inr:
        notes.append(str(len(exports_inr)) + " export invoice(s) are not booked in foreign currency - Foreign Amount and "
                     "Exchange rate are shown in red.")
    if nongst:
        notes.append(str(len(nongst)) + " entr(ies) carry no GST and were treated as Non-GST supply (amber) - check the "
                     "category (e.g. interest, provisions).")
    if orig:
        notes.append(str(len(orig)) + " credit / debit note(s) have no original invoice reference in Tally.")
    if mixed:
        notes.append(str(len(mixed)) + " invoice(s) carry more than one tax rate - Rate shows 'Mixed', rates in Remark.")
    if next_fy:
        notes.append(str(len(next_fy)) + " row(s) have Month Paid (3B) after the year end - counted as declared in next FY.")
    if info.get("missing_fields"):
        notes.append("This Tally did not provide: " + ", ".join(info["missing_fields"]) + " - classification used the "
                     "GSTIN, party master and ledger names instead.")
    notes += warnings
    notes.append("Read by " + info["method"] + " in " + str(info["seconds"]) + " seconds from " +
                 str(info["income_ledgers"]) + " income ledger(s).")
    notes.append("Double-click Month Paid (3B) or Category to change it - your changes are saved per company and year.")
    bad = (tie is not None and abs(tie) >= 1) or exports_inr
    headline = (("⚠ " if bad or nongst or orig else "✔ ") + str(len(rows)) + " invoice(s) / note(s): " +
                str(len(gst)) + " with GST, " + str(len(rows) - len(gst)) + " without  ·  " +
                info["fy_label"] + ("  ·  income tie-out ok" if tie is not None and abs(tie) < 1 else ""))
    show_sr_note("\n".join([headline] + notes), RED if bad else AMBER if (nongst or orig) else GREEN)
    if exports_inr:
        messagebox.showwarning("Exports not in foreign currency",
                               str(len(exports_inr)) + " export invoice(s) appear to be booked in rupees only (no "
                               "foreign currency amount in Tally).\n\nThey have been extracted; the Foreign Amount and "
                               "Exchange rate cells are marked red so they can be completed.")


def colour_button(parent, text, command, colour, active):
    return tk.Button(parent, text=text, command=command, bg=colour, fg="white", activebackground=active,
                     activeforeground="white", disabledforeground="#F3F4F6", font=("Segoe UI", 10, "bold"),
                     relief="flat", padx=12, pady=3, cursor="hand2")


class MessageStrip:
    # One coloured line for the headline + a "Notes" button that opens a panel with the details.
    def __init__(self, parent):
        self.bar = tk.Frame(parent, bg=BG)
        self.bar.pack(fill="x", pady=(4, 2))
        self.button = tk.Button(self.bar, text="Notes", command=self.toggle, bg="#E5E7EB", fg=TEXT, relief="flat",
                                font=("Segoe UI", 9, "bold"), padx=10, pady=1, cursor="hand2", state="disabled")
        self.button.pack(side="right")
        self.label = tk.Label(self.bar, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10, "bold"), anchor="w")
        self.label.pack(side="left", fill="x", expand=True)
        self.panel = tk.Frame(parent, bg=CARD, highlightbackground="#E2E8F0", highlightthickness=1)
        self.text = tk.Text(self.panel, height=6, wrap="word", font=("Segoe UI", 9), relief="flat", bg=CARD, fg=TEXT,
                            padx=8, pady=4)
        scroll_bar = ttk.Scrollbar(self.panel, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll_bar.set)
        scroll_bar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.is_open, self.full, self.count = False, "", 0

    def show(self, text, colour, open_notes=False):
        lines = [line for line in text.split("\n") if line.strip()] or [""]
        self.full = text
        self.label.configure(text=lines[0], fg=colour)
        self.count = len(lines) - 1
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", "\n".join("• " + line for line in lines[1:]))
        self.text.configure(state="disabled")
        self.button.configure(state="normal" if self.count else "disabled",
                              bg="#FDE68A" if self.count and colour in (AMBER, RED) else "#E5E7EB")
        self.set_open(self.count > 0 and (self.is_open or open_notes or colour == RED))

    def set_open(self, wanted):
        if wanted and not self.is_open:
            self.panel.pack(fill="x", after=self.bar, pady=(0, 4))
        elif not wanted and self.is_open:
            self.panel.pack_forget()
        self.is_open = wanted
        self.button.configure(text=("Hide notes ▴" if wanted else "Notes (" + str(self.count) + ") ▾")
                              if self.count else "Notes")

    def toggle(self):
        self.set_open(self.count > 0 and not self.is_open)

    def flash(self, text, colour):
        # Changes only the headline - the notes from the last extraction stay available.
        self.label.configure(text=text, fg=colour)


def footer_item(parent, title):
    tk.Label(parent, text=title, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=(9, 3))
    value = tk.Label(parent, text="-", bg=CARD, fg=TEXT, font=("Segoe UI", 10, "bold"))
    value.pack(side="left")
    tk.Label(parent, text="|", bg=CARD, fg="#CBD5E1", font=("Segoe UI", 10)).pack(side="left", padx=(8, 0))
    return value


def make_table(parent, keys, headings, widths, money_keys, horizontal):
    frame = tk.Frame(parent, bg=BG)
    frame.pack(fill="both", expand=True)
    tree = ttk.Treeview(frame, columns=keys, show="headings", style="TB.Treeview")
    for key, heading, width in zip(keys, headings, widths):
        tree.heading(key, text=heading)
        tree.column(key, width=width, minwidth=40, stretch=not horizontal and key not in money_keys,
                    anchor="e" if key in money_keys else "w")
    tree.tag_configure("odd", background="#F8FAFC")
    tree.tag_configure("even", background="#FFFFFF")
    tree.tag_configure("itc_no", background="#FEF3C7")
    tree.tag_configure("unclassified", background="#FEE2E2")
    tree.tag_configure("total", background="#E5E7EB", font=("Segoe UI", 10, "bold"))
    y_scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=y_scroll.set)
    if horizontal:
        x_scroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=x_scroll.set)
        x_scroll.pack(side="bottom", fill="x")
    y_scroll.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    return tree


window = tk.Tk()
window.title("Tally Extractor  -  Trial Balance & Fixed Asset Additions")
window.geometry("1360x840")
window.minsize(1100, 600)
window.configure(bg=BG)
try:
    window.state("zoomed")                       # start maximised on Windows - more room for the table
except tk.TclError:
    pass
state.update({"connect_on": True, "probe": [], "fa_rows": [], "fa_tb_debits": None, "fa_company": "", "fa_period": "",
              "fa_end": date.today(), "fa_recon": None, "fa_fy_days": 365, "fa_view": "key"})

style = ttk.Style()
style.theme_use("clam")
style.configure("Green.Horizontal.TProgressbar", background="#2E9E44", troughcolor="#2B3F6B",
                bordercolor=BLUE_DARK, lightcolor="#2E9E44", darkcolor="#2E9E44")
style.configure("TB.Treeview", rowheight=24, font=("Segoe UI", 10))
style.configure("TB.Treeview.Heading", font=("Segoe UI", 9, "bold"), background=BLUE, foreground="white")
style.map("TB.Treeview.Heading", background=[("active", BLUE_DARK)])
style.configure("TNotebook", background=BG, borderwidth=0)
style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(16, 4))
style.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", BLUE)])

# ---- Bottom status bar: connection + progress
status_bar = tk.Frame(window, bg=BLUE_DARK)
status_bar.pack(side="bottom", fill="x")
status_dot = tk.Label(status_bar, text="●", bg=BLUE_DARK, fg=AMBER, font=("Segoe UI", 12))
status_dot.pack(side="left", padx=(12, 4))
progress = ttk.Progressbar(status_bar, style="Green.Horizontal.TProgressbar", mode="determinate", length=220)
progress.pack(side="right", padx=12, pady=5)
status_text = tk.Label(status_bar, text="Checking connection to Tally...", bg=BLUE_DARK, fg="white",
                       font=("Segoe UI", 9), anchor="w")
status_text.pack(side="left", fill="x", expand=True, pady=4)

# ---- Top bar: company, period, port - one row, shared by both tabs
card = tk.Frame(window, bg=CARD, highlightbackground="#E2E8F0", highlightthickness=1)
card.pack(fill="x", padx=10, pady=(8, 4))
label_style = {"bg": CARD, "fg": TEXT, "font": ("Segoe UI", 10, "bold")}
entry_style = {"font": ("Segoe UI", 10), "relief": "solid", "bd": 1}
tk.Label(card, text="Company", **label_style).pack(side="left", padx=(10, 4), pady=7)
company_box = ttk.Combobox(card, width=42, state="readonly", font=("Segoe UI", 10))
company_box.pack(side="left")
company_box.bind("<<ComboboxSelected>>", on_company_changed)
tk.Label(card, text="Period", **label_style).pack(side="left", padx=(16, 4))
year_box = ttk.Combobox(card, width=10, state="readonly", font=("Segoe UI", 10))
year_box.pack(side="left")
year_box.bind("<<ComboboxSelected>>", on_year_chosen)
tk.Label(card, text="From", bg=CARD, fg=TEXT, font=("Segoe UI", 10)).pack(side="left", padx=(10, 4))
from_box = tk.Entry(card, width=11, **entry_style)
from_box.pack(side="left")
tk.Label(card, text="To", bg=CARD, fg=TEXT, font=("Segoe UI", 10)).pack(side="left", padx=(8, 4))
to_box = tk.Entry(card, width=11, **entry_style)
to_box.pack(side="left")
tk.Button(card, text="?", command=on_details, bg="#E5E7EB", fg=TEXT, relief="flat", font=("Segoe UI", 10, "bold"),
          padx=8, cursor="hand2").pack(side="right", padx=(6, 10))
connect_button = tk.Button(card, text="Disconnect", command=on_connect_toggle, bg="#6B7280", fg="white",
                           activebackground="#4B5563", activeforeground="white", font=("Segoe UI", 10, "bold"),
                           relief="flat", padx=10, pady=2, cursor="hand2", width=10)
connect_button.pack(side="right")
port_box = tk.Entry(card, width=10, **entry_style)
port_box.insert(0, "9000-9005")
port_box.pack(side="right", padx=(4, 8))
tk.Label(card, text="Port", **label_style).pack(side="right")

tabs = ttk.Notebook(window)
tabs.pack(fill="both", expand=True, padx=10, pady=(0, 6))
tb_tab = tk.Frame(tabs, bg=BG, padx=6)
fa_tab = tk.Frame(tabs, bg=BG, padx=6)
tabs.add(tb_tab, text="Trial Balance")
tabs.add(fa_tab, text="Fixed Asset Additions")

# ============================ TAB 1 - TRIAL BALANCE ============================
tb_top = tk.Frame(tb_tab, bg=BG)
tb_top.pack(fill="x", pady=(6, 0))
extract_button = colour_button(tb_top, "Extract Trial Balance", on_extract, ORANGE, "#D9731A")
extract_button.pack(side="left")
tk.Label(tb_top, text="Search", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(18, 4))
search_box = tk.Entry(tb_top, width=24, **entry_style)
search_box.pack(side="left", ipady=2)
search_box.bind("<KeyRelease>", refresh_table)
show_zero_var = tk.BooleanVar(value=False)
tk.Checkbutton(tb_top, text="Show zero-balance ledgers", variable=show_zero_var, command=refresh_table,
               bg=BG, activebackground=BG, font=("Segoe UI", 10)).pack(side="left", padx=(12, 0))
export_pdf_button = colour_button(tb_top, "PDF", lambda: on_export("PDF"), "#B91C1C", "#991B1B")
export_pdf_button.configure(state="disabled")
export_pdf_button.pack(side="right")
export_excel_button = colour_button(tb_top, "Excel", lambda: on_export("Excel"), GREEN_BTN, "#1B5E20")
export_excel_button.configure(state="disabled")
export_excel_button.pack(side="right", padx=(0, 6))
tk.Label(tb_top, text="Export:", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="right", padx=(0, 6))
tb_strip = MessageStrip(tb_tab)
tb_strip.show("Pick the company and period, then click Extract Trial Balance.", MUTED)

tb_footer = tk.Frame(tb_tab, bg=CARD, highlightbackground="#E2E8F0", highlightthickness=1)
tb_footer.pack(side="bottom", fill="x", pady=(4, 6))
open_check = footer_item(tb_footer, "Opening difference")
period_check = footer_item(tb_footer, "Period difference")
close_check = footer_item(tb_footer, "Closing difference")
count_label = tk.Label(tb_footer, text="", bg=CARD, fg=MUTED, font=("Segoe UI", 9))
count_label.pack(side="left", padx=12, pady=5)

columns = ["ledger", "group"] + AMOUNT_KEYS
table = make_table(tb_tab, columns, ["Name of Ledger", "Name of Group"] + AMOUNT_TITLES,
                   [300, 200, 120, 120, 120, 120, 120, 120], AMOUNT_KEYS, horizontal=False)

# ========================== TAB 2 - FIXED ASSET ADDITIONS ==========================
fa_top = tk.Frame(fa_tab, bg=BG)
fa_top.pack(fill="x", pady=(6, 0))
fa_extract_button = colour_button(fa_top, "Extract Additions", on_fa_extract, ORANGE, "#D9731A")
fa_extract_button.pack(side="left")
fa_test_button = colour_button(fa_top, "Test read", lambda: on_fa_extract(test=True), BLUE, BLUE_DARK)
fa_test_button.pack(side="left", padx=(6, 0))
fa_cancel_button = colour_button(fa_top, "Cancel", on_fa_cancel, "#6B7280", "#4B5563")
fa_cancel_button.configure(state="disabled")
fa_cancel_button.pack(side="left", padx=(6, 0))
tk.Label(fa_top, text="Search", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(18, 4))
fa_search_box = tk.Entry(fa_top, width=22, **entry_style)
fa_search_box.pack(side="left", ipady=2)
fa_search_box.bind("<KeyRelease>", lambda e: refresh_fa_table())
fa_pdf_button = colour_button(fa_top, "PDF", lambda: on_fa_export("PDF"), "#B91C1C", "#991B1B")
fa_pdf_button.configure(state="disabled")
fa_pdf_button.pack(side="right")
fa_excel_button = colour_button(fa_top, "Excel", lambda: on_fa_export("Excel"), GREEN_BTN, "#1B5E20")
fa_excel_button.configure(state="disabled")
fa_excel_button.pack(side="right", padx=(0, 6))
tk.Label(fa_top, text="Export:", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="right", padx=(0, 6))
fa_books_row = tk.Frame(fa_tab, bg=BG)
fa_books_row.pack(fill="x", pady=(6, 0))
tk.Label(fa_books_row, text="Entity", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left")
entity_box = ttk.Combobox(fa_books_row, values=ENTITY_TYPES, width=30, state="readonly", font=("Segoe UI", 10))
entity_box.pack(side="left", padx=(4, 16))
entity_box.bind("<<ComboboxSelected>>", on_entity_chosen)
tk.Label(fa_books_row, text="Books depreciation", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left")
method_box = ttk.Combobox(fa_books_row, values=BOOK_METHODS, width=42, state="readonly", font=("Segoe UI", 10))
method_box.pack(side="left", padx=(4, 10))
method_box.bind("<<ComboboxSelected>>", on_method_chosen)
basis_label = tk.Label(fa_books_row, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9))
basis_label.pack(side="left")
tk.Button(fa_books_row, text="\u2699 Rates", command=open_rate_master, bg="#E5E7EB", fg=TEXT, relief="flat",
          font=("Segoe UI", 8), padx=4, pady=0, cursor="hand2").pack(side="left", padx=(10, 0))
fa_view_var = tk.StringVar(value="key")
for text, value in (("All", "all"), ("Key", "key")):
    tk.Radiobutton(fa_books_row, text=text, value=value, variable=fa_view_var,
                   command=lambda: set_fa_view(fa_view_var.get()), bg=BG, activebackground=BG,
                   font=("Segoe UI", 10)).pack(side="right")
tk.Label(fa_books_row, text="Columns", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(0, 2))
fa_strip = MessageStrip(fa_tab)
fa_strip.show("Debits to ledgers under 'Fixed Assets' are listed as additions. Double-click a ✎ column to edit; "
              "yellow = ITC not availed, red = asset class not chosen.", MUTED)

fa_footer = tk.Frame(fa_tab, bg=CARD, highlightbackground="#E2E8F0", highlightthickness=1)
fa_footer.pack(side="bottom", fill="x", pady=(4, 6))
books_value = footer_item(fa_footer, "Books")
picked_value = footer_item(fa_footer, "Picked up")
gap_value = footer_item(fa_footer, "Not picked up")
deletions_value = footer_item(fa_footer, "Deletions")
tied_value = footer_item(fa_footer, "Ledgers tied to Tally")
co_dep_value = footer_item(fa_footer, "Books dep. (year)")
it_dep_value = footer_item(fa_footer, "IT dep. (blocks)")

FA_SHORT = {"sl": "Sl", "put_date": "Put to use", "party": "Party Name", "description": "Description", "gstn": "GSTN",
            "taxable": "Taxable Value", "net": "Net Total", "itc": "ITC", "capitalised": "Capitalised",
            "ledger": "Ledger", "days": "Days", "asset_class": "Asset Class", "co_rate": "Books %",
            "co_dep": "Books Dep.", "co_wdv": "Books WDV", "ge180": "≥180 days", "lt180": "<180 days",
            "it_rate": "IT %", "it_dep": "IT Dep.", "it_wdv": "IT WDV"}
fa_sub = ttk.Notebook(fa_tab)
fa_sub.pack(fill="both", expand=True)
fa_pages = {}
for page_title in ("Additions", "Deletions & other entries", "Fixed Asset Sch - Books", "Income-tax blocks"):
    fa_pages[page_title] = tk.Frame(fa_sub, bg=BG)
    fa_sub.add(fa_pages[page_title], text=page_title)
fa_keys = [key for key, t, w, e in FA_COLUMNS]
fa_table = make_table(fa_pages["Additions"], fa_keys,
                      [FA_SHORT.get(key, title) + (" ✎" if editable else "") for key, title, w, editable in FA_COLUMNS],
                      [width for k, t, width, e in FA_COLUMNS], FA_MONEY + ["days", "sl", "co_rate", "it_rate"],
                      horizontal=True)
fa_table.bind("<Double-1>", on_fa_double_click)
entry_table = make_table(fa_pages["Deletions & other entries"], [k for k, t, w in ENTRY_COLUMNS],
                         [t for k, t, w in ENTRY_COLUMNS], [w for k, t, w in ENTRY_COLUMNS],
                         ["book", "consideration", "gst", "pl", "accdep", "sl"], horizontal=True)
entry_table.bind("<Double-1>", on_entry_double_click)
schedule_table = make_table(fa_pages["Fixed Asset Sch - Books"], [k for k, t, w in SCHEDULE_COLUMNS],
                            [t for k, t, w in SCHEDULE_COLUMNS], [w for k, t, w in SCHEDULE_COLUMNS],
                            [k for k, t, w in SCHEDULE_COLUMNS if k not in ("ledger", "asset_class")], horizontal=True)
block_table = make_table(fa_pages["Income-tax blocks"], [k for k, t, w in BLOCK_COLUMNS],
                         [t for k, t, w in BLOCK_COLUMNS], [w for k, t, w in BLOCK_COLUMNS],
                         [k for k, t, w in BLOCK_COLUMNS if k not in ("block", "flag")], horizontal=True)
block_table.bind("<Double-1>", on_block_double_click)
schedule_table.bind("<Double-1>", on_schedule_double_click)
for tree in (entry_table, schedule_table, block_table):
    tree.tag_configure("bad", background="#FEE2E2")
    tree.tag_configure("check", background="#FEF3C7")
    tree.tag_configure("accdep", background="#EEF2FF")
    tree.tag_configure("excluded", background="#F3F4F6", foreground="#6B7280")
set_fa_view("key")
set_books_choice(ENTITY_TYPES[0], METHOD_DAYS)

# ========================== TAB 3 - SALES RECONCILIATION ==========================
sr_tab = tk.Frame(tabs, bg=BG, padx=6)
tabs.add(sr_tab, text="Sales Reconciliation")
sr_top = tk.Frame(sr_tab, bg=BG)
sr_top.pack(fill="x", pady=(6, 0))
sr_extract_button = colour_button(sr_top, "Extract Sales", on_sr_extract, ORANGE, "#D9731A")
sr_extract_button.pack(side="left")
sr_cancel_button = colour_button(sr_top, "Cancel", on_sr_cancel, "#6B7280", "#4B5563")
sr_cancel_button.configure(state="disabled")
sr_cancel_button.pack(side="left", padx=(6, 0))
sr_pdf_button = colour_button(sr_top, "Load GSTR PDFs", lambda: on_sr_load(False), BLUE, BLUE_DARK)
sr_pdf_button.pack(side="left", padx=(14, 0))
sr_folder_button = colour_button(sr_top, "From folder", lambda: on_sr_load(True), BLUE, BLUE_DARK)
sr_folder_button.pack(side="left", padx=(6, 0))
tk.Label(sr_top, text="Search", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(16, 4))
sr_search_box = tk.Entry(sr_top, width=20, **entry_style)
sr_search_box.pack(side="left", ipady=2)
sr_search_box.bind("<KeyRelease>", lambda e: refresh_sr())
tk.Button(sr_top, text="⚙ Template", command=on_sr_change_template, bg="#E5E7EB", fg=TEXT, relief="flat",
          font=("Segoe UI", 8), padx=4, pady=0, cursor="hand2").pack(side="right", padx=(6, 0))
sr_register_button = colour_button(sr_top, "Into GST Register", lambda: on_sr_export("template"), GREEN_BTN, "#1B5E20")
sr_register_button.pack(side="right")
sr_recon_button = colour_button(sr_top, "Recon Excel", lambda: on_sr_export("recon"), GREEN_BTN, "#1B5E20")
sr_recon_button.pack(side="right", padx=(0, 6))
tk.Label(sr_top, text="Export:", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="right", padx=(0, 6))
sr_strip = MessageStrip(sr_tab)
sr_strip.show("Extract Sales reads Sales Accounts, Direct Incomes and Indirect Incomes (plus fixed asset sales). "
              "Load the GSTR-1 / 1A / 3B PDFs for the year - they are read, never saved.", MUTED)

sr_footer = tk.Frame(sr_tab, bg=CARD, highlightbackground="#E2E8F0", highlightthickness=1)
sr_footer.pack(side="bottom", fill="x", pady=(4, 6))
sr_books_value = footer_item(sr_footer, "Books taxable")
sr_r1_value = footer_item(sr_footer, "GSTR-1 + 1A")
sr_3b_value = footer_item(sr_footer, "GSTR-3B")
sr_gap1_value = footer_item(sr_footer, "Unexplained vs R1")
sr_gap3_value = footer_item(sr_footer, "Unexplained vs 3B")
sr_months_value = footer_item(sr_footer, "Returns loaded")
sr_tie_value = footer_item(sr_footer, "Income tie-out")

sr_sub = ttk.Notebook(sr_tab)
sr_sub.pack(fill="both", expand=True)
sr_pages = {}
for page_title in ("Books - GST charged", "Books - No GST", "Books - Monthly", "GST Returns (PDF)", "Reconciliation",
                   "Year-bucket items", "Advances (11A/11B)"):
    sr_pages[page_title] = tk.Frame(sr_sub, bg=BG)
    sr_sub.add(sr_pages[page_title], text=page_title)
sr_keys = [k for k, t, w in SR_COLUMNS] + [k for k, t, w in SR_EXTRA]
sr_heads = [t + (" ✎" if k in ("month_paid", "category") else "") for k, t, w in SR_COLUMNS + SR_EXTRA]
sr_widths = [w for k, t, w in SR_COLUMNS + SR_EXTRA]
sr_gst_table = make_table(sr_pages["Books - GST charged"], sr_keys, sr_heads, sr_widths, SR_MONEY, horizontal=True)
sr_nogst_table = make_table(sr_pages["Books - No GST"], sr_keys, sr_heads, sr_widths, SR_MONEY, horizontal=True)
for table in (sr_gst_table, sr_nogst_table):
    table.bind("<Double-1>", lambda e, t=table: on_sr_double_click(t, e))
month_keys = ["m", "4A", "5A", "6A", "6B", "6C", "7", "9B", "9A", "8", "tot", "ig", "cg", "sg"]
sr_month_table = make_table(sr_pages["Books - Monthly"], month_keys,
                            ["Month Paid (3B)", "4A B2B", "5A B2CL", "6A Exports", "6B SEZ", "6C Deemed", "7 B2CS",
                             "9B Notes", "9A Amend.", "8 Nil/Exempt/Non-GST", "Total taxable (excl. 8)", "IGST", "CGST",
                             "SGST"], [90] + [105] * 13, month_keys[1:], horizontal=True)
ret_keys = ["m", "r1", "r1a", "r3b", "o_t", "o_i", "o_c", "o_s", "4A", "5", "6A", "6B", "6C", "7", "9A", "9BR", "9BU", "9C",
            "10", "8", "1A", "a_t", "a_i", "a_c", "a_s", "b", "c", "d", "e"]
sr_returns_table = make_table(sr_pages["GST Returns (PDF)"], ret_keys,
                              ["Month", "R1", "1A", "3B", "R1 outward taxable", "R1 IGST", "R1 CGST", "R1 SGST", "4A", "5",
                               "6A", "6B", "6C", "7", "9A net", "9B regd.", "9B unregd.", "9C net", "10", "8",
                               "1A outward taxable", "3B 3.1(a) taxable", "3B IGST", "3B CGST", "3B SGST", "3.1(b)",
                               "3.1(c)", "3.1(d) RCM", "3.1(e)"], [70, 40, 40, 40] + [105] * 25, ret_keys[4:],
                              horizontal=True)
recon_page = sr_pages["Reconciliation"]
recon_top = tk.Frame(recon_page, bg=BG)
recon_top.pack(fill="both", expand=True)
recon_keys = ["m"] + ["%s_%s" % (g, k) for g in ("b", "r1", "r3", "d1", "d3") for k in ("t", "i", "c", "s")] + ["x"]
recon_heads = ["Month"] + ["%s %s" % (g, k) for g in ("Books", "R1+1A", "3B", "Books-R1", "Books-3B")
                           for k in ("taxable", "IGST", "CGST", "SGST")] + ["R1-3B taxable"]
sr_recon_table = make_table(recon_top, recon_keys, recon_heads, [70] + [105] * 21, recon_keys[1:], horizontal=True)
sr_recon_table.configure(height=14)
tk.Label(recon_page, text="Year-end bridge: books to returns", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold"),
         anchor="w").pack(fill="x", pady=(6, 2))
recon_bottom = tk.Frame(recon_page, bg=BG, height=210)
recon_bottom.pack(fill="x")
recon_bottom.pack_propagate(False)
sr_bridge_table = make_table(recon_bottom, ["p", "t", "i", "c", "s"], ["Particulars", "Taxable", "IGST", "CGST", "SGST"],
                             [620, 130, 120, 120, 120], ["t", "i", "c", "s"], horizontal=False)
bucket_page = sr_pages["Year-bucket items"]
bucket_bar = tk.Frame(bucket_page, bg=BG)
bucket_bar.pack(fill="x", pady=(6, 4))
colour_button(bucket_bar, "Add item", on_bucket_add, BLUE, BLUE_DARK).pack(side="left")
colour_button(bucket_bar, "Delete item", on_bucket_delete, "#6B7280", "#4B5563").pack(side="left", padx=6)
tk.Label(bucket_bar, text="Previous-year invoices / notes and amendments declared in this year's returns. Current-year "
                          "items declared next year come from Month Paid (3B) in the books tabs. Saved per company and "
                          "year.", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=10)
sr_bucket_table = make_table(bucket_page, [k for k, t, w in BUCKET_COLUMNS], [t + " ✎" for k, t, w in BUCKET_COLUMNS],
                             [w for k, t, w in BUCKET_COLUMNS], ["taxable", "igst", "cgst", "sgst"], horizontal=True)
sr_bucket_table.bind("<Double-1>", on_bucket_double_click)
adv_page = sr_pages["Advances (11A/11B)"]
tk.Label(adv_page, text="Basic view: advances as declared in GSTR-1 (tables 11A / 11B). Voucher-level tracking - advance "
                        "receipt, party and the invoice later raised - will be added in a later version.",
         bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(6, 4))
adv_keys = ["m", "at", "ai", "ac", "as", "bt", "bi", "bc", "bs"]
sr_adv_table = make_table(adv_page, adv_keys, ["Month", "11A taxable", "11A IGST", "11A CGST", "11A SGST", "11B taxable",
                                               "11B IGST", "11B CGST", "11B SGST"], [80] + [120] * 8, adv_keys[1:],
                          horizontal=False)
for tree in (sr_gst_table, sr_nogst_table, sr_recon_table, sr_bridge_table):
    tree.tag_configure("bad", background="#FEE2E2")
    tree.tag_configure("check", background="#FEF3C7")
    tree.tag_configure("excluded", background="#F3F4F6", foreground="#6B7280")

window.after(150, check_messages)
window.after(300, schedule_check)
window.mainloop()
