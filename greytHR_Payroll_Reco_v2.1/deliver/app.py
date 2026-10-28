"""
greytHR Payroll Reconciliation Tool  -  version 2.0 (corrected)

Reconciles two consecutive greytHR "Salary Statement" exports (previous month vs
current month) at gross, deduction and net-pay level and produces a formula-linked
Excel workbook.

Key rules implemented in this version
-------------------------------------
* ZERO-TOLERANCE: there are no amount or percentage thresholds. A difference of
  Rs 0.00 is a match; any other difference (including Rs 1 or a few paise) is an
  exception and is reported.
* All amounts are held as exact decimals (Python Decimal), so comparisons are exact
  and are never rounded before comparison.
* The GROSS, TOTAL DEDUCTIONS and NET PAY columns in the export are the source of
  truth. Nothing is plugged or forced: unexplained amounts are shown as such.
* greytHR exports TOTAL DEDUCTIONS as a negative number while the individual
  deduction components are positive. The sign convention is detected per file,
  documented in the workbook, and deductions are always handled as positive
  amounts internally (Net = Gross - Deductions).
* Columns are classified by name first (lists below) and by position only as a
  fallback; every column's treatment is shown in the "Column Mapping" sheet.

Run with:   python -m streamlit run app.py      (or double-click the .bat launcher)
"""

import datetime
import hashlib
import io
import json
import os
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import openpyxl
import pandas as pd
from openpyxl.formatting.rule import FormulaRule, Rule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.styles.numbers import NumberFormat
from openpyxl.utils import get_column_letter

APP_VERSION = "2.1"

# =============================================================================
# SETTINGS  -  column names recognised in greytHR exports.
# Headings are compared after converting to upper case and collapsing spaces.
# Add your client's headings here if they differ.
# =============================================================================
ID_ALIASES = ["EMPLOYEE NO", "EMPLOYEE NO.", "EMP NO", "EMP NO.", "EMPLOYEE NUMBER",
              "EMPLOYEE CODE", "EMP CODE", "EMPLOYEE ID", "EMP ID"]
NAME_ALIASES = ["EMPLOYEE NAME", "NAME", "EMP NAME", "FULL NAME", "EMPLOYEE FULL NAME"]
GROSS_ALIASES = ["GROSS", "GROSS SALARY", "GROSS EARNINGS", "TOTAL EARNINGS", "GROSS PAY"]
TOTAL_DED_ALIASES = ["TOTAL DEDUCTIONS", "TOTAL DEDUCTION", "DEDUCTIONS TOTAL"]
NET_ALIASES = ["NET PAY", "NET SALARY", "NET AMOUNT", "NET"]

# Descriptive (non-pay) columns, kept under their own labels.
JOIN_DATE_ALIASES = ["JOIN DATE", "DATE OF JOINING", "DOJ", "JOINING DATE"]
LEFT_ALIASES = ["LEFT?", "LEFT"]
STATUS_ALIASES = ["STATUS", "EMPLOYEE STATUS"]
DAYS_ALIASES = ["DAYS IN MONTH", "MONTH DAYS", "TOTAL DAYS"]
PAID_DAYS_ALIASES = ["EMP EFFECTIVE WORKDAYS", "EFFECTIVE WORKDAYS", "PAID DAYS", "PAYABLE DAYS"]
LOP_ALIASES = ["LOP", "LOP DAYS", "LOSS OF PAY DAYS", "LOSS OF PAY"]
DEPT_ALIASES = ["DEPARTMENT", "DEPT"]
OTHER_INFO_ALIASES = ["DESIGNATION", "LOCATION", "DATE OF LEAVING", "LEAVING DATE", "GRADE",
                      "COST CENTRE", "COST CENTER", "PAN", "UAN", "BANK NAME", "BANK ACCOUNT",
                      "BANK ACCOUNT NO", "IFSC", "ARREAR DAYS", "GENDER", "DATE OF BIRTH",
                      "PF NUMBER", "ESI NUMBER", "CATEGORY", "DIVISION", "ENTITY"]

# Earning categories used in the gross bridge.
CAT_REGULAR = "Regular salary"
CAT_ARREARS = "Arrears"
CAT_ONETIME = "Bonus / one-time"
CAT_VARIABLE = "Reimbursement / variable"
CAT_UNCLASSIFIED = "Unclassified (review)"
EARNING_CATEGORIES = [CAT_REGULAR, CAT_ARREARS, CAT_ONETIME, CAT_VARIABLE, CAT_UNCLASSIFIED]

# Known earning components and their category. Any heading containing "ARREAR"
# is treated as Arrears regardless of this list.
KNOWN_EARNINGS = {
    "BASIC": CAT_REGULAR, "HRA": CAT_REGULAR, "TELEPHONE ALLOWANCE": CAT_REGULAR,
    "PERSONAL ALLOWANCE": CAT_REGULAR, "MEAL ALLOWANCE": CAT_REGULAR, "LTA REIMB": CAT_REGULAR,
    "CAR MAINT AND FUEL REIMB": CAT_REGULAR, "MEMBERSHIP ALLOWANCE": CAT_REGULAR, "NPS": CAT_REGULAR,
    "PROFESSIONAL DEVELOPMENT": CAT_REGULAR, "STIPEND": CAT_REGULAR, "SPECIAL ALLOWANCE": CAT_REGULAR,
    "CONVEYANCE ALLOWANCE": CAT_REGULAR, "MEDICAL ALLOWANCE": CAT_REGULAR,
    "CHILDREN EDUCATION ALLOWANCE": CAT_REGULAR,
    "ONCALL SUPPORT ALLOWANCE": CAT_VARIABLE, "EXPENSE REIMBURSEMENT": CAT_VARIABLE,
    "OVERTIME": CAT_VARIABLE, "SHIFT ALLOWANCE": CAT_VARIABLE,
    "GRATUITY": CAT_ONETIME, "LEAVE ENCASHMENT": CAT_ONETIME, "REFERRAL BONUS": CAT_ONETIME,
    "EXCELLENCE AWARD": CAT_ONETIME, "SDM SDE BONUS": CAT_ONETIME, "RECOGNITION BONUS": CAT_ONETIME,
    "BONUS": CAT_ONETIME, "STATUTORY BONUS": CAT_ONETIME, "INCENTIVE": CAT_ONETIME,
    "NOTICE PAY": CAT_ONETIME, "JOINING BONUS": CAT_ONETIME, "RETENTION BONUS": CAT_ONETIME,
}
# Whole words used to categorise earning columns that are NOT in the list above.
ONETIME_WORDS = {"BONUS", "AWARD", "ENCASHMENT", "GRATUITY", "INCENTIVE", "REFERRAL",
                 "EXGRATIA", "EX-GRATIA", "SEVERANCE", "COMMISSION"}
VARIABLE_WORDS = {"REIMBURSEMENT", "EXPENSE", "EXPENSES", "ONCALL", "OVERTIME", "SHIFT"}

KNOWN_DEDUCTIONS = {"PF", "PF ARREARS", "VPF", "PROF TAX", "PROFESSIONAL TAX", "PT", "INCOME TAX",
                    "TDS", "ESI", "ESIC", "LWF", "LABOUR WELFARE FUND", "OTHER DEDUCTION",
                    "MEAL ALLOWANCE DEDUCTION", "NPS DEDUCTION", "LOAN", "LOAN RECOVERY",
                    "SALARY ADVANCE", "ADVANCE RECOVERY", "NOTICE PAY RECOVERY"}

ZERO = Decimal("0")
PAISA = Decimal("0.01")
EXCEL_NOISE = 0.005  # Excel float noise allowance used only inside workbook formulas

ROLE_ID, ROLE_NAME, ROLE_INFO = "Employee ID", "Employee name", "Information (not pay)"
ROLE_EARN, ROLE_DED = "Earning component", "Deduction component"
ROLE_GROSS, ROLE_TD, ROLE_NET = "GROSS (source of truth)", "TOTAL DEDUCTIONS", "NET PAY (source of truth)"
ROLE_IGNORED = "Not used (after NET PAY / employer cost)"

GROUP_CONT, GROUP_JOIN, GROUP_LEAVE, GROUP_DUP = "Continuing", "Joiner", "Leaver", "Duplicate ID"


class ReconError(Exception):
    """An input problem that stops the reconciliation (shown to the user as-is)."""


# =============================================================================
# Small helpers
# =============================================================================
def norm(text):
    """Upper-case heading with single spaces, used for all column matching."""
    if text is None:
        return ""
    try:
        if pd.isna(text):
            return ""
    except (TypeError, ValueError):
        pass
    return re.sub(r"\s+", " ", str(text)).strip().upper()


def is_blank(value):
    if value is None:
        return True
    if isinstance(value, float) and value != value:  # NaN
        return True
    try:
        if value is pd.NaT or (not isinstance(value, (str, bool)) and pd.isna(value)):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(value, str) and value.strip() in ("", "nan", "NaN", "None")


def clean_emp_id(value):
    """Employee No as text. 1023.0 -> '1023'; leading zeros in text are kept."""
    if is_blank(value):
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    text = str(value).strip()
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".")[0]
    return text


def parse_amount(value):
    """Return (Decimal, state) where state is 'ok', 'blank' or 'invalid'.
    Blank and invalid both return 0 but are always reported by the caller."""
    if is_blank(value):
        return ZERO, "blank"
    if isinstance(value, bool):
        return ZERO, "invalid"
    if isinstance(value, int):
        return Decimal(value), "ok"
    if isinstance(value, float):
        return Decimal(repr(value)), "ok"
    if isinstance(value, Decimal):
        return value, "ok"
    text = str(value).strip()
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    text = re.sub(r"(?i)^(rs\.?|inr|₹)", "", text.strip())
    text = text.replace("₹", "").replace(",", "").replace(" ", "")
    if text in ("-", "--", "—"):
        return ZERO, "blank"
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return ZERO, "invalid"
    if not amount.is_finite():
        return ZERO, "invalid"
    return (-amount if negative else amount), "ok"


def parse_bool(value):
    if isinstance(value, bool):
        return value
    text = norm(value)
    if text in ("TRUE", "YES", "Y", "1"):
        return True
    if text in ("FALSE", "NO", "N", "0", ""):
        return False
    return None


def fmt_inr(amount):
    """Indian digit grouping for notes, e.g. 1445427 -> '14,45,427'."""
    amount = Decimal(amount)
    sign = "-" if amount < 0 else "+"
    amount = abs(amount)
    whole = int(amount)
    paise = amount - whole
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        head = ",".join(re.findall(r"\d{1,2}", head[::-1]))[::-1]
        digits = head + "," + tail
    if paise:
        digits += str(paise.quantize(PAISA))[1:]
    return sign + digits


def id_sort_key(eid):
    return (0, int(eid), eid) if eid.isdigit() else (1, 0, eid)


def to_float(value):
    return float(value) if isinstance(value, Decimal) else value


def safe_text(value):
    """Value for a text cell in Excel (never NaN)."""
    if is_blank(value):
        return ""
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.strftime("%d %b %Y")
    return value if isinstance(value, (int, float, bool)) else str(value)


def guess_month_label(filename, fallback):
    """'Salary Statement-August 2026.xls' -> 'August 2026'."""
    months = "january|february|march|april|may|june|july|august|september|october|november|december"
    found = re.search(r"(?i)(" + months + r")[\s\-_]*'?(\d{2,4})?", filename or "")
    if not found:
        return fallback
    month = found.group(1).capitalize()
    year = found.group(2)
    if year and len(year) == 2:
        year = "20" + year
    return f"{month} {year}" if year else month


# =============================================================================
# 1. Reading a greytHR export
# =============================================================================
def read_raw_table(file_bytes, filename):
    """Read the first sheet with no header assumption. Returns a DataFrame of raw cells."""
    name = (filename or "").lower()
    buffer = io.BytesIO(file_bytes)
    if name.endswith(".csv"):
        last_error = None
        for encoding in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                buffer.seek(0)
                return pd.read_csv(buffer, header=None, dtype=str, keep_default_na=False,
                                   encoding=encoding, skip_blank_lines=False)
            except UnicodeDecodeError as error:
                last_error = error
        raise ReconError(f"{filename}: could not read the CSV file ({last_error}).")
    if name.endswith(".xlsx") or name.endswith(".xlsm"):
        try:
            return pd.read_excel(buffer, header=None, dtype=object, engine="openpyxl")
        except Exception as error:
            raise ReconError(f"{filename}: could not read the .xlsx file ({error}).")
    if name.endswith(".xls"):
        head = file_bytes[:1024].lower()
        if b"<html" in head or b"<table" in head or b"<?xml" in head:
            # Some greytHR downloads are web pages saved with an .xls name.
            try:
                tables = pd.read_html(io.BytesIO(file_bytes), header=None)
                return max(tables, key=lambda t: t.shape[0] * t.shape[1]).astype(object)
            except Exception as error:
                raise ReconError(f"{filename}: this .xls is a web-page export and could not be read "
                                 f"({error}). Open it in Excel, Save As .xlsx and upload again.")
        try:
            return pd.read_excel(buffer, header=None, dtype=object, engine="xlrd")
        except ImportError:
            raise ReconError("The 'xlrd' package is needed to read .xls files. Run the launcher again "
                             "so it can install it.")
        except Exception as error:
            raise ReconError(f"{filename}: could not read the .xls file ({error}).")
    raise ReconError(f"{filename}: unsupported file type. Please upload .xls, .xlsx or .csv.")


def find_header_row(raw):
    """Index of the first row (within the first 30) that contains an Employee No heading."""
    for index in range(min(30, len(raw))):
        if any(norm(cell) in ID_ALIASES for cell in raw.iloc[index].tolist()):
            return index
    return None


def classify_earning(heading_norm):
    """(category, basis) for an earning column."""
    if "ARREAR" in heading_norm:
        return CAT_ARREARS, "Heading contains 'ARREAR'"
    if heading_norm in KNOWN_EARNINGS:
        return KNOWN_EARNINGS[heading_norm], "Known component list"
    words = set(re.split(r"[^A-Z\-]+", heading_norm))
    if words & ONETIME_WORDS:
        return CAT_ONETIME, "Keyword in heading (review)"
    if words & VARIABLE_WORDS:
        return CAT_VARIABLE, "Keyword in heading (review)"
    return CAT_UNCLASSIFIED, "Not in component list (review)"


def parse_month(file_bytes, filename, label):
    """Read and validate one month's export. Returns a dict describing the month."""
    raw = read_raw_table(file_bytes, filename)
    if raw.empty:
        raise ReconError(f"{label} ({filename}): the file is empty.")
    header_index = find_header_row(raw)
    if header_index is None:
        first_rows = [", ".join(str(v) for v in raw.iloc[i].tolist() if not is_blank(v))
                      for i in range(min(3, len(raw)))]
        raise ReconError(f"{label} ({filename}): no 'Employee No' heading found in the first 30 rows. "
                         f"First rows read: {' | '.join(first_rows)}")

    issues = []  # each: severity (FAIL / REVIEW / INFO), check, emp, column, detail, amount

    def add_issue(severity, check, detail, emp="", column="", amount=None):
        issues.append({"severity": severity, "check": check, "month": label, "emp": emp,
                       "column": column, "detail": detail, "amount": amount})

    # --- headings (made unique so no column is lost) ---
    headings, seen = [], {}
    for position, cell in enumerate(raw.iloc[header_index].tolist()):
        heading = "" if is_blank(cell) else re.sub(r"\s+", " ", str(cell)).strip()
        if not heading:
            heading = f"(blank heading col {position + 1})"
        if norm(heading) in seen:
            seen[norm(heading)] += 1
            new_heading = f"{heading} ({seen[norm(heading)]})"
            add_issue("REVIEW", "Repeated column heading",
                      f"Heading '{heading}' appears more than once; the repeat was renamed '{new_heading}'.",
                      column=new_heading)
            heading = new_heading
        else:
            seen[norm(heading)] = 1
        headings.append(heading)
    keys = [norm(h) for h in headings]

    def find(aliases):
        for alias in aliases:
            if alias in keys:
                return keys.index(alias)
        return None

    id_pos, gross_pos, net_pos = find(ID_ALIASES), find(GROSS_ALIASES), find(NET_ALIASES)
    td_pos, name_pos = find(TOTAL_DED_ALIASES), find(NAME_ALIASES)
    missing = [what for what, pos in (("Employee No", id_pos), ("GROSS", gross_pos), ("NET PAY", net_pos))
               if pos is None]
    if missing:
        raise ReconError(f"{label} ({filename}): required column(s) not found: {', '.join(missing)}. "
                         f"Headings found (row {header_index + 1}): {', '.join(headings)}")

    # --- rows: employees, grand total, blank / unexplained rows ---
    employee_rows, grand_total = [], None
    for index in range(header_index + 1, len(raw)):
        cells = raw.iloc[index].tolist()
        excel_row = index + 1
        eid = clean_emp_id(cells[id_pos])
        texts = [norm(c) for c in cells if isinstance(c, str)]
        is_total = any(re.search(r"\bTOTAL\b", t) for t in texts)
        if eid and not re.search(r"\bTOTAL\b", norm(eid)):
            employee_rows.append((excel_row, cells, eid))
            continue
        if is_total:
            if grand_total is None:
                grand_total = {"row": excel_row, "cells": cells}
                add_issue("INFO", "Rows excluded", f"Row {excel_row} is the greytHR grand-total row; "
                          "excluded from employee data and used to cross-check column totals.")
            else:
                add_issue("REVIEW", "Rows excluded", f"Row {excel_row} is an additional total row and was excluded.")
            continue
        has_amount = any(parse_amount(c)[0] != 0 for i, c in enumerate(cells) if i != id_pos
                         and parse_amount(c)[1] == "ok")
        if all(is_blank(c) for c in cells):
            continue  # completely blank template row
        if has_amount:
            add_issue("FAIL", "Row without Employee No",
                      f"Row {excel_row} has amounts but no Employee No; it was excluded. Check the export.")
        else:
            add_issue("INFO", "Rows excluded", f"Row {excel_row} has no Employee No and no amounts; excluded.")
    if not employee_rows:
        raise ReconError(f"{label} ({filename}): no employee rows found below the heading row.")

    # --- decide which columns hold amounts ---
    info_alias_set = set(JOIN_DATE_ALIASES + LEFT_ALIASES + STATUS_ALIASES + DAYS_ALIASES +
                         PAID_DAYS_ALIASES + LOP_ALIASES + DEPT_ALIASES + OTHER_INFO_ALIASES)
    numeric = {}
    for pos in range(len(headings)):
        states = [parse_amount(cells[pos])[1] for _, cells, _ in employee_rows]
        ok, invalid = states.count("ok"), states.count("invalid")
        numeric[pos] = ok > 0 and ok >= invalid

    gross_area_end = td_pos if td_pos is not None and td_pos > gross_pos else net_pos
    columns = []  # list of dicts: heading, key, pos, role, category, basis
    for pos, (heading, key) in enumerate(zip(headings, keys)):
        role, category, basis = None, "", ""
        if pos == id_pos:
            role, basis = ROLE_ID, "Heading name"
        elif pos == name_pos:
            role, basis = ROLE_NAME, "Heading name"
        elif pos == gross_pos:
            role, basis = ROLE_GROSS, "Heading name"
        elif pos == td_pos:
            role, basis = ROLE_TD, "Heading name"
        elif pos == net_pos:
            role, basis = ROLE_NET, "Heading name"
        elif key in info_alias_set:
            role, basis = ROLE_INFO, "Known information column"
        elif not numeric[pos]:
            role, basis = ROLE_INFO, "Holds text / dates, not amounts"
        elif key in KNOWN_DEDUCTIONS:
            role, category, basis = ROLE_DED, "Deduction", "Known component list"
            if pos < gross_pos or pos > net_pos:
                basis += " (located outside the deduction area - review)"
        elif key in KNOWN_EARNINGS or ("ARREAR" in key and pos < gross_pos):
            role = ROLE_EARN
            category, basis = classify_earning(key)
            if pos > gross_pos:
                basis += " (located after GROSS - review)"
        elif pos < gross_pos:
            role = ROLE_EARN
            category, basis = classify_earning(key)
            basis = "Position before GROSS; " + basis
        elif gross_pos < pos < gross_area_end or (td_pos is not None and td_pos < pos < net_pos):
            role, category, basis = ROLE_DED, "Deduction", "Position between GROSS and NET PAY (review)"
        else:
            role, basis = ROLE_IGNORED, "Position after NET PAY"
        columns.append({"heading": heading, "key": key, "pos": pos, "role": role,
                        "category": category, "basis": basis})

    earn_cols = [c for c in columns if c["role"] == ROLE_EARN]
    ded_cols = [c for c in columns if c["role"] == ROLE_DED]
    if not earn_cols:
        add_issue("FAIL", "Column classification", "No earning component columns were identified.")

    def info_pos(aliases):
        return find(aliases)

    pos_join, pos_left, pos_status = info_pos(JOIN_DATE_ALIASES), info_pos(LEFT_ALIASES), info_pos(STATUS_ALIASES)
    pos_days, pos_paid, pos_lop = info_pos(DAYS_ALIASES), info_pos(PAID_DAYS_ALIASES), info_pos(LOP_ALIASES)
    pos_dept = info_pos(DEPT_ALIASES)

    # --- build employee records with exact decimals; report blank / invalid amounts ---
    blank_log, invalid_log = {}, []
    amount_positions = [c["pos"] for c in columns if c["role"] in (ROLE_EARN, ROLE_DED, ROLE_GROSS, ROLE_TD, ROLE_NET)]
    records = []
    for excel_row, cells, eid in employee_rows:
        amounts = {}
        for pos in amount_positions:
            value, state = parse_amount(cells[pos])
            amounts[headings[pos]] = value
            if state == "blank":
                blank_log.setdefault(headings[pos], []).append(eid)
            elif state == "invalid":
                invalid_log.append((eid, headings[pos], cells[pos]))

        def number_or_none(pos):
            if pos is None:
                return None
            value, state = parse_amount(cells[pos])
            return value if state == "ok" else None

        record = {
            "id": eid, "row": excel_row,
            "name": "" if name_pos is None or is_blank(cells[name_pos]) else str(cells[name_pos]).strip(),
            "dept": "" if pos_dept is None or is_blank(cells[pos_dept]) else str(cells[pos_dept]).strip(),
            "status": "" if pos_status is None else safe_text(cells[pos_status]),
            "join": "" if pos_join is None else safe_text(cells[pos_join]),
            "left": None if pos_left is None else parse_bool(cells[pos_left]),
            "days": number_or_none(pos_days), "paid": number_or_none(pos_paid), "lop": number_or_none(pos_lop),
            "earn": {c["heading"]: amounts[c["heading"]] for c in earn_cols},
            "ded": {c["heading"]: amounts[c["heading"]] for c in ded_cols},
            "gross": amounts[headings[gross_pos]],
            "net": amounts[headings[net_pos]],
            "td_signed": amounts[headings[td_pos]] if td_pos is not None else None,
            "raw": cells,
        }
        records.append(record)

    for heading, ids in blank_log.items():
        add_issue("REVIEW", "Blank amount treated as 0",
                  f"{len(ids)} blank cell(s) in '{heading}' treated as 0. Employees: "
                  f"{', '.join(ids[:15])}{' ...' if len(ids) > 15 else ''}", column=heading)
    for eid, heading, value in invalid_log:
        add_issue("FAIL", "Invalid amount", f"Value '{value}' in '{heading}' is not a number; "
                  "it was NOT used as 0 silently - correct the export.", emp=eid, column=heading)

    # --- deduction sign convention ---
    if td_pos is None:
        convention = "DERIVED"
        convention_text = ("No TOTAL DEDUCTIONS column - total deductions taken as the sum of the "
                           "deduction components.")
        for r in records:
            r["ded_total"] = sum(r["ded"].values(), ZERO)
    else:
        negatives = sum(1 for r in records if r["td_signed"] < 0)
        positives = sum(1 for r in records if r["td_signed"] > 0)
        if negatives and not positives:
            convention = "NEGATIVE"
            convention_text = ("TOTAL DEDUCTIONS is exported as a NEGATIVE number while deduction components are "
                               "positive. Deductions are used as positive amounts: Deductions = -TOTAL DEDUCTIONS; "
                               "Net = GROSS - Deductions.")
        elif positives and not negatives:
            convention = "POSITIVE"
            convention_text = "TOTAL DEDUCTIONS is exported as a positive number. Net = GROSS - TOTAL DEDUCTIONS."
        elif not positives and not negatives:
            convention = "POSITIVE"
            convention_text = "TOTAL DEDUCTIONS is zero for every employee."
        else:
            convention = "MIXED"
            convention_text = ("TOTAL DEDUCTIONS has both positive and negative values; each row's absolute value "
                               "is used as the deduction amount. Review the export.")
            add_issue("REVIEW", "Deduction sign convention",
                      f"TOTAL DEDUCTIONS is negative for {negatives} and positive for {positives} employees.",
                      column=headings[td_pos])
        for r in records:
            signed = r["td_signed"]
            r["ded_total"] = -signed if convention == "NEGATIVE" else (abs(signed) if convention == "MIXED" else signed)

    # --- duplicate employee numbers (never overwritten) ---
    by_id = {}
    for r in records:
        by_id.setdefault(r["id"], []).append(r)
    duplicates = {eid for eid, rows in by_id.items() if len(rows) > 1}
    for eid in sorted(duplicates, key=id_sort_key):
        rows = ", ".join(str(r["row"]) for r in by_id[eid])
        add_issue("FAIL", "Duplicate Employee No",
                  f"Employee No {eid} appears {len(by_id[eid])} times (rows {rows}). These rows are kept, "
                  "excluded from employee matching and shown separately in the bridges.", emp=eid)

    # --- grand-total row cross-check ---
    grand_values = {}
    if grand_total is not None:
        for c in columns:
            if c["role"] in (ROLE_EARN, ROLE_DED, ROLE_GROSS, ROLE_TD, ROLE_NET):
                value, state = parse_amount(grand_total["cells"][c["pos"]])
                grand_values[c["heading"]] = value if state == "ok" else None

    if name_pos is None:
        add_issue("INFO", "Employee name", "No employee-name column in this export; employees are identified "
                  "by Employee No only. No names have been made up.")

    return {
        "label": label, "filename": filename, "header_row": header_index + 1,
        "headings": headings, "columns": columns, "earn_cols": [c["heading"] for c in earn_cols],
        "ded_cols": [c["heading"] for c in ded_cols],
        "gross_col": headings[gross_pos], "net_col": headings[net_pos],
        "td_col": headings[td_pos] if td_pos is not None else None,
        "name_col": headings[name_pos] if name_pos is not None else None,
        "paid_days_available": pos_paid is not None and pos_days is not None,
        "lop_available": pos_lop is not None,
        "records": records, "by_id": by_id, "duplicates": duplicates,
        "grand_total_row": grand_total["row"] if grand_total else None, "grand_values": grand_values,
        "convention": convention, "convention_text": convention_text, "issues": issues,
    }


# =============================================================================
# 2. Reconciliation logic (all in exact decimals)
# =============================================================================
def paid_ratio(record):
    if record["days"] is None or record["paid"] is None or record["days"] == 0:
        return None
    return record["paid"] / record["days"]


def split_regular_change(prev_rec, curr_rec, prev_regular, curr_regular):
    """Split the change in regular salary into (structure change, paid-days impact).
    Paid-days impact = previous full-month rate x change in paid-days ratio, where
    paid-days ratio = EMP EFFECTIVE WORKDAYS / DAYS IN MONTH. Structure change is the
    remainder, so the two always add up exactly to the change (no double counting)."""
    change = curr_regular - prev_regular
    r_prev, r_curr = paid_ratio(prev_rec), paid_ratio(curr_rec)
    if r_prev is None or r_curr is None:
        return change, ZERO, "paid days not available"
    if r_prev == r_curr:
        return change, ZERO, ""
    if r_prev == 0 or r_curr == 0:
        return ZERO, change, "zero paid days in one month - whole change treated as paid-days impact"
    full_prev = prev_regular / r_prev
    impact = (full_prev * (r_curr - r_prev)).quantize(PAISA, rounding=ROUND_HALF_UP)
    return change - impact, impact, ""


def sum_dict(d):
    return sum(d.values(), ZERO)


def reconcile(prev, curr):
    """Compare two parsed months. Returns a dict with every figure the workbook needs."""
    if norm(prev["label"]) == norm(curr["label"]):
        raise ReconError("The two month labels are the same - please give each month a different label.")
    dup_ids = prev["duplicates"] | curr["duplicates"]
    prev_ids = {r["id"] for r in prev["records"]} - dup_ids
    curr_ids = {r["id"] for r in curr["records"]} - dup_ids
    continuing = sorted(prev_ids & curr_ids, key=id_sort_key)
    joiners = sorted(curr_ids - prev_ids, key=id_sort_key)
    leavers = sorted(prev_ids - curr_ids, key=id_sort_key)
    P = {eid: prev["by_id"][eid][0] for eid in prev_ids}
    C = {eid: curr["by_id"][eid][0] for eid in curr_ids}
    prev_dup_recs = [r for r in prev["records"] if r["id"] in dup_ids]
    curr_dup_recs = [r for r in curr["records"] if r["id"] in dup_ids]

    # union of components, previous month's order first
    earn_union = list(prev["earn_cols"]) + [c for c in curr["earn_cols"] if c not in prev["earn_cols"]]
    ded_union = list(prev["ded_cols"]) + [c for c in curr["ded_cols"] if c not in prev["ded_cols"]]
    category = {}
    for month in (prev, curr):
        for c in month["columns"]:
            if c["role"] == ROLE_EARN:
                category.setdefault(c["heading"], c["category"])

    # ---- per-employee source checks (both months, every row) ----
    checks = []
    for month in (prev, curr):
        for r in month["records"]:
            earn_sum, ded_sum = sum_dict(r["earn"]), sum_dict(r["ded"])
            checks.append({
                "month": month["label"], "id": r["id"], "row": r["row"],
                "earn_sum": earn_sum, "gross": r["gross"], "earn_var": earn_sum - r["gross"],
                "ded_sum": ded_sum, "ded_total": r["ded_total"],
                "ded_var": ded_sum - r["ded_total"] if month["td_col"] else ZERO,
                "net_calc": r["gross"] - r["ded_total"], "net": r["net"],
                "net_var": r["gross"] - r["ded_total"] - r["net"],
            })
    for chk in checks:
        chk["ok"] = chk["earn_var"] == 0 and chk["ded_var"] == 0 and chk["net_var"] == 0

    # ---- continuing employees ----
    cont_rows = []
    for eid in continuing:
        p, c = P[eid], C[eid]
        cat_change = {cat: ZERO for cat in EARNING_CATEGORIES}
        prev_reg = sum((p["earn"].get(k, ZERO) for k in earn_union if category.get(k) == CAT_REGULAR), ZERO)
        curr_reg = sum((c["earn"].get(k, ZERO) for k in earn_union if category.get(k) == CAT_REGULAR), ZERO)
        structure, paid_impact, split_note = split_regular_change(p, c, prev_reg, curr_reg)
        for k in earn_union:
            if category.get(k) != CAT_REGULAR:
                cat_change[category.get(k, CAT_UNCLASSIFIED)] += c["earn"].get(k, ZERO) - p["earn"].get(k, ZERO)
        gross_change = c["gross"] - p["gross"]
        explained = structure + paid_impact + sum(cat_change[x] for x in EARNING_CATEGORIES if x != CAT_REGULAR)
        ded_change = c["ded_total"] - p["ded_total"]
        net_change = c["net"] - p["net"]

        moves = []
        for k in earn_union + ded_union:
            source = "earn" if k in earn_union else "ded"
            diff = c[source].get(k, ZERO) - p[source].get(k, ZERO)
            if diff != 0:
                moves.append((k, diff))
        moves.sort(key=lambda m: abs(m[1]), reverse=True)
        notes = [f"{k} {fmt_inr(d)}" for k, d in moves]
        if paid_ratio(p) is not None and paid_ratio(c) is not None and paid_ratio(p) != paid_ratio(c):
            notes.append(f"Paid days {p['paid']}/{p['days']} -> {c['paid']}/{c['days']}")
        if prev["lop_available"] and curr["lop_available"] and p["lop"] != c["lop"]:
            notes.append(f"LOP {p['lop']} -> {c['lop']}")
        if split_note:
            notes.append(f"({split_note})")

        cont_rows.append({
            "id": eid, "name": c["name"] or p["name"], "status": c["status"], "join": c["join"] or p["join"],
            "left_prev": p["left"], "left_curr": c["left"],
            "paid_prev": p["paid"], "paid_curr": c["paid"], "lop_prev": p["lop"], "lop_curr": c["lop"],
            "gross_prev": p["gross"], "gross_curr": c["gross"], "gross_change": gross_change,
            "structure": structure, "paid_impact": paid_impact,
            "arrears": cat_change[CAT_ARREARS], "onetime": cat_change[CAT_ONETIME],
            "variable": cat_change[CAT_VARIABLE], "unclassified": cat_change[CAT_UNCLASSIFIED],
            "gross_unexplained": gross_change - explained,
            "ded_prev": p["ded_total"], "ded_curr": c["ded_total"], "ded_change": ded_change,
            "net_prev": p["net"], "net_curr": c["net"], "net_change": net_change,
            "net_unexplained": net_change - (gross_change - ded_change),
            "components_changed": len(moves),
            "has_difference": bool(moves) or gross_change != 0 or ded_change != 0 or net_change != 0,
            "what_changed": "; ".join(notes),
        })

    # ---- component-level long tables (every employee, every non-zero line) ----
    def component_lines(kind, union):
        lines = []
        groups = [(GROUP_CONT, eid, P[eid], C[eid]) for eid in continuing]
        groups += [(GROUP_JOIN, eid, None, C[eid]) for eid in joiners]
        groups += [(GROUP_LEAVE, eid, P[eid], None) for eid in leavers]
        groups += [(GROUP_DUP, r["id"], r, None) for r in prev_dup_recs]
        groups += [(GROUP_DUP, r["id"], None, r) for r in curr_dup_recs]
        prev_set, curr_set = set(prev[kind + "_cols"]), set(curr[kind + "_cols"])
        for group, eid, p, c in groups:
            for k in union:
                vp = p[kind].get(k, ZERO) if p else ZERO
                vc = c[kind].get(k, ZERO) if c else ZERO
                if vp == 0 and vc == 0:
                    continue
                note = ""
                if k not in prev_set:
                    note = f"Column not in {prev['label']} export"
                elif k not in curr_set:
                    note = f"Column not in {curr['label']} export"
                name = (c or p)["name"]
                lines.append({"id": eid, "name": name, "group": group, "component": k,
                              "category": category.get(k, "Deduction") if kind == "earn" else "Deduction",
                              "prev": vp, "curr": vc, "diff": vc - vp, "note": note})
        return lines

    earn_lines = component_lines("earn", earn_union)
    ded_lines = component_lines("ded", ded_union)

    def comp_table(kind, union, lines):
        table = []
        for k in union:
            src_prev = sum((r[kind].get(k, ZERO) for r in prev["records"]), ZERO)
            src_curr = sum((r[kind].get(k, ZERO) for r in curr["records"]), ZERO)
            joiners_amt = sum((l["curr"] for l in lines if l["component"] == k and l["group"] == GROUP_JOIN), ZERO)
            leavers_amt = sum((l["prev"] for l in lines if l["component"] == k and l["group"] == GROUP_LEAVE), ZERO)
            cont_amt = sum((l["diff"] for l in lines if l["component"] == k and l["group"] == GROUP_CONT), ZERO)
            dup_amt = sum((l["diff"] for l in lines if l["component"] == k and l["group"] == GROUP_DUP), ZERO)
            calc = src_prev + joiners_amt - leavers_amt + cont_amt + dup_amt
            table.append({"component": k, "category": category.get(k, "Deduction") if kind == "earn" else "Deduction",
                          "prev": src_prev, "joiners": joiners_amt, "leavers": leavers_amt, "cont": cont_amt,
                          "dup": dup_amt, "calc": calc, "curr": src_curr, "diff": calc - src_curr,
                          "in_prev": k in prev[kind + "_cols"], "in_curr": k in curr[kind + "_cols"]})
        return table

    earn_table = comp_table("earn", earn_union, earn_lines)
    ded_table = comp_table("ded", ded_union, ded_lines)

    # ---- bridges ----
    def total(records, field):
        return sum((r[field] for r in records), ZERO)

    g = {"prev": total(prev["records"], "gross"), "curr": total(curr["records"], "gross"),
         "dup_prev": -total(prev_dup_recs, "gross"), "dup_curr": total(curr_dup_recs, "gross"),
         "joiners": sum((C[e]["gross"] for e in joiners), ZERO),
         "leavers": -sum((P[e]["gross"] for e in leavers), ZERO),
         "cont": sum((r["gross_change"] for r in cont_rows), ZERO)}
    g["calc"] = g["prev"] + g["dup_prev"] + g["joiners"] + g["leavers"] + g["cont"] + g["dup_curr"]
    g["diff"] = g["calc"] - g["curr"]
    g_analysis = {key: sum((r[key] for r in cont_rows), ZERO)
                  for key in ("structure", "paid_impact", "arrears", "onetime", "variable", "unclassified",
                              "gross_unexplained")}
    g["unexplained"] = g_analysis["gross_unexplained"]
    g["comp_prev_sum"] = sum((t["prev"] for t in earn_table), ZERO)
    g["comp_curr_sum"] = sum((t["curr"] for t in earn_table), ZERO)
    g["comp_table_nonzero"] = sum(1 for t in earn_table if t["diff"] != 0)

    n = {"prev": total(prev["records"], "net"), "curr": total(curr["records"], "net"),
         "dup_prev": -total(prev_dup_recs, "net"), "dup_curr": total(curr_dup_recs, "net"),
         "joiners": sum((C[e]["net"] for e in joiners), ZERO),
         "leavers": -sum((P[e]["net"] for e in leavers), ZERO),
         "cont": sum((r["net_change"] for r in cont_rows), ZERO)}
    n["calc"] = n["prev"] + n["dup_prev"] + n["joiners"] + n["leavers"] + n["cont"] + n["dup_curr"]
    n["diff"] = n["calc"] - n["curr"]
    n["cont_gross"] = g["cont"]
    n["cont_ded_by_comp"] = {t["component"]: t["cont"] for t in ded_table}
    n["cont_ded_total"] = sum((r["ded_change"] for r in cont_rows), ZERO)
    n["unexplained"] = n["cont"] - (n["cont_gross"] - sum(n["cont_ded_by_comp"].values(), ZERO))
    n["ded_prev"] = total(prev["records"], "ded_total")
    n["ded_curr"] = total(curr["records"], "ded_total")
    n["comp_table_nonzero"] = sum(1 for t in ded_table if t["diff"] != 0)

    h = {"prev": len(prev["records"]), "curr": len(curr["records"]), "joiners": len(joiners),
         "leavers": len(leavers), "dup_prev": len(prev_dup_recs), "dup_curr": len(curr_dup_recs)}
    h["calc"] = h["prev"] - h["dup_prev"] + h["joiners"] - h["leavers"] + h["dup_curr"]
    h["diff"] = h["calc"] - h["curr"]

    # ---- file-level checks ----
    issues = list(prev["issues"]) + list(curr["issues"])
    for month in (prev, curr):
        for heading, gt_value in month["grand_values"].items():
            if gt_value is None:
                continue
            kind_total = sum((r["earn"].get(heading, r["ded"].get(heading, ZERO)) for r in month["records"]), ZERO)
            if heading == month["gross_col"]:
                kind_total = total(month["records"], "gross")
            elif heading == month["net_col"]:
                kind_total = total(month["records"], "net")
            elif heading == month["td_col"]:
                kind_total = total(month["records"], "td_signed")
            if kind_total != gt_value:
                issues.append({"severity": "FAIL", "check": "Grand-total row", "month": month["label"], "emp": "",
                               "column": heading, "amount": kind_total - gt_value,
                               "detail": f"Sum of employee rows {fmt_inr(kind_total)} differs from the grand-total "
                                         f"row {fmt_inr(gt_value)}."})
    for chk in checks:
        for field, name in (("earn_var", "Earnings components vs GROSS"),
                            ("ded_var", "Deduction components vs TOTAL DEDUCTIONS"),
                            ("net_var", "GROSS - deductions vs NET PAY")):
            if chk[field] != 0:
                issues.append({"severity": "FAIL", "check": name, "month": chk["month"], "emp": chk["id"],
                               "column": "", "amount": chk[field],
                               "detail": f"Source-data exception: difference {fmt_inr(chk[field])} (source left unchanged)."})
    for month, other in ((prev, curr), (curr, prev)):
        for k in month["earn_cols"] + month["ded_cols"]:
            if k not in other["earn_cols"] + other["ded_cols"]:
                issues.append({"severity": "REVIEW", "check": "Component in one month only", "month": month["label"],
                               "emp": "", "column": k, "amount": None,
                               "detail": f"'{k}' exists only in the {month['label']} export (new, discontinued or "
                                         "renamed). Treated as 0 in the other month because the column is absent."})
        for c in month["columns"]:
            if "(review)" in c["basis"]:
                issues.append({"severity": "REVIEW", "check": "Column classification", "month": month["label"],
                               "emp": "", "column": c["heading"], "amount": None,
                               "detail": f"Classified as {c['role']}"
                                         f"{' - ' + c['category'] if c['category'] else ''} by: {c['basis']}."})
    for eid in continuing:
        if P[eid]["left"]:
            issues.append({"severity": "REVIEW", "check": "Left? flag", "month": prev["label"], "emp": eid,
                           "column": "Left?", "amount": None,
                           "detail": f"Marked Left? = True in {prev['label']} but still paid in {curr['label']}."})
    for eid in continuing:
        if P[eid]["join"] and C[eid]["join"] and P[eid]["join"] != C[eid]["join"]:
            issues.append({"severity": "REVIEW", "check": "Join Date changed", "month": curr["label"], "emp": eid,
                           "column": "Join Date", "amount": None,
                           "detail": f"Join Date is {P[eid]['join']} in {prev['label']} but {C[eid]['join']} in "
                                     f"{curr['label']} - possible re-hire under the same Employee No."})
    for eid in sorted(curr_ids, key=id_sort_key):
        if C[eid]["left"]:
            issues.append({"severity": "REVIEW", "check": "Left? flag", "month": curr["label"], "emp": eid,
                           "column": "Left?", "amount": None,
                           "detail": f"Marked Left? = True in {curr['label']} - expected to drop out next month."})
    for eid in leavers:
        if P[eid]["left"] is False:
            issues.append({"severity": "REVIEW", "check": "Left? flag", "month": prev["label"], "emp": eid,
                           "column": "Left?", "amount": None,
                           "detail": f"Not paid in {curr['label']} but was not marked Left? in {prev['label']}."})

    fail_count = sum(1 for i in issues if i["severity"] == "FAIL")
    status = {
        "headcount": h["diff"] == 0,
        "gross_bridge": g["diff"] == 0,
        "gross_unexplained": g["unexplained"] == 0,
        "gross_components": g["comp_table_nonzero"] == 0,
        "net_bridge": n["diff"] == 0,
        "net_unexplained": n["unexplained"] == 0,
        "net_components": n["comp_table_nonzero"] == 0,
        "data_checks": fail_count == 0,
    }
    status["overall"] = all(status.values())

    return {
        "prev": prev, "curr": curr, "continuing": continuing, "joiners": joiners, "leavers": leavers,
        "dup_ids": dup_ids, "prev_dup_recs": prev_dup_recs, "curr_dup_recs": curr_dup_recs,
        "P": P, "C": C, "earn_union": earn_union, "ded_union": ded_union, "category": category,
        "checks": checks, "cont_rows": cont_rows, "earn_lines": earn_lines, "ded_lines": ded_lines,
        "earn_table": earn_table, "ded_table": ded_table, "gross": g, "gross_analysis": g_analysis,
        "net": n, "headcount": h, "issues": issues, "fail_count": fail_count, "status": status,
        "differences": sorted([r for r in cont_rows if r["has_difference"]],
                              key=lambda r: (-abs(r["gross_change"]), -abs(r["net_change"]), id_sort_key(r["id"]))),
    }


# =============================================================================
# 3. Excel workbook
# =============================================================================
HEADER_FILL = PatternFill("solid", start_color="1F4E78", end_color="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF")
SECTION_FILL = PatternFill("solid", start_color="D9E1F2", end_color="D9E1F2")
SECTION_FONT = Font(bold=True, color="1F4E78")
TITLE_FONT = Font(bold=True, size=14, color="1F4E78")
BOLD = Font(bold=True)
RED_FILL = PatternFill("solid", start_color="FFC7CE", end_color="FFC7CE")
RED_FONT = Font(color="9C0006")
GREEN_FILL = PatternFill("solid", start_color="C6EFCE", end_color="C6EFCE")
GREEN_FONT = Font(color="006100")
THIN = Side(style="thin", color="D0D0D0")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
# Indian digit grouping (1,23,45,678.00). Excel number formats allow only two conditions, so
# positive numbers use the conditional format below and negative amounts get the same grouping
# (in red, with a minus sign) through conditional-formatting rules added by indian_negatives().
AMT = '[>=10000000]##\\,##\\,##\\,##0.00;[>=100000]##\\,##\\,##0.00;##,##0.00'
AMT0 = '[>=10000000]##\\,##\\,##\\,##0;[>=100000]##\\,##\\,##0;##,##0'  # whole rupees (dashboard)
INT_POS = '[>=10000000]##\\,##\\,##\\,##0;[>=100000]##\\,##\\,##0;##,##0'
INT = '#,##0;[Red]-#,##0;0'  # counts (always below one lakh, where Indian and western grouping match)
NEG_FORMATS = {  # base format -> [(rule condition, number format for negative amounts, id)]
    "AMT": [("<=-10000000", '##\\,##\\,##\\,##0.00;[Red]-##\\,##\\,##\\,##0.00', 301),
            ("<=-100000", '##\\,##\\,##0.00;[Red]-##\\,##\\,##0.00', 302),
            ("<0", '##,##0.00;[Red]-##,##0.00', 303)],
    "AMT0": [("<=-10000000", '##\\,##\\,##\\,##0;[Red]-##\\,##\\,##\\,##0', 304),
             ("<=-100000", '##\\,##\\,##0;[Red]-##\\,##\\,##0', 305),
             ("<0", '##,##0;[Red]-##,##0', 306)],
}
INDIAN_TEXT_FMT = '[>=10000000]##\\,##\\,##\\,##0;[>=100000]##\\,##\\,##0;##,##0'
PCT = '0.00%;[Red]-0.00%'
DAYS = '0.##'


def indian_negatives(ws):
    """Give negative amounts Indian grouping via conditional formatting (one rule set per block)."""
    for kind in NEG_FORMATS:
        cells = [cell for cell, k in getattr(ws, "amount_cells", {}).items() if k == kind]
        _indian_negative_rules(ws, cells, NEG_FORMATS[kind])


def _indian_negative_rules(ws, cells, formats):
    by_col = {}
    for r, c in cells:
        by_col.setdefault(c, []).append(r)
    runs = {}  # (first_row, last_row) -> [columns]
    for c, rows in by_col.items():
        rows.sort()
        start = prev = rows[0]
        for r in rows[1:] + [None]:
            if r is not None and r == prev + 1:
                prev = r
                continue
            runs.setdefault((start, prev), []).append(c)
            if r is not None:
                start = prev = r
    for (r1, r2), cols in runs.items():
        cols.sort()
        block_start = block_prev = cols[0]
        for c in cols[1:] + [None]:
            if c is not None and c == block_prev + 1:
                block_prev = c
                continue
            top_left = f"{get_column_letter(block_start)}{r1}"
            cell_range = f"{top_left}:{get_column_letter(block_prev)}{r2}"
            for condition, code, fmt_id in formats:
                ws.conditional_formatting.add(cell_range, Rule(
                    type="expression", formula=[f"AND(ISNUMBER({top_left}),{top_left}{condition})"],
                    dxf=DifferentialStyle(numFmt=NumberFormat(numFmtId=fmt_id, formatCode=code))))
            if c is not None:
                block_start = block_prev = c


def xl_inr(expr):
    """Formula text showing a number with Indian grouping, e.g. -28,04,386."""
    return f'IF(({expr})<0,"-","")&TEXT(ABS({expr}),"{INDIAN_TEXT_FMT}")'


def q(sheet):
    """Quoted sheet name for formulas."""
    return "'" + sheet.replace("'", "''") + "'"


def xl_text(text):
    """A text constant inside a formula."""
    return '"' + str(text).replace('"', '""') + '"'


def put(ws, row, col, value, fmt=None, font=None, fill=None, border=True, wrap=False):
    cell = ws.cell(row=row, column=col, value=to_float(value) if isinstance(value, Decimal) else value)
    if fmt:
        cell.number_format = fmt
        kind = "AMT" if fmt == AMT else ("AMT0" if fmt == AMT0 else None)
        if kind and value is not None and (not isinstance(value, str) or value.startswith("=")):
            if not hasattr(ws, "amount_cells"):
                ws.amount_cells = {}
            ws.amount_cells[(row, col)] = kind  # remembered so negatives get Indian grouping too
    if font:
        cell.font = font
    if fill:
        cell.fill = fill
    if border:
        cell.border = BORDER
    if wrap:
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    return cell


def header_row(ws, row, headers, start_col=1):
    for i, text in enumerate(headers):
        cell = put(ws, row, start_col + i, text, font=HEADER_FONT, fill=HEADER_FILL)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def section(ws, row, text, width=6):
    for col in range(1, width + 1):
        put(ws, row, col, text if col == 1 else None, font=SECTION_FONT, fill=SECTION_FILL)


def set_widths(ws, widths):
    for col, width in widths.items():
        ws.column_dimensions[col].width = width


def flag_nonzero(ws, cell_range):
    """Red highlight for any non-zero difference (beyond Excel float noise)."""
    first = cell_range.split(":")[0].replace("$", "")
    ws.conditional_formatting.add(cell_range, FormulaRule(
        formula=[f"AND(ISNUMBER({first}),ABS({first})>={EXCEL_NOISE})"], fill=RED_FILL, font=RED_FONT))


def flag_text(ws, cell_range, good_words, bad_words):
    first = cell_range.split(":")[0].replace("$", "")
    for word in bad_words:
        ws.conditional_formatting.add(cell_range, FormulaRule(
            formula=[f'ISNUMBER(SEARCH("{word}",{first}))'], fill=RED_FILL, font=RED_FONT))
    for word in good_words:
        ws.conditional_formatting.add(cell_range, FormulaRule(
            formula=[f'ISNUMBER(SEARCH("{word}",{first}))'], fill=GREEN_FILL, font=GREEN_FONT))


def status_formula(diff_cell, ok="RECONCILED", bad="NOT RECONCILED"):
    return f'=IF(ABS({diff_cell})<{EXCEL_NOISE},"{ok}","{bad}")'


def agree_formula(formula_cell, python_cell):
    return f'=IF(ABS({formula_cell}-{python_cell})<{EXCEL_NOISE},"Yes","NO")'


def build_dashboard(db, res, client, ref):
    """One-page management view: assertions, key figures, ratios and what moved payroll.
    Every figure is a formula linked to the detailed sheets."""
    prev, curr = res["prev"], res["curr"]
    PL, CL = prev["label"], curr["label"]
    gr, nr, sm = q("Gross Reconciliation"), q("Net Reconciliation"), q("Summary")
    dc, ae, ad = q("Data Checks"), q("All Employees"), q("All Differences")
    sr = ref["status_rows"]
    s0, ss = ref["s_first"], ref["section_start"]
    big = Font(bold=True, size=20, color="1F4E78")
    for col, width in {"A": 52, "B": 20, "C": 20, "D": 20, "E": 14}.items():
        db.column_dimensions[col].width = width
    db.sheet_view.showGridLines = False

    put(db, 1, 1, "Payroll Dashboard", font=big, border=False)
    put(db, 2, 1, (client + "  ·  " if client else "") + f"{CL} compared with {PL}",
        font=Font(bold=True, size=12), border=False)
    put(db, 3, 1, "Prepared " + datetime.datetime.now().strftime("%d %b %Y") +
        " · zero tolerance: every rupee of difference is checked · amounts in ₹", border=False)

    put(db, 5, 1, "OVERALL RESULT", font=Font(bold=True, size=13))
    cell = put(db, 5, 2, f"={sm}!B{ref['overall_row']}", font=Font(bold=True, size=13))
    cell.alignment = Alignment(horizontal="center")
    db.merge_cells("B5:E5")
    flag_text(db, "B5", ["FULLY"], ["NOT"])

    # --- key assertions ---
    row = 7
    section(db, row, "KEY ASSERTIONS", 5)
    header_row(db, row + 1, ["Assertion", "Result", "Evidence", "", ""])
    db.merge_cells(start_row=row + 1, start_column=3, end_row=row + 1, end_column=5)
    dup_rows = [ss + 7 + 1, ss + 13 + 1]
    inv_rows = [ss + 7 + 2, ss + 13 + 2]
    noid_rows = [ss + 7 + 3, ss + 13 + 3]
    ok = '"✔ Yes","✘ No"'
    assertions = [
        ("Closing gross and net pay agree with the greytHR register to the rupee",
         f'=IF(AND({sm}!B{s0 + 1}="PASS",{sm}!B{s0 + 4}="PASS"),{ok})',
         f'="Gross difference ₹"&{xl_inr(f"{gr}!B{ref["g_diff_row"]}")}&"  ·  Net difference ₹"&'
         f'{xl_inr(f"{nr}!B{ref["n_diff_row"]}")}'),
        ("Every rupee of movement is explained, by employee and by pay component",
         f'=IF(AND({sm}!B{s0 + 2}="PASS",{sm}!B{s0 + 3}="PASS",{sm}!B{s0 + 5}="PASS",{sm}!B{s0 + 6}="PASS"),{ok})',
         f'="Unexplained: gross ₹"&{xl_inr(f"{gr}!B{ref["g_unexp_row"]}")}&", net ₹"&'
         f'{xl_inr(f"{nr}!B{ref["n_unexp_row"]}")}'),
        ("Headcount movement is fully explained",
         f'=IF({sm}!B{s0}="PASS",{ok})',
         f'={sm}!B{sr[PL + " employees"]}&" + "&{sm}!B{sr["Add: joiners"]}&" joiners - "&'
         f'ABS({sm}!B{sr["Less: leavers"]})&" leavers = "&{sm}!B{sr["Actual " + CL + " employees"]}&" employees"'),
        ("Each employee's pay adds up (earnings = gross; gross - deductions = net)",
         f'=IF(COUNTIF({dc}!F{ss + 1}:F{ss + 6},"FAIL")=0,{ok})',
         f'=({sm}!B{sr[PL + " employees"]}+{sm}!B{sr["Actual " + CL + " employees"]})&" employee pay lines checked'
         f' · exceptions: "&SUM({dc}!D{ss + 1}:D{ss + 6})'),
        ("Register totals agree with greytHR's own grand-total row",
         f'=IF(AND(ISNUMBER({gr}!B7),ISNUMBER({gr}!C7)),IF(AND(ABS(N({gr}!B8))<{EXCEL_NOISE},'
         f'ABS(N({gr}!C8))<{EXCEL_NOISE},ABS(N({nr}!B9))<{EXCEL_NOISE},ABS(N({nr}!C9))<{EXCEL_NOISE}),{ok}),'
         f'"Not checked")',
         f'=IF(AND(ISNUMBER({gr}!B7),ISNUMBER({gr}!C7)),"Every pay column checked against the register total row",'
         f'"A register has no grand-total row")'),
        ("No duplicate, invalid or unidentified employee records",
         f'=IF(AND({",".join(f"{dc}!F{r}" + chr(61) + chr(34) + "PASS" + chr(34) for r in dup_rows + inv_rows + noid_rows)}),{ok})',
         f'="Duplicate IDs: "&({dc}!D{dup_rows[0]}+{dc}!D{dup_rows[1]})&"  ·  invalid amounts: "&'
         f'({dc}!D{inv_rows[0]}+{dc}!D{inv_rows[1]})&"  ·  rows without Employee No: "&'
         f'({dc}!D{noid_rows[0]}+{dc}!D{noid_rows[1]})'),
        ("Workbook figures agree with an independent recalculation",
         f'=IF({sm}!B{s0 + 8}="PASS",{ok})',
         '="Every bridge figure matches the tool\'s separate Python calculation"'),
    ]
    a_first = row + 2
    for i, (text, result, evidence) in enumerate(assertions):
        x = a_first + i
        put(db, x, 1, text, wrap=True)
        put(db, x, 2, result, font=BOLD).alignment = Alignment(horizontal="center", vertical="top")
        put(db, x, 3, evidence, wrap=True)
        put(db, x, 4, None)
        put(db, x, 5, None)
        db.merge_cells(start_row=x, start_column=3, end_row=x, end_column=5)
        db.row_dimensions[x].height = 30
    flag_text(db, f"B{a_first}:B{a_first + len(assertions) - 1}", ["Yes"], ["No", "Not"])

    # --- key figures ---
    row = a_first + len(assertions) + 1
    section(db, row, "KEY FIGURES", 5)
    header_row(db, row + 1, ["Metric", PL, CL, "Change", "Change %"])
    hc_prev, hc_curr = f"{sm}!B{sr[PL + ' employees']}", f"{sm}!B{sr['Actual ' + CL + ' employees']}"

    def ded_cells(names):
        rows = [ref["dcomp_first"] + i for i, t in enumerate(res["ded_table"]) if norm(t["component"]) in names]
        if not rows:
            return None, None
        return ("=" + "+".join(f"{nr}!C{r}" for r in rows), "=" + "+".join(f"{nr}!J{r}" for r in rows))

    def cat_total(category, col):
        c1, c2 = ref["comp_first"], ref["comp_last"]
        return f"=SUMIF({gr}!$B${c1}:$B${c2},{xl_text(category)},{gr}!${col}${c1}:${col}${c2})"

    tds = ded_cells({"INCOME TAX", "TDS"})
    pf = ded_cells({"PF", "PF ARREARS", "VPF"})
    k = row + 2
    figures = [
        ("Employees paid", "=" + hc_prev, "=" + hc_curr, "int"),
        ("Gross payroll", f"={gr}!B6", f"={gr}!C6", "amt"),
        ("Total deductions", f"={nr}!B11", f"={nr}!C11", "amt"),
        ("Net pay (take-home)", f"={nr}!B7", f"={nr}!C7", "amt"),
        ("Average gross per employee", f"=IFERROR(B{k + 1}/B{k},0)", f"=IFERROR(C{k + 1}/C{k},0)", "amt"),
        ("Average net pay per employee", f"=IFERROR(B{k + 3}/B{k},0)", f"=IFERROR(C{k + 3}/C{k},0)", "amt"),
        ("Income tax (TDS) deducted", tds[0], tds[1], "amt"),
        ("Provident fund deducted (PF, VPF, PF arrears)", pf[0], pf[1], "amt"),
        ("Bonus and one-time payments (incl. gratuity, leave encashment)", cat_total(CAT_ONETIME, "C"),
         cat_total(CAT_ONETIME, "J"), "amt"),
        ("Arrears paid", cat_total(CAT_ARREARS, "C"), cat_total(CAT_ARREARS, "J"), "amt"),
    ]
    fig_row = {}
    for i, (text, f_prev, f_curr, kind) in enumerate(figures):
        x = k + i
        fig_row[text] = x
        fmt = INT if kind == "int" else AMT0
        put(db, x, 1, text)
        if f_prev is None:
            put(db, x, 2, "Not in register")
            put(db, x, 3, "Not in register")
            put(db, x, 4, None)
            put(db, x, 5, None)
            continue
        put(db, x, 2, f_prev, fmt=fmt)
        put(db, x, 3, f_curr, fmt=fmt)
        put(db, x, 4, f"=C{x}-B{x}", fmt=fmt)
        put(db, x, 5, f'=IF(B{x}=0,"",D{x}/B{x})', fmt=PCT)

    # --- key ratios ---
    row = k + len(figures) + 1
    section(db, row, "KEY RATIOS", 5)
    header_row(db, row + 1, ["Ratio", PL, CL, "Change (% points)", ""])
    g, d, n = fig_row["Gross payroll"], fig_row["Total deductions"], fig_row["Net pay (take-home)"]

    def share(num_row, label):
        if num_row is None:
            return (label, None, None, "pct")
        return (label, f'=IFERROR(B{num_row}/B{g},"")', f'=IFERROR(C{num_row}/C{g},"")', "pct")

    joiners_cell = f"{sm}!B{sr['Add: joiners']}"
    leavers_cell = f"ABS({sm}!B{sr['Less: leavers']})"
    ratios = [
        share(d, "Deductions as % of gross"),
        share(n, "Take-home (net pay) as % of gross"),
        share(fig_row["Income tax (TDS) deducted"] if tds[0] else None, "Income tax as % of gross"),
        share(fig_row["Provident fund deducted (PF, VPF, PF arrears)"] if pf[0] else None, "Provident fund as % of gross"),
        share(fig_row["Bonus and one-time payments (incl. gratuity, leave encashment)"],
              "Bonus and one-time payments as % of gross"),
        ("Gross payroll change, month on month", None, f'=IFERROR(C{g}/B{g}-1,"")', "single"),
        ("Attrition (leavers ÷ opening employees)", None, f'=IFERROR({leavers_cell}/{hc_prev},"")', "single"),
        ("Hiring (joiners ÷ opening employees)", None, f'=IFERROR({joiners_cell}/{hc_prev},"")', "single"),
        ("Continuing employees whose pay changed", None,
         f'=IFERROR({sm}!B{sr["Continuing employees with any difference"]}/COUNTA({ae}!A2:A{ref["ae_last"]}),"")',
         "single"),
    ]
    for i, (text, f_prev, f_curr, kind) in enumerate(ratios):
        x = row + 2 + i
        put(db, x, 1, text)
        if kind == "pct" and f_prev is None:
            put(db, x, 2, "Not in register")
            put(db, x, 3, "Not in register")
            put(db, x, 4, None)
        elif kind == "pct":
            put(db, x, 2, f_prev, fmt=PCT)
            put(db, x, 3, f_curr, fmt=PCT)
            put(db, x, 4, f'=IFERROR((C{x}-B{x})*100,"")', fmt='0.00;[Red]-0.00')
        else:
            put(db, x, 2, "-").alignment = Alignment(horizontal="center")
            put(db, x, 3, f_curr, fmt=PCT)
            put(db, x, 4, None)
        put(db, x, 5, None)

    # --- what moved gross payroll ---
    row = row + 2 + len(ratios) + 1
    section(db, row, "WHAT MOVED GROSS PAYROLL", 5)
    header_row(db, row + 1, ["Driver", "Amount", "% of opening gross", "", ""])
    fr, af = ref["first"], ref["a_first"]
    drivers = [
        (f"Opening gross ({PL})", f"={gr}!B{fr}", False),
        ("New joiners", f"={gr}!B{fr + 2}", True),
        ("Leavers", f"={gr}!B{fr + 3}", True),
        ("Salary structure changes (increments / revisions)", f"={gr}!B{af}", True),
        ("Paid days / loss of pay", f"={gr}!B{af + 1}", True),
        ("Arrears", f"={gr}!B{af + 2}", True),
        ("Bonus and one-time payments", f"={gr}!B{af + 3}", True),
        ("Reimbursements and variable pay", f"={gr}!B{af + 4}", True),
        ("Unclassified pay components (review)", f"={gr}!B{af + 5}", True),
    ]
    if res["dup_ids"]:
        drivers.append(("Duplicate-ID rows", f"={gr}!B{fr + 1}+{gr}!B{fr + 5}", True))
    drivers += [("Unexplained", f"={gr}!B{ref['g_unexp_row']}", False),
                (f"Closing gross ({CL})", f"={gr}!B{ref['calc_row'] + 1}", False)]
    d_first = row + 2
    for i, (text, formula, in_chart) in enumerate(drivers):
        x = d_first + i
        bold = BOLD if text.startswith(("Opening", "Closing")) else None
        put(db, x, 1, text, font=bold)
        put(db, x, 2, formula, fmt=AMT0, font=bold)
        put(db, x, 3, f'=IFERROR(B{x}/$B${d_first},"")', fmt=PCT)
    flag_nonzero(db, f"B{d_first + len(drivers) - 2}")

    # --- top individual movements ---
    row = d_first + len(drivers) + 1
    section(db, row, "LARGEST INDIVIDUAL MOVEMENTS (continuing employees, by gross change)", 5)
    header_row(db, row + 1, ["Employee No", "Gross change", "Net pay change", "What changed", ""])
    db.merge_cells(start_row=row + 1, start_column=4, end_row=row + 1, end_column=5)
    top = min(5, len(res["differences"]))
    if not top:
        put(db, row + 2, 1, "No continuing employee's pay changed.")
    for i in range(top):
        x, src = row + 2 + i, 2 + i
        top_align = Alignment(vertical="top")
        put(db, x, 1, f"={ad}!A{src}").alignment = Alignment(vertical="top", horizontal="left")
        put(db, x, 2, f"={ad}!E{src}", fmt=AMT0).alignment = top_align
        put(db, x, 3, f"={ad}!I{src}", fmt=AMT0).alignment = top_align
        put(db, x, 4, f"={ad}!K{src}", wrap=True)
        put(db, x, 5, None)
        db.merge_cells(start_row=x, start_column=4, end_row=x, end_column=5)
        db.row_dimensions[x].height = 62
    put(db, row + 2 + max(top, 1), 1, f"All {len(res['differences'])} employees with any change are on the "
                                      "'All Differences' sheet.", border=False)

    # --- for attention ---
    row = row + 4 + max(top, 1)
    section(db, row, "FOR ATTENTION", 5)
    i_first, i_last = ref["issues_header"] + 1, ref["issues_header"] + max(ref["n_issues"], 1)
    put(db, row + 1, 1, "Items that must be resolved (FAIL)")
    put(db, row + 1, 2, f'=COUNTIF({dc}!A{i_first}:A{i_last},"FAIL")', fmt=INT)
    flag_nonzero(db, f"B{row + 1}")
    put(db, row + 2, 1, "Items to review (REVIEW)")
    put(db, row + 2, 2, f'=COUNTIF({dc}!A{i_first}:A{i_last},"REVIEW")', fmt=INT)
    notes = [i for i in res["issues"] if i["severity"] == "FAIL"] + \
            [i for i in res["issues"] if i["severity"] == "REVIEW" and i["emp"]]
    x = row + 3
    for item in notes[:8]:
        text = (f"Employee {item['emp']}: " if item["emp"] else "") + item["detail"]
        put(db, x, 1, f"{item['severity']} - {text}", border=False, wrap=True)
        db.merge_cells(start_row=x, start_column=1, end_row=x, end_column=5)
        db.row_dimensions[x].height = 30
        x += 1
    if len(notes) > 8:
        put(db, x, 1, f"... and {len(notes) - 8} more on the 'Data Checks' sheet.", border=False)
        x += 1
    put(db, x + 1, 1, "Detailed working: Summary, Gross Reconciliation and Net Reconciliation sheets. "
                      "Component-level review items (new or discontinued pay heads) are on 'Data Checks'.",
        border=False, wrap=True)
    db.merge_cells(start_row=x + 1, start_column=1, end_row=x + 1, end_column=5)
    db.row_dimensions[x + 1].height = 30

    db.page_setup.orientation = "portrait"
    db.page_setup.fitToWidth = 1
    db.page_setup.fitToHeight = 0
    db.sheet_properties.pageSetUpPr.fitToPage = True
    db.print_area = f"A1:E{x + 1}"


def build_workbook(res, client=""):
    prev, curr = res["prev"], res["curr"]
    PL, CL = prev["label"], curr["label"]
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    names = ["Dashboard", "Summary", "Gross Reconciliation", "Net Reconciliation", "Earning Components",
             "Deduction Components", "All Differences", "All Employees", "Joiners", "Leavers",
             "Data Checks", "Column Mapping", "Source Data"]
    ws = {name: wb.create_sheet(name) for name in names}
    name_note = "" if (prev["name_col"] or curr["name_col"]) else " (not in export)"

    # ---------------- Source Data ----------------
    sd = ws["Source Data"]
    union_headings = list(prev["headings"]) + [h for h in curr["headings"] if h not in prev["headings"]]
    header_row(sd, 1, ["Month", "Source row"] + union_headings)
    sd_col = {h: get_column_letter(3 + i) for i, h in enumerate(union_headings)}
    row = 2
    for month in (prev, curr):
        heading_pos = {h: i for i, h in enumerate(month["headings"])}
        amount_cols = set(month["earn_cols"] + month["ded_cols"] +
                          [month["gross_col"], month["net_col"]] + ([month["td_col"]] if month["td_col"] else []))
        for r in month["records"]:
            put(sd, row, 1, month["label"], border=False)
            put(sd, row, 2, r["row"], border=False)
            for i, h in enumerate(union_headings):
                if h not in heading_pos:
                    continue
                raw_value = r["raw"][heading_pos[h]]
                if h in amount_cols:
                    value, state = parse_amount(raw_value)
                    put(sd, row, 3 + i, value if state == "ok" else (None if state == "blank" else str(raw_value)),
                        fmt=AMT, border=False)
                else:
                    value = clean_emp_id(raw_value) if norm(h) in ID_ALIASES else safe_text(raw_value)
                    put(sd, row, 3 + i, value, border=False)
            row += 1
    sd_last = max(row - 1, 2)
    sd.freeze_panes = "C2"
    sd.auto_filter.ref = f"A1:{get_column_letter(2 + len(union_headings))}{sd_last}"
    set_widths(sd, {"A": 16, "B": 10})

    def sd_sum(heading, label):
        if heading is None or heading not in sd_col:
            return 0
        col = sd_col[heading]
        return (f"SUMIFS({q('Source Data')}!${col}$2:${col}${sd_last},"
                f"{q('Source Data')}!$A$2:$A${sd_last},{xl_text(label)})")

    def sd_count(label):
        return f"COUNTIFS({q('Source Data')}!$A$2:$A${sd_last},{xl_text(label)})"

    # ---------------- All Employees (continuing) ----------------
    ae = ws["All Employees"]
    ae_headers = ["Employee No", "Employee Name" + name_note, "Status", "Join Date",
                  f"Left? {PL}", f"Left? {CL}", f"Paid days {PL}", f"Paid days {CL}", f"LOP {PL}", f"LOP {CL}",
                  f"Gross {PL}", f"Gross {CL}", "Gross change", "Gross change %",
                  "Regular salary - structure change", "Regular salary - paid-days (LOP) impact", "Arrears",
                  "Bonus / one-time", "Reimbursement / variable", "Unclassified earnings (review)",
                  "Gross change unexplained",
                  f"Deductions {PL}", f"Deductions {CL}", "Deductions change",
                  f"Net pay {PL}", f"Net pay {CL}", "Net pay change", "Net pay change %",
                  "Net change unexplained", "Components changed", "Any difference?", "What changed"]
    header_row(ae, 1, ae_headers)
    for i, r in enumerate(res["cont_rows"]):
        x = i + 2
        values = [r["id"], r["name"], r["status"], r["join"],
                  "" if r["left_prev"] is None else r["left_prev"], "" if r["left_curr"] is None else r["left_curr"],
                  r["paid_prev"], r["paid_curr"],
                  r["lop_prev"] if prev["lop_available"] else "n/a", r["lop_curr"] if curr["lop_available"] else "n/a",
                  r["gross_prev"], r["gross_curr"], f"=L{x}-K{x}", f'=IF(K{x}=0,"",M{x}/K{x})',
                  r["structure"], r["paid_impact"], r["arrears"], r["onetime"], r["variable"], r["unclassified"],
                  f"=M{x}-SUM(O{x}:T{x})",
                  r["ded_prev"], r["ded_curr"], f"=W{x}-V{x}",
                  r["net_prev"], r["net_curr"], f"=Z{x}-Y{x}", f'=IF(Y{x}=0,"",AA{x}/Y{x})',
                  f"=AA{x}-(M{x}-X{x})", r["components_changed"],
                  f'=IF(OR(ABS(M{x})>={EXCEL_NOISE},ABS(X{x})>={EXCEL_NOISE},ABS(AA{x})>={EXCEL_NOISE},AD{x}>0),"Yes","No")',
                  r["what_changed"]]
        for col, value in enumerate(values, start=1):
            fmt = AMT if 11 <= col <= 29 else None
            if col in (14, 28):
                fmt = PCT
            if col in (7, 8, 9, 10):
                fmt = DAYS
            if col == 30:
                fmt = INT
            put(ae, x, col, value, fmt=fmt)
    ae_last = max(len(res["cont_rows"]) + 1, 2)
    ae.freeze_panes = "B2"
    ae.auto_filter.ref = f"A1:AF{ae_last}"
    flag_nonzero(ae, f"U2:U{ae_last}")
    flag_nonzero(ae, f"AC2:AC{ae_last}")
    flag_text(ae, f"AE2:AE{ae_last}", [], ["Yes"])
    set_widths(ae, {"A": 12, "B": 16, "C": 13, "D": 13, "AF": 90})
    for col in range(5, 31):
        ae.column_dimensions[get_column_letter(col)].width = 14

    def ae_sum(col):
        return f"SUM({q('All Employees')}!{col}2:{col}{ae_last})"

    # ---------------- Joiners / Leavers ----------------
    def people_sheet(sheet, ids, source, month):
        header_row(sheet, 1, ["Employee No", "Employee Name" + name_note, "Status", "Join Date", "Left?",
                              "Paid days", "Days in month", "Gross", "Deductions", "Net pay"])
        for i, eid in enumerate(ids):
            r = source[eid]
            vals = [eid, r["name"], r["status"], r["join"], "" if r["left"] is None else r["left"],
                    r["paid"], r["days"], r["gross"], r["ded_total"], r["net"]]
            for col, v in enumerate(vals, start=1):
                put(sheet, i + 2, col, v, fmt=AMT if col >= 8 else (DAYS if col in (6, 7) else None))
        first, last = 2, len(ids) + 1
        total_row = last + 1
        put(sheet, total_row, 1, f"Total ({len(ids)})", font=BOLD)
        for col in (8, 9, 10):
            letter = get_column_letter(col)
            put(sheet, total_row, col, f"=SUM({letter}{first}:{letter}{last})" if ids else 0, fmt=AMT, font=BOLD)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = f"A1:J{max(last, 2)}"
        put(sheet, total_row + 2, 1, f"Figures are from the {month} export.", border=False)
        set_widths(sheet, {"A": 13, "B": 16, "C": 14, "D": 14, "E": 8, "F": 10, "G": 12, "H": 16, "I": 16, "J": 16})
        return total_row

    joiners_total = people_sheet(ws["Joiners"], res["joiners"], res["C"], CL)
    leavers_total = people_sheet(ws["Leavers"], res["leavers"], res["P"], PL)

    # ---------------- Earning / Deduction Components ----------------
    def component_sheet(sheet, lines):
        header_row(sheet, 1, ["Employee No", "Employee Name" + name_note, "Group", "Component", "Category",
                              PL, CL, "Difference", "Difference %", "Status", "Note"])
        for i, l in enumerate(lines):
            x = i + 2
            vals = [l["id"], l["name"], l["group"], l["component"], l["category"], l["prev"], l["curr"],
                    f"=G{x}-F{x}", f'=IF(F{x}=0,"",H{x}/F{x})',
                    f'=IF(ABS(H{x})<{EXCEL_NOISE},"Match","Changed")', l["note"]]
            for col, v in enumerate(vals, start=1):
                put(sheet, x, col, v, fmt=AMT if col in (6, 7, 8) else (PCT if col == 9 else None))
        last = max(len(lines) + 1, 2)
        sheet.freeze_panes = "B2"
        sheet.auto_filter.ref = f"A1:K{last}"
        flag_text(sheet, f"J2:J{last}", ["Match"], ["Changed"])
        set_widths(sheet, {"A": 12, "B": 16, "C": 13, "D": 40, "E": 24, "F": 15, "G": 15, "H": 15, "I": 12,
                           "J": 10, "K": 34})
        return last

    ec_last = component_sheet(ws["Earning Components"], res["earn_lines"])
    dc_last = component_sheet(ws["Deduction Components"], res["ded_lines"])

    def comp_sumifs(sheet, last, value_col, component, group=None):
        s = q(sheet)
        formula = (f"SUMIFS({s}!${value_col}$2:${value_col}${last},{s}!$D$2:$D${last},{xl_text(component)}")
        if group:
            formula += f",{s}!$C$2:$C${last},{xl_text(group)}"
        return formula + ")"

    # ---------------- Data Checks ----------------
    dch = ws["Data Checks"]
    issues = res["issues"]
    checks = res["checks"]
    coverage = []
    for month in (prev, curr):
        for c in month["columns"]:
            if c["role"] in (ROLE_EARN, ROLE_DED):
                field = "earn" if c["role"] == ROLE_EARN else "ded"
                coverage.append((month["label"], c["heading"], c["role"], c["category"],
                                 sum((r[field][c["heading"]] for r in month["records"]), ZERO)))
    file_checks = []  # (check, month, items, exceptions, amount, result) values only
    for month in (prev, curr):
        mi = [i for i in issues if i["month"] == month["label"]]

        def count(check, mi=mi):
            return sum(1 for i in mi if i["check"] == check)
        file_checks.append(("Required columns present", month["label"], 3, 0, None, "PASS"))
        file_checks.append(("Duplicate Employee No", month["label"], len(month["records"]),
                            count("Duplicate Employee No"), None,
                            "FAIL" if count("Duplicate Employee No") else "PASS"))
        file_checks.append(("Invalid amounts", month["label"], len(month["records"]), count("Invalid amount"), None,
                            "FAIL" if count("Invalid amount") else "PASS"))
        file_checks.append(("Rows with amounts but no Employee No", month["label"], "", count("Row without Employee No"),
                            None, "FAIL" if count("Row without Employee No") else "PASS"))
        gt_fail = [i for i in mi if i["check"] == "Grand-total row"]
        file_checks.append(("Employee rows vs greytHR grand-total row (every amount column)", month["label"],
                            len(month["grand_values"]) if month["grand_total_row"] else "No total row",
                            len(gt_fail), sum((abs(i["amount"]) for i in gt_fail), ZERO) if gt_fail else None,
                            "FAIL" if gt_fail else ("PASS" if month["grand_total_row"] else "REVIEW")))
        file_checks.append(("Blank amounts treated as 0", month["label"], "", count("Blank amount treated as 0"),
                            None, "REVIEW" if count("Blank amount treated as 0") else "PASS"))

    put(dch, 1, 1, "Data Checks - validation of both source exports (zero tolerance)", font=TITLE_FONT, border=False)
    put(dch, 3, 1, "Overall data-check result", font=BOLD)
    section_start = 5
    header_row(dch, section_start, ["Check", "Month", "Items tested", "Exceptions", "Total of exceptions (absolute)",
                                    "Result"])
    per_emp_checks = [("Earning components = GROSS (each employee)", "E"),
                      ("Deduction components = TOTAL DEDUCTIONS (each employee)", "H"),
                      ("GROSS - deductions = NET PAY (each employee)", "K")]
    n_summary_rows = len(per_emp_checks) * 2 + len(file_checks)
    issues_header = section_start + n_summary_rows + 3
    coverage_header = issues_header + max(len(issues), 1) + 3
    table_header = coverage_header + len(coverage) + 3
    t_first, t_last = table_header + 1, table_header + len(checks)

    row = section_start + 1
    for label in (PL, CL):
        for text, col in per_emp_checks:
            mcol = f"$A${t_first}:$A${t_last}"
            vcol = f"${col}${t_first}:${col}${t_last}"
            put(dch, row, 1, text)
            put(dch, row, 2, label)
            put(dch, row, 3, f"=COUNTIFS({mcol},{xl_text(label)})", fmt=INT)
            put(dch, row, 4, f'=COUNTIFS({mcol},{xl_text(label)},{vcol},">="&{EXCEL_NOISE})'
                             f'+COUNTIFS({mcol},{xl_text(label)},{vcol},"<="&-{EXCEL_NOISE})', fmt=INT)
            put(dch, row, 5, f"=SUMPRODUCT(({mcol}={xl_text(label)})*ABS({vcol}))", fmt=AMT)
            put(dch, row, 6, f'=IF(D{row}=0,"PASS","FAIL")')
            row += 1
    for check, label, items, exc, amount, result in file_checks:
        for col, v in enumerate([check, label, items, exc, amount, result], start=1):
            put(dch, row, col, v, fmt=INT if col in (3, 4) else (AMT if col == 5 else None))
        row += 1
    summary_last = row - 1
    per_emp_fail_count = sum(1 for label in (PL, CL) for field in ("earn_var", "ded_var", "net_var")
                             if any(ch["month"] == label and ch[field] != 0 for ch in checks))
    put(dch, 3, 2, f'=IF(COUNTIF(F{section_start + 1}:F{summary_last},"FAIL")=0,"PASS","FAIL")', font=BOLD)
    flag_text(dch, f"F{section_start + 1}:F{summary_last}", ["PASS"], ["FAIL"])
    flag_text(dch, "B3", ["PASS"], ["FAIL"])

    section(dch, issues_header - 1, "Exceptions and review items (FAIL = must be resolved; REVIEW = check; "
                                    "INFO = for the record)", 7)
    header_row(dch, issues_header, ["Severity", "Check", "Month", "Employee No", "Column", "Amount", "Detail"])
    order = {"FAIL": 0, "REVIEW": 1, "INFO": 2}
    sorted_issues = sorted(issues, key=lambda i: (order[i["severity"]], i["check"], i["month"],
                                                  id_sort_key(i["emp"] or "0")))
    if not sorted_issues:
        put(dch, issues_header + 1, 1, "None")
    for i, item in enumerate(sorted_issues):
        x = issues_header + 1 + i
        for col, v in enumerate([item["severity"], item["check"], item["month"], item["emp"], item["column"],
                                 item["amount"], item["detail"]], start=1):
            put(dch, x, col, v, fmt=AMT if col == 6 else None)
    if sorted_issues:
        flag_text(dch, f"A{issues_header + 1}:A{issues_header + len(sorted_issues)}", [], ["FAIL"])

    section(dch, coverage_header - 1, "Column coverage - every earning / deduction column included in the "
                                      "component sums used above", 7)
    header_row(dch, coverage_header, ["Month", "Column", "Treatment", "Category", "Column total",
                                      "Included in component sum?"])
    for i, (label, heading, role, cat, amount) in enumerate(coverage):
        for col, v in enumerate([label, heading, role, cat, amount, "Yes"], start=1):
            put(dch, coverage_header + 1 + i, col, v, fmt=AMT if col == 5 else None)

    section(dch, table_header - 1, "Employee-level validation (every employee, both months)", 12)
    # Layout: A Month, B Emp, C Row, D Earn sum, E Earn variance, F Gross, G Ded sum, H Ded variance,
    # I Deductions (positive), J Gross - deductions, K Net variance, L Net pay, M Status
    header_row(dch, table_header, ["Month", "Employee No", "Source row", "Sum of earning components",
                                   "Earnings - GROSS", "GROSS", "Sum of deduction components",
                                   "Deduction components - deductions", "Deductions (positive)",
                                   "GROSS - deductions", "Calculated net - NET PAY", "NET PAY", "Status"])
    td_present = {PL: bool(prev["td_col"]), CL: bool(curr["td_col"])}
    for i, chk in enumerate(checks):
        x = t_first + i
        vals = [chk["month"], chk["id"], chk["row"], chk["earn_sum"], f"=D{x}-F{x}", chk["gross"], chk["ded_sum"],
                f"=G{x}-I{x}" if td_present[chk["month"]] else 0, chk["ded_total"], f"=F{x}-I{x}",
                f"=J{x}-L{x}", chk["net"],
                f'=IF(AND(ABS(E{x})<{EXCEL_NOISE},ABS(H{x})<{EXCEL_NOISE},ABS(K{x})<{EXCEL_NOISE}),"OK","EXCEPTION")']
        for col, v in enumerate(vals, start=1):
            put(dch, x, col, v, fmt=AMT if 4 <= col <= 12 else (INT if col == 3 else None))
    if checks:
        flag_nonzero(dch, f"E{t_first}:E{t_last}")
        flag_nonzero(dch, f"H{t_first}:H{t_last}")
        flag_nonzero(dch, f"K{t_first}:K{t_last}")
        flag_text(dch, f"M{t_first}:M{t_last}", ["OK"], ["EXCEPTION"])
    dch.auto_filter.ref = f"A{table_header}:M{t_last}"
    set_widths(dch, {"A": 52, "B": 30, "C": 12, "D": 16, "E": 20, "F": 16, "G": 70, "H": 18, "I": 16,
                     "J": 16, "K": 18, "L": 16, "M": 12})

    # ---------------- Gross Reconciliation ----------------
    gr = ws["Gross Reconciliation"]
    G, GA = res["gross"], res["gross_analysis"]
    put(gr, 1, 1, f"Gross reconciliation - {CL} vs {PL}", font=TITLE_FONT, border=False)
    put(gr, 2, 1, "Zero tolerance: every non-zero difference is an exception. 'Python check' is an independent "
                  "calculation; 'Agrees?' compares it with the Excel formula.", border=False)
    section(gr, 4, "1. Source totals", 5)
    header_row(gr, 5, ["Item", PL, CL])
    # component table (section 4) position is needed for row 9
    comp_header = 42
    comp_first, comp_last = comp_header + 1, comp_header + len(res["earn_table"])
    comp_total = comp_last + 1
    put(gr, 6, 1, "Sum of employee GROSS (Source Data)")
    put(gr, 6, 2, "=" + sd_sum(prev["gross_col"], PL), fmt=AMT)
    put(gr, 6, 3, "=" + sd_sum(curr["gross_col"], CL), fmt=AMT)
    put(gr, 7, 1, "GROSS per greytHR grand-total row")
    for col, month in ((2, prev), (3, curr)):
        gt = month["grand_values"].get(month["gross_col"])
        put(gr, 7, col, gt if gt is not None else "Not present", fmt=AMT)
    put(gr, 8, 1, "Difference (employee rows - grand total)")
    put(gr, 8, 2, '=IF(ISNUMBER(B7),B6-B7,"n/a")', fmt=AMT)
    put(gr, 8, 3, '=IF(ISNUMBER(C7),C6-C7,"n/a")', fmt=AMT)
    put(gr, 9, 1, "Sum of all earning components")
    put(gr, 9, 2, f"=C{comp_total}", fmt=AMT)
    put(gr, 9, 3, f"=J{comp_total}", fmt=AMT)
    put(gr, 10, 1, "Earning components - GROSS")
    put(gr, 10, 2, "=B9-B6", fmt=AMT)
    put(gr, 10, 3, "=C9-C6", fmt=AMT)
    put(gr, 11, 1, "Employees whose components do not add up to GROSS")
    put(gr, 11, 2, f"={q('Data Checks')}!D{section_start + 1}", fmt=INT)
    put(gr, 11, 3, f"={q('Data Checks')}!D{section_start + 1 + len(per_emp_checks)}", fmt=INT)
    flag_nonzero(gr, "B8:C8")
    flag_nonzero(gr, "B10:C11")

    section(gr, 13, "2. Gross bridge", 5)
    header_row(gr, 14, ["Line", "Amount (Excel formula)", "Python check", "Agrees?"])
    bridge = [
        (f"{PL} reported gross", "=B6", G["prev"]),
        (f"Less: duplicate-ID rows in {PL}", G["dup_prev"], G["dup_prev"]),
        (f"Add: joiners' gross ({len(res['joiners'])})", f"={q('Joiners')}!H{joiners_total}", G["joiners"]),
        (f"Less: leavers' gross ({len(res['leavers'])})", f"=-{q('Leavers')}!H{leavers_total}", G["leavers"]),
        (f"Add: change in gross of continuing employees ({len(res['continuing'])})", "=" + ae_sum("M"), G["cont"]),
        (f"Add: duplicate-ID rows in {CL}", G["dup_curr"], G["dup_curr"]),
    ]
    first = 15
    for i, (text, formula, py) in enumerate(bridge):
        x = first + i
        put(gr, x, 1, text)
        put(gr, x, 2, formula, fmt=AMT)
        put(gr, x, 3, py, fmt=AMT)
        put(gr, x, 4, agree_formula(f"B{x}", f"C{x}"))
    calc_row = first + len(bridge)
    put(gr, calc_row, 1, f"Calculated {CL} gross", font=BOLD)
    put(gr, calc_row, 2, f"=SUM(B{first}:B{calc_row - 1})", fmt=AMT, font=BOLD)
    put(gr, calc_row, 3, G["calc"], fmt=AMT)
    put(gr, calc_row, 4, agree_formula(f"B{calc_row}", f"C{calc_row}"))
    put(gr, calc_row + 1, 1, f"Actual {CL} gross (source)")
    put(gr, calc_row + 1, 2, "=C6", fmt=AMT)
    put(gr, calc_row + 1, 3, G["curr"], fmt=AMT)
    put(gr, calc_row + 1, 4, agree_formula(f"B{calc_row + 1}", f"C{calc_row + 1}"))
    g_diff_row = calc_row + 2
    put(gr, g_diff_row, 1, "Difference (calculated - actual)", font=BOLD)
    put(gr, g_diff_row, 2, f"=B{calc_row}-B{calc_row + 1}", fmt=AMT, font=BOLD)
    put(gr, g_diff_row, 3, G["diff"], fmt=AMT)
    put(gr, g_diff_row, 4, agree_formula(f"B{g_diff_row}", f"C{g_diff_row}"))
    g_status_row = g_diff_row + 1
    put(gr, g_status_row, 1, "Gross bridge status", font=BOLD)
    put(gr, g_status_row, 2, status_formula(f"B{g_diff_row}"), font=BOLD)
    flag_nonzero(gr, f"B{g_diff_row}:C{g_diff_row}")
    flag_text(gr, f"B{g_status_row}", ["RECONCILED"], ["NOT"])

    a_head = g_status_row + 2
    section(gr, a_head, "3. Analysis of the continuing employees' gross change", 5)
    header_row(gr, a_head + 1, ["Line", "Amount (Excel formula)", "Python check", "Agrees?"])
    analysis = [
        ("Regular salary - structure change", "O", GA["structure"]),
        ("Regular salary - paid-days (LOP / joining / leaving) impact", "P", GA["paid_impact"]),
        ("Arrears", "Q", GA["arrears"]),
        ("Bonus / one-time payments", "R", GA["onetime"]),
        ("Reimbursements / variable pay", "S", GA["variable"]),
        ("Unclassified earning components (review)", "T", GA["unclassified"]),
    ]
    a_first = a_head + 2
    for i, (text, col, py) in enumerate(analysis):
        x = a_first + i
        put(gr, x, 1, text)
        put(gr, x, 2, "=" + ae_sum(col), fmt=AMT)
        put(gr, x, 3, py, fmt=AMT)
        put(gr, x, 4, agree_formula(f"B{x}", f"C{x}"))
    a_sum = a_first + len(analysis)
    put(gr, a_sum, 1, "Explained change", font=BOLD)
    put(gr, a_sum, 2, f"=SUM(B{a_first}:B{a_sum - 1})", fmt=AMT, font=BOLD)
    put(gr, a_sum, 3, G["cont"] - G["unexplained"], fmt=AMT)
    put(gr, a_sum, 4, agree_formula(f"B{a_sum}", f"C{a_sum}"))
    put(gr, a_sum + 1, 1, "Change in gross of continuing employees (bridge line above)")
    put(gr, a_sum + 1, 2, f"=B{first + 4}", fmt=AMT)
    put(gr, a_sum + 1, 3, G["cont"], fmt=AMT)
    put(gr, a_sum + 1, 4, agree_formula(f"B{a_sum + 1}", f"C{a_sum + 1}"))
    g_unexp_row = a_sum + 2
    put(gr, g_unexp_row, 1, "Unexplained (shown, never forced to zero)", font=BOLD)
    put(gr, g_unexp_row, 2, f"=B{a_sum + 1}-B{a_sum}", fmt=AMT, font=BOLD)
    put(gr, g_unexp_row, 3, G["unexplained"], fmt=AMT)
    put(gr, g_unexp_row, 4, agree_formula(f"B{g_unexp_row}", f"C{g_unexp_row}"))
    put(gr, g_unexp_row + 1, 1, "Paid-days impact = previous full-month regular salary x change in "
                                "(EMP EFFECTIVE WORKDAYS / DAYS IN MONTH); structure change is the remainder, so "
                                "small amounts there for pro-rated employees are greytHR rounding.", border=False)
    flag_nonzero(gr, f"B{g_unexp_row}:C{g_unexp_row}")

    # section 4 - component table (starts at a fixed row so earlier formulas can refer to it)
    if g_unexp_row + 3 > comp_header - 1:
        raise RuntimeError("Layout overflow in Gross Reconciliation sheet")
    section(gr, comp_header - 1, "4. Earning components - previous total to current total", 12)
    header_row(gr, comp_header, ["Component", "Category", f"{PL} total (source)", "Add: joiners", "Less: leavers",
                                 "Continuing change", "Duplicate-ID rows", f"Calculated {CL}",
                                 "In both exports?", f"{CL} total (source)", "Difference", "Status"])
    for i, t in enumerate(res["earn_table"]):
        x = comp_first + i
        k = t["component"]
        vals = [k, t["category"],
                "=" + (sd_sum(k, PL) if t["in_prev"] else "0"),
                "=" + comp_sumifs("Earning Components", ec_last, "G", k, GROUP_JOIN),
                "=-" + comp_sumifs("Earning Components", ec_last, "F", k, GROUP_LEAVE),
                "=" + comp_sumifs("Earning Components", ec_last, "H", k, GROUP_CONT),
                "=" + comp_sumifs("Earning Components", ec_last, "H", k, GROUP_DUP),
                f"=SUM(C{x}:G{x})",
                "Yes" if t["in_prev"] and t["in_curr"] else ("Only " + (PL if t["in_prev"] else CL)),
                "=" + (sd_sum(k, CL) if t["in_curr"] else "0"),
                f"=H{x}-J{x}", status_formula(f"K{x}", "OK", "DIFFERENCE")]
        for col, v in enumerate(vals, start=1):
            put(gr, x, col, v, fmt=AMT if col in (3, 4, 5, 6, 7, 8, 10, 11) else None)
    put(gr, comp_total, 1, "Total", font=BOLD)
    for col in (3, 4, 5, 6, 7, 8, 10, 11):
        letter = get_column_letter(col)
        put(gr, comp_total, col, f"=SUM({letter}{comp_first}:{letter}{comp_last})", fmt=AMT, font=BOLD)
    put(gr, comp_total + 1, 1, "Check: total of calculated components = actual GROSS")
    put(gr, comp_total + 1, 8, f"=H{comp_total}-C6", fmt=AMT)
    put(gr, comp_total + 1, 10, f"=J{comp_total}-C6", fmt=AMT)
    flag_nonzero(gr, f"K{comp_first}:K{comp_total}")
    flag_nonzero(gr, f"H{comp_total + 1}:J{comp_total + 1}")
    flag_text(gr, f"L{comp_first}:L{comp_last}", ["OK"], ["DIFFERENCE"])
    set_widths(gr, {"A": 62, "B": 22, "C": 18, "D": 15, "E": 15, "F": 16, "G": 15, "H": 18, "I": 15, "J": 18,
                    "K": 14, "L": 12})

    # ---------------- Net Reconciliation ----------------
    nr = ws["Net Reconciliation"]
    N = res["net"]
    put(nr, 1, 1, f"Net pay reconciliation - {CL} vs {PL}", font=TITLE_FONT, border=False)
    put(nr, 2, 1, "Deduction sign convention - " + PL + ": " + prev["convention_text"], border=False)
    put(nr, 3, 1, "Deduction sign convention - " + CL + ": " + curr["convention_text"], border=False)
    section(nr, 5, "1. Source totals", 5)
    header_row(nr, 6, ["Item", PL, CL])
    dcomp_header = 60 + len(res["ded_union"])
    dcomp_first, dcomp_last = dcomp_header + 1, dcomp_header + len(res["ded_table"])
    dcomp_total = dcomp_last + 1
    put(nr, 7, 1, "Sum of employee NET PAY (Source Data)")
    put(nr, 7, 2, "=" + sd_sum(prev["net_col"], PL), fmt=AMT)
    put(nr, 7, 3, "=" + sd_sum(curr["net_col"], CL), fmt=AMT)
    put(nr, 8, 1, "NET PAY per greytHR grand-total row")
    for col, month in ((2, prev), (3, curr)):
        gt = month["grand_values"].get(month["net_col"])
        put(nr, 8, col, gt if gt is not None else "Not present", fmt=AMT)
    put(nr, 9, 1, "Difference (employee rows - grand total)")
    put(nr, 9, 2, '=IF(ISNUMBER(B8),B7-B8,"n/a")', fmt=AMT)
    put(nr, 9, 3, '=IF(ISNUMBER(C8),C7-C8,"n/a")', fmt=AMT)
    put(nr, 10, 1, "TOTAL DEDUCTIONS as exported (signed)")
    put(nr, 10, 2, "=" + sd_sum(prev["td_col"], PL) if prev["td_col"] else "No column", fmt=AMT)
    put(nr, 10, 3, "=" + sd_sum(curr["td_col"], CL) if curr["td_col"] else "No column", fmt=AMT)
    put(nr, 11, 1, "Total deductions used (positive amounts)")
    for col, month, letter in ((2, prev, "B"), (3, curr, "C")):
        if month["td_col"] is None:
            put(nr, 11, col, f"={letter}12", fmt=AMT)
        elif month["convention"] == "NEGATIVE":
            put(nr, 11, col, f"=-{letter}10", fmt=AMT)
        elif month["convention"] == "POSITIVE":
            put(nr, 11, col, f"={letter}10", fmt=AMT)
        else:
            put(nr, 11, col, N["ded_prev"] if month is prev else N["ded_curr"], fmt=AMT)
    put(nr, 12, 1, "Sum of all deduction components")
    put(nr, 12, 2, f"=C{dcomp_total}", fmt=AMT)
    put(nr, 12, 3, f"=J{dcomp_total}", fmt=AMT)
    put(nr, 13, 1, "Deduction components - total deductions")
    put(nr, 13, 2, "=B12-B11", fmt=AMT)
    put(nr, 13, 3, "=C12-C11", fmt=AMT)
    put(nr, 14, 1, "GROSS - total deductions - NET PAY")
    put(nr, 14, 2, f"={q('Gross Reconciliation')}!B6-B11-B7", fmt=AMT)
    put(nr, 14, 3, f"={q('Gross Reconciliation')}!C6-C11-C7", fmt=AMT)
    put(nr, 15, 1, "Employees whose GROSS - deductions does not equal NET PAY")
    put(nr, 15, 2, f"={q('Data Checks')}!D{section_start + 3}", fmt=INT)
    put(nr, 15, 3, f"={q('Data Checks')}!D{section_start + 3 + len(per_emp_checks)}", fmt=INT)
    flag_nonzero(nr, "B9:C9")
    flag_nonzero(nr, "B13:C15")

    section(nr, 17, "2. Net pay bridge", 5)
    header_row(nr, 18, ["Line", "Amount (Excel formula)", "Python check", "Agrees?"])
    nbridge = [
        (f"{PL} reported net pay", "=B7", N["prev"]),
        (f"Less: duplicate-ID rows in {PL}", N["dup_prev"], N["dup_prev"]),
        (f"Add: joiners' net pay ({len(res['joiners'])})", f"={q('Joiners')}!J{joiners_total}", N["joiners"]),
        (f"Less: leavers' net pay ({len(res['leavers'])})", f"=-{q('Leavers')}!J{leavers_total}", N["leavers"]),
        (f"Add: change in net pay of continuing employees ({len(res['continuing'])})", "=" + ae_sum("AA"), N["cont"]),
        (f"Add: duplicate-ID rows in {CL}", N["dup_curr"], N["dup_curr"]),
    ]
    nfirst = 19
    for i, (text, formula, py) in enumerate(nbridge):
        x = nfirst + i
        put(nr, x, 1, text)
        put(nr, x, 2, formula, fmt=AMT)
        put(nr, x, 3, py, fmt=AMT)
        put(nr, x, 4, agree_formula(f"B{x}", f"C{x}"))
    ncalc = nfirst + len(nbridge)
    put(nr, ncalc, 1, f"Calculated {CL} net pay", font=BOLD)
    put(nr, ncalc, 2, f"=SUM(B{nfirst}:B{ncalc - 1})", fmt=AMT, font=BOLD)
    put(nr, ncalc, 3, N["calc"], fmt=AMT)
    put(nr, ncalc, 4, agree_formula(f"B{ncalc}", f"C{ncalc}"))
    put(nr, ncalc + 1, 1, f"Actual {CL} net pay (source)")
    put(nr, ncalc + 1, 2, "=C7", fmt=AMT)
    put(nr, ncalc + 1, 3, N["curr"], fmt=AMT)
    put(nr, ncalc + 1, 4, agree_formula(f"B{ncalc + 1}", f"C{ncalc + 1}"))
    n_diff_row = ncalc + 2
    put(nr, n_diff_row, 1, "Difference (calculated - actual)", font=BOLD)
    put(nr, n_diff_row, 2, f"=B{ncalc}-B{ncalc + 1}", fmt=AMT, font=BOLD)
    put(nr, n_diff_row, 3, N["diff"], fmt=AMT)
    put(nr, n_diff_row, 4, agree_formula(f"B{n_diff_row}", f"C{n_diff_row}"))
    n_status_row = n_diff_row + 1
    put(nr, n_status_row, 1, "Net bridge status", font=BOLD)
    put(nr, n_status_row, 2, status_formula(f"B{n_diff_row}"), font=BOLD)
    flag_nonzero(nr, f"B{n_diff_row}:C{n_diff_row}")
    flag_text(nr, f"B{n_status_row}", ["RECONCILED"], ["NOT"])

    na = n_status_row + 2
    section(nr, na, "3. Analysis of the continuing employees' net pay change", 5)
    header_row(nr, na + 1, ["Line", "Amount (Excel formula)", "Python check", "Agrees?"])
    x = na + 2
    put(nr, x, 1, "Add: change in gross of continuing employees")
    put(nr, x, 2, f"={q('Gross Reconciliation')}!B{first + 4}", fmt=AMT)
    put(nr, x, 3, N["cont_gross"], fmt=AMT)
    put(nr, x, 4, agree_formula(f"B{x}", f"C{x}"))
    nexp_first = x
    for k in res["ded_union"]:
        x += 1
        put(nr, x, 1, f"Less: increase in {k}")
        put(nr, x, 2, "=-" + comp_sumifs("Deduction Components", dc_last, "H", k, GROUP_CONT), fmt=AMT)
        put(nr, x, 3, -N["cont_ded_by_comp"][k], fmt=AMT)
        put(nr, x, 4, agree_formula(f"B{x}", f"C{x}"))
    x += 1
    put(nr, x, 1, "Explained change", font=BOLD)
    put(nr, x, 2, f"=SUM(B{nexp_first}:B{x - 1})", fmt=AMT, font=BOLD)
    put(nr, x, 3, N["cont_gross"] - sum(N["cont_ded_by_comp"].values(), ZERO), fmt=AMT)
    put(nr, x, 4, agree_formula(f"B{x}", f"C{x}"))
    exp_row = x
    x += 1
    put(nr, x, 1, "Change in net pay of continuing employees (bridge line above)")
    put(nr, x, 2, f"=B{nfirst + 4}", fmt=AMT)
    put(nr, x, 3, N["cont"], fmt=AMT)
    put(nr, x, 4, agree_formula(f"B{x}", f"C{x}"))
    x += 1
    n_unexp_row = x
    put(nr, x, 1, "Unexplained (shown, never forced to zero)", font=BOLD)
    put(nr, x, 2, f"=B{x - 1}-B{exp_row}", fmt=AMT, font=BOLD)
    put(nr, x, 3, N["unexplained"], fmt=AMT)
    put(nr, x, 4, agree_formula(f"B{x}", f"C{x}"))
    flag_nonzero(nr, f"B{x}:C{x}")
    x += 1
    put(nr, x, 1, "Check: change in total deductions of continuing employees (All Employees sheet)")
    put(nr, x, 2, "=" + ae_sum("X"), fmt=AMT)
    put(nr, x, 3, N["cont_ded_total"], fmt=AMT)
    put(nr, x, 4, agree_formula(f"B{x}", f"C{x}"))
    if x + 2 > dcomp_header - 1:
        raise RuntimeError("Layout overflow in Net Reconciliation sheet")

    section(nr, dcomp_header - 1, "4. Deduction components (positive amounts) - previous total to current total", 12)
    header_row(nr, dcomp_header, ["Component", "Category", f"{PL} total (source)", "Add: joiners", "Less: leavers",
                                  "Continuing change", "Duplicate-ID rows", f"Calculated {CL}",
                                  "In both exports?", f"{CL} total (source)", "Difference", "Status"])
    for i, t in enumerate(res["ded_table"]):
        x = dcomp_first + i
        k = t["component"]
        vals = [k, t["category"],
                "=" + (sd_sum(k, PL) if t["in_prev"] else "0"),
                "=" + comp_sumifs("Deduction Components", dc_last, "G", k, GROUP_JOIN),
                "=-" + comp_sumifs("Deduction Components", dc_last, "F", k, GROUP_LEAVE),
                "=" + comp_sumifs("Deduction Components", dc_last, "H", k, GROUP_CONT),
                "=" + comp_sumifs("Deduction Components", dc_last, "H", k, GROUP_DUP),
                f"=SUM(C{x}:G{x})",
                "Yes" if t["in_prev"] and t["in_curr"] else ("Only " + (PL if t["in_prev"] else CL)),
                "=" + (sd_sum(k, CL) if t["in_curr"] else "0"),
                f"=H{x}-J{x}", status_formula(f"K{x}", "OK", "DIFFERENCE")]
        for col, v in enumerate(vals, start=1):
            put(nr, x, col, v, fmt=AMT if col in (3, 4, 5, 6, 7, 8, 10, 11) else None)
    put(nr, dcomp_total, 1, "Total", font=BOLD)
    for col in (3, 4, 5, 6, 7, 8, 10, 11):
        letter = get_column_letter(col)
        put(nr, dcomp_total, col, f"=SUM({letter}{dcomp_first}:{letter}{dcomp_last})" if res["ded_table"] else 0,
            fmt=AMT, font=BOLD)
    flag_nonzero(nr, f"K{dcomp_first}:K{dcomp_total}")
    flag_text(nr, f"L{dcomp_first}:L{max(dcomp_last, dcomp_first)}", ["OK"], ["DIFFERENCE"])
    set_widths(nr, {"A": 62, "B": 22, "C": 18, "D": 15, "E": 15, "F": 16, "G": 15, "H": 18, "I": 15, "J": 18,
                    "K": 14, "L": 12})

    # ---------------- All Differences ----------------
    ad = ws["All Differences"]
    header_row(ad, 1, ["Employee No", "Employee Name" + name_note, f"Gross {PL}", f"Gross {CL}", "Gross change",
                       "Deductions change", f"Net pay {PL}", f"Net pay {CL}", "Net pay change",
                       "Components changed", "What changed"])
    for i, r in enumerate(res["differences"]):
        x = i + 2
        vals = [r["id"], r["name"], r["gross_prev"], r["gross_curr"], f"=D{x}-C{x}", r["ded_change"],
                r["net_prev"], r["net_curr"], f"=H{x}-G{x}", r["components_changed"], r["what_changed"]]
        for col, v in enumerate(vals, start=1):
            put(ad, x, col, v, fmt=AMT if 3 <= col <= 9 else (INT if col == 10 else None))
    ad_last = max(len(res["differences"]) + 1, 2)
    put(ad, ad_last + 2, 1, "Zero tolerance: every continuing employee with any non-zero movement is listed "
                            "(no amount or % threshold). Sorted by size of gross change. Joiners and leavers are "
                            "on their own sheets.", border=False)
    ad.freeze_panes = "B2"
    ad.auto_filter.ref = f"A1:K{ad_last}"
    set_widths(ad, {"A": 12, "B": 16, "C": 15, "D": 15, "E": 15, "F": 15, "G": 15, "H": 15, "I": 15, "J": 12,
                    "K": 100})

    # ---------------- Column Mapping ----------------
    cm = ws["Column Mapping"]
    header_row(cm, 1, ["Column heading", f"In {PL}?", f"{PL} column no.", f"In {CL}?", f"{CL} column no.",
                       "Treatment", "Category", "How classified", f"{PL} total", f"{CL} total", "Note"])
    info_by = {}
    for month in (prev, curr):
        for c in month["columns"]:
            info_by.setdefault(c["heading"], {})[month["label"]] = c
    for i, h in enumerate(union_headings):
        x = i + 2
        cp, cc = info_by[h].get(PL), info_by[h].get(CL)
        ref = cc or cp
        role_text = ref["role"]
        if cp and cc and (cp["role"], cp["category"]) != (cc["role"], cc["category"]):
            role_text = f"{PL}: {cp['role']} / {CL}: {cc['role']}"
        note = ""
        if cp and not cc:
            note = f"Only in {PL} (discontinued or renamed?)"
        elif cc and not cp:
            note = f"Only in {CL} (new or renamed?)"

        def col_total(month, c):
            if not c or c["role"] not in (ROLE_EARN, ROLE_DED, ROLE_GROSS, ROLE_TD, ROLE_NET):
                return ""
            return "=" + sd_sum(h, month["label"])
        vals = [h, "Yes" if cp else "No", cp["pos"] + 1 if cp else "", "Yes" if cc else "No",
                cc["pos"] + 1 if cc else "", role_text, ref["category"], ref["basis"],
                col_total(prev, cp), col_total(curr, cc), note]
        for col, v in enumerate(vals, start=1):
            put(cm, x, col, v, fmt=AMT if col in (9, 10) else None)
    cm_last = len(union_headings) + 1
    put(cm, cm_last + 2, 1, f"Header row detected: {PL} row {prev['header_row']}, {CL} row {curr['header_row']}. "
                            f"Grand-total row: {PL} row {prev['grand_total_row'] or 'none'}, "
                            f"{CL} row {curr['grand_total_row'] or 'none'}.", border=False)
    put(cm, cm_last + 3, 1, "Employee names: " + ("taken from '" + (prev["name_col"] or curr["name_col"]) + "'"
                                                   if (prev["name_col"] or curr["name_col"]) else
                                                   "no name column in either export - employees are identified "
                                                   "by Employee No; no names have been made up."), border=False)
    cm.freeze_panes = "B2"
    cm.auto_filter.ref = f"A1:K{cm_last}"
    set_widths(cm, {"A": 44, "B": 9, "C": 10, "D": 9, "E": 10, "F": 30, "G": 24, "H": 52, "I": 16, "J": 16, "K": 36})

    # ---------------- Summary ----------------
    sm = ws["Summary"]
    S = res["status"]
    put(sm, 1, 1, "greytHR Payroll Reconciliation", font=TITLE_FONT, border=False)
    meta = [("Client", client or "-"), ("Previous month", f"{PL}  ({prev['filename']})"), ("Current month", f"{CL}  ({curr['filename']})"),
            ("Prepared", datetime.datetime.now().strftime("%d %b %Y %H:%M") + f"  (tool version {APP_VERSION})"),
            ("Variance rule", "Zero tolerance - every non-zero difference is reported (no amount or % threshold)"),
            ("Deduction sign convention", f"{PL}: {prev['convention']}; {CL}: {curr['convention']} "
                                          "(see Net Reconciliation)"),
            ("Employee names", "Taken from the export" if (prev["name_col"] or curr["name_col"])
             else "Not provided in the exports - Employee No is used")]
    for i, (k, v) in enumerate(meta):
        put(sm, 3 + i, 1, k, font=BOLD)
        put(sm, 3 + i, 2, v)
        sm.merge_cells(start_row=3 + i, start_column=2, end_row=3 + i, end_column=4)
    hdr = 10
    header_row(sm, hdr, ["Item", "Amount (Excel formula)", "Python check", "Agrees?"])
    gr_s, nr_s = q("Gross Reconciliation"), q("Net Reconciliation")
    lines = []  # (text, formula, python, kind) kind: section/amount/int/status
    lines.append(("HEADCOUNT", None, None, "section"))
    hc = res["headcount"]
    lines += [(f"{PL} employees", "=" + sd_count(PL), hc["prev"], "int"),
              ("Less: duplicate-ID rows (previous month)", -hc["dup_prev"], -hc["dup_prev"], "int"),
              ("Add: joiners", f"=COUNTA({q('Joiners')}!A2:A{joiners_total - 1})" if res["joiners"] else 0,
               hc["joiners"], "int"),
              ("Less: leavers", f"=-COUNTA({q('Leavers')}!A2:A{leavers_total - 1})" if res["leavers"] else 0,
               -hc["leavers"], "int"),
              ("Add: duplicate-ID rows (current month)", hc["dup_curr"], hc["dup_curr"], "int")]
    hc_first = hdr + 2
    hc_calc = hc_first + 5
    lines += [(f"Calculated {CL} employees", f"=SUM(B{hc_first}:B{hc_calc - 1})", hc["calc"], "int"),
              (f"Actual {CL} employees", "=" + sd_count(CL), hc["curr"], "int"),
              ("Headcount difference", f"=B{hc_calc}-B{hc_calc + 1}", hc["diff"], "int")]
    lines.append(("GROSS", None, None, "section"))
    lines += [(f"{PL} gross", f"={gr_s}!B{first}", G["prev"], "amt"),
              ("Joiners", f"={gr_s}!B{first + 2}", G["joiners"], "amt"),
              ("Leavers", f"={gr_s}!B{first + 3}", G["leavers"], "amt"),
              ("Continuing employees' change", f"={gr_s}!B{first + 4}", G["cont"], "amt"),
              ("Duplicate-ID rows (net)", f"={gr_s}!B{first + 1}+{gr_s}!B{first + 5}",
               G["dup_prev"] + G["dup_curr"], "amt"),
              (f"Calculated {CL} gross", f"={gr_s}!B{calc_row}", G["calc"], "amt"),
              (f"Actual {CL} gross", f"={gr_s}!B{calc_row + 1}", G["curr"], "amt"),
              ("Gross bridge difference", f"={gr_s}!B{g_diff_row}", G["diff"], "amt"),
              ("Unexplained in continuing change", f"={gr_s}!B{g_unexp_row}", G["unexplained"], "amt"),
              ("Earning components with a reconciliation difference",
               f'=COUNTIF({gr_s}!L{comp_first}:L{comp_last},"DIFFERENCE")', G["comp_table_nonzero"], "int")]
    lines.append(("NET PAY", None, None, "section"))
    lines += [(f"{PL} net pay", f"={nr_s}!B{nfirst}", N["prev"], "amt"),
              ("Joiners", f"={nr_s}!B{nfirst + 2}", N["joiners"], "amt"),
              ("Leavers", f"={nr_s}!B{nfirst + 3}", N["leavers"], "amt"),
              ("Continuing employees' change", f"={nr_s}!B{nfirst + 4}", N["cont"], "amt"),
              ("Duplicate-ID rows (net)", f"={nr_s}!B{nfirst + 1}+{nr_s}!B{nfirst + 5}",
               N["dup_prev"] + N["dup_curr"], "amt"),
              (f"Calculated {CL} net pay", f"={nr_s}!B{ncalc}", N["calc"], "amt"),
              (f"Actual {CL} net pay", f"={nr_s}!B{ncalc + 1}", N["curr"], "amt"),
              ("Net bridge difference", f"={nr_s}!B{n_diff_row}", N["diff"], "amt"),
              ("Unexplained in continuing change", f"={nr_s}!B{n_unexp_row}", N["unexplained"], "amt"),
              ("Deduction components with a reconciliation difference",
               f'=COUNTIF({nr_s}!L{dcomp_first}:L{max(dcomp_last, dcomp_first)},"DIFFERENCE")',
               N["comp_table_nonzero"], "int")]
    lines.append(("DEDUCTIONS (positive amounts)", None, None, "section"))
    lines += [(f"{PL} total deductions", f"={nr_s}!B11", N["ded_prev"], "amt"),
              (f"{CL} total deductions", f"={nr_s}!C11", N["ded_curr"], "amt"),
              ("Change", f"={nr_s}!C11-{nr_s}!B11", N["ded_curr"] - N["ded_prev"], "amt")]
    lines.append(("EXCEPTIONS (zero tolerance)", None, None, "section"))
    n_changed_lines = sum(1 for l in res["earn_lines"] + res["ded_lines"] if l["group"] == GROUP_CONT and l["diff"] != 0)
    lines += [("Continuing employees with any difference",
               f'=COUNTIF({q("All Employees")}!AE2:AE{ae_last},"Yes")', len(res["differences"]), "int"),
              ("Component lines changed (continuing employees)",
               f'=COUNTIFS({q("Earning Components")}!C2:C{ec_last},"{GROUP_CONT}",'
               f'{q("Earning Components")}!J2:J{ec_last},"Changed")'
               f'+COUNTIFS({q("Deduction Components")}!C2:C{dc_last},"{GROUP_CONT}",'
               f'{q("Deduction Components")}!J2:J{dc_last},"Changed")', n_changed_lines, "int"),
              ("Data-check items marked FAIL", f'=COUNTIF({q("Data Checks")}!F{section_start + 1}:F{summary_last},"FAIL")',
               sum(1 for c in file_checks if c[5] == "FAIL") + per_emp_fail_count, "int")]

    status_rows = {}
    x = hdr + 1
    for text, formula, py, kind in lines:
        if kind == "section":
            section(sm, x, text, 4)
            x += 1
            continue
        put(sm, x, 1, text, font=BOLD if text.startswith(("Calculated", "Actual")) or "difference" in text.lower()
            else None)
        put(sm, x, 2, formula, fmt=INT if kind == "int" else AMT)
        put(sm, x, 3, py, fmt=INT if kind == "int" else AMT)
        put(sm, x, 4, agree_formula(f"B{x}", f"C{x}"))
        status_rows[text] = x
        x += 1
    diff_rows = [status_rows[t] for t in ("Headcount difference", "Gross bridge difference", "Net bridge difference")]
    for t in diff_rows:
        flag_nonzero(sm, f"B{t}:C{t}")
    x += 1
    section(sm, x, "RECONCILIATION STATUS", 4)
    x += 1
    gross_unexp_cell = f"{gr_s}!B{g_unexp_row}"
    net_unexp_cell = f"{nr_s}!B{n_unexp_row}"
    status_lines = [
        ("Headcount", f"ABS(B{status_rows['Headcount difference']})<{EXCEL_NOISE}", S["headcount"]),
        ("Gross bridge", f"ABS({gr_s}!B{g_diff_row})<{EXCEL_NOISE}", S["gross_bridge"]),
        ("Gross - continuing change fully explained", f"ABS({gross_unexp_cell})<{EXCEL_NOISE}",
         S["gross_unexplained"]),
        ("Gross - every earning component reconciles",
         f'COUNTIF({gr_s}!L{comp_first}:L{comp_last},"DIFFERENCE")=0', S["gross_components"]),
        ("Net pay bridge", f"ABS({nr_s}!B{n_diff_row})<{EXCEL_NOISE}", S["net_bridge"]),
        ("Net pay - continuing change fully explained", f"ABS({net_unexp_cell})<{EXCEL_NOISE}", S["net_unexplained"]),
        ("Net pay - every deduction component reconciles",
         f'COUNTIF({nr_s}!L{dcomp_first}:L{max(dcomp_last, dcomp_first)},"DIFFERENCE")=0', S["net_components"]),
        ("Source data checks (Data Checks sheet)", f'{q("Data Checks")}!B3="PASS"', S["data_checks"]),
    ]
    header_row(sm, x, ["Check", "Result (Excel formula)", "Python check", "Agrees?"])
    x += 1
    s_first = x
    for text, condition, py in status_lines:
        put(sm, x, 1, text)
        put(sm, x, 2, f'=IF({condition},"PASS","FAIL")')
        put(sm, x, 3, "PASS" if py else "FAIL")
        put(sm, x, 4, f'=IF(B{x}=C{x},"Yes","NO")')
        x += 1
    put(sm, x, 1, "Formula vs Python agreement (all 'Agrees?' cells)")
    put(sm, x, 2, f'=IF(COUNTIF(D{hdr + 1}:D{x - 1},"NO")=0,"PASS","FAIL")')
    put(sm, x, 3, "PASS")
    put(sm, x, 4, f'=IF(B{x}=C{x},"Yes","NO")')
    x += 1
    overall_row = x
    put(sm, x, 1, "OVERALL", font=BOLD)
    put(sm, x, 2, f'=IF(COUNTIF(B{s_first}:B{x - 1},"FAIL")=0,"FULLY RECONCILED","NOT RECONCILED - see FAIL lines")',
        font=BOLD)
    put(sm, x, 3, "FULLY RECONCILED" if S["overall"] else "NOT RECONCILED - see FAIL lines", font=BOLD)
    put(sm, x, 4, f'=IF(B{x}=C{x},"Yes","NO")')
    flag_text(sm, f"B{s_first}:C{overall_row}", ["PASS", "FULLY"], ["FAIL", "NOT"])
    flag_text(sm, f"D{hdr + 1}:D{overall_row}", [], ["NO"])
    put(sm, overall_row + 2, 1, "Formulas recalculate automatically when the workbook is opened in Microsoft Excel. "
                                "'Python check' figures were calculated independently by the tool; every 'Agrees?' "
                                "cell must read Yes.", border=False)
    set_widths(sm, {"A": 58, "B": 34, "C": 30, "D": 10})
    sm.freeze_panes = "A11"

    # ---------------- Dashboard (management view, first sheet) ----------------
    build_dashboard(ws["Dashboard"], res, client, {
        "first": first, "calc_row": calc_row, "a_first": a_first, "g_diff_row": g_diff_row,
        "g_unexp_row": g_unexp_row, "comp_first": comp_first, "comp_last": comp_last,
        "nfirst": nfirst, "ncalc": ncalc, "n_diff_row": n_diff_row, "n_unexp_row": n_unexp_row,
        "dcomp_first": dcomp_first, "dcomp_last": dcomp_last, "s_first": s_first, "overall_row": overall_row,
        "status_rows": status_rows, "section_start": section_start, "issues_header": issues_header,
        "n_issues": len(sorted_issues), "ae_last": ae_last, "ad_last": ad_last,
    })

    for sheet in wb.worksheets:
        indian_negatives(sheet)
    for sheet in wb.worksheets:
        sheet.sheet_view.zoomScale = 90
    wb.calculation.fullCalcOnLoad = True
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def run_reconciliation(prev_bytes, prev_name, prev_label, curr_bytes, curr_name, curr_label, client=""):
    """Full pipeline used by the app and by the tests."""
    prev = parse_month(prev_bytes, prev_name, prev_label.strip() or "Previous month")
    curr = parse_month(curr_bytes, curr_name, curr_label.strip() or "Current month")
    result = reconcile(prev, curr)
    result["client"] = client
    result["workbook"] = build_workbook(result, client)
    return result


# =============================================================================
# 4. Register library - pay registers saved on this computer for re-use
# =============================================================================
DEFAULT_LIBRARY_DIR = os.environ.get(
    "PAYROLL_LIBRARY_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "Payroll Register Library"))
MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
               "october", "november", "december"]


def period_key(label):
    """'August 2026' -> '2026-08' (used to sort registers); '' if the label has no month and year."""
    text = (label or "").lower()
    for number, name in enumerate(MONTH_NAMES, start=1):
        if re.search(r"\b" + name[:3], text):
            year = re.search(r"(20\d{2}|\b\d{2}\b)", text.replace(name, " "))
            if year:
                y = year.group(1)
                return f"{('20' + y) if len(y) == 2 else y}-{number:02d}"
    return ""


def _slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "_", text or "").strip("_")[:40] or "Unassigned"


def library_index(lib_dir=None):
    """All saved registers, newest period first."""
    lib_dir = lib_dir or DEFAULT_LIBRARY_DIR
    path = os.path.join(lib_dir, "index.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as handle:
        entries = json.load(handle)
    return sorted(entries, key=lambda e: (e.get("client", "").lower(), e.get("period") or "", e.get("saved_at", "")),
                  reverse=True)


def _write_index(lib_dir, entries):
    os.makedirs(lib_dir, exist_ok=True)
    path = os.path.join(lib_dir, "index.json")
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=2, ensure_ascii=False)
    os.replace(temp, path)  # never leaves a half-written index behind


def library_save(file_bytes, filename, client, label, month=None, lib_dir=None):
    """Store an exact copy of a register. Returns (entry, newly_saved).
    The same file for the same client is stored only once."""
    lib_dir = lib_dir or DEFAULT_LIBRARY_DIR
    client = (client or "").strip() or "Unassigned"
    digest = hashlib.sha256(file_bytes).hexdigest()
    entries = library_index(lib_dir)
    for entry in entries:
        if entry["sha256"] == digest and entry["client"].lower() == client.lower():
            return entry, False
    if month is None:
        month = parse_month(file_bytes, filename, label or "Month")
    folder = os.path.join(lib_dir, _slug(client))
    os.makedirs(folder, exist_ok=True)
    stored_name = f"{period_key(label) or 'undated'}__{digest[:10]}__{os.path.basename(filename)}"
    with open(os.path.join(folder, stored_name), "wb") as handle:
        handle.write(file_bytes)
    entry = {
        "id": digest[:16] + "_" + _slug(client).lower(), "client": client, "label": label.strip(),
        "period": period_key(label), "filename": os.path.basename(filename),
        "stored_as": os.path.join(_slug(client), stored_name), "sha256": digest, "bytes": len(file_bytes),
        "saved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "employees": len(month["records"]),
        "gross": str(sum((r["gross"] for r in month["records"]), ZERO)),
        "net": str(sum((r["net"] for r in month["records"]), ZERO)),
    }
    entries.append(entry)
    _write_index(lib_dir, entries)
    return entry, True


def library_read(entry, lib_dir=None):
    """Bytes of a saved register; refuses a file that has changed since it was saved."""
    lib_dir = lib_dir or DEFAULT_LIBRARY_DIR
    path = os.path.join(lib_dir, entry["stored_as"])
    if not os.path.exists(path):
        raise ReconError(f"The saved register '{entry['filename']}' is missing from {os.path.dirname(path)}.")
    with open(path, "rb") as handle:
        data = handle.read()
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ReconError(f"The saved register '{entry['filename']}' has been changed on disk since it was saved; "
                         "upload the original again.")
    return data


def library_delete(entry_id, lib_dir=None):
    """Remove a saved register (index entry and stored copy). Returns True if something was removed."""
    lib_dir = lib_dir or DEFAULT_LIBRARY_DIR
    entries = library_index(lib_dir)
    keep = [e for e in entries if e["id"] != entry_id]
    if len(keep) == len(entries):
        return False
    for entry in entries:
        if entry["id"] == entry_id:
            path = os.path.join(lib_dir, entry["stored_as"])
            if os.path.exists(path):
                os.remove(path)
    _write_index(lib_dir, keep)
    return True


def inr_text(amount, decimals=False):
    """Plain Indian-grouped text for the screen, e.g. -28,04,386."""
    amount = Decimal(amount)
    if not decimals:
        amount = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    text = fmt_inr(amount)[1:]
    if decimals and "." not in text:
        text += ".00"
    return ("-" if amount < 0 else "") + text


def entry_caption(entry, with_client=True):
    return (f"{entry['client']} · " if with_client else "") + \
        f"{entry['label']} · {entry['filename']} · {entry['employees']} employees · gross ₹{inr_text(entry['gross'])}"


# =============================================================================
# 5. Streamlit interface
# =============================================================================
def main():
    import streamlit as st

    st.set_page_config(page_title="greytHR Payroll Reconciliation", page_icon="📊", layout="wide")
    st.title("greytHR Payroll Reconciliation")
    st.caption(f"Version {APP_VERSION} · Zero tolerance: every non-zero difference is reported. "
               "Files are processed and stored on this computer only.")

    try:
        saved = library_index()
    except Exception as error:
        saved = []
        st.warning(f"The saved-register library could not be read ({error}). Upload files as usual.")

    # --- client ---
    clients = sorted({e["client"] for e in saved}, key=str.lower)
    new_client = "➕ New client"
    if clients:
        choice = st.selectbox("Client", clients + [new_client], key="client_choice")
        client = st.text_input("New client name", key="client_new").strip() if choice == new_client else choice
    else:
        client = st.text_input("Client / company name (used to file the registers you upload)",
                               key="client_new").strip()

    sides = {}
    columns = st.columns(2)
    for side, title, column in (("prev", "Previous month", columns[0]), ("curr", "Current month", columns[1])):
        with column:
            st.subheader(f"{title} register")
            pick_up, pick_saved = st.columns([3, 1], vertical_alignment="bottom")
            upload = pick_up.file_uploader(f"Choose {title.lower()} file (.xls, .xlsx, .csv)",
                                           type=["xls", "xlsx", "csv"], key=f"{side}_file")
            mine = [e for e in saved if not client or e["client"].lower() == client.lower()]
            entry = None
            with pick_saved.popover(f"📂 Saved ({len(mine)})", use_container_width=True):
                if not mine:
                    st.write("No saved registers" + (f" for {client}" if client else "") +
                             " yet. Registers you upload are saved here when you run a reconciliation.")
                else:
                    options = ["none"] + [e["id"] for e in mine]
                    by_id = {e["id"]: e for e in mine}
                    chosen = st.radio("Use a saved register", options, key=f"{side}_saved_{_slug(client)}",
                                      format_func=lambda i: "— use the file uploaded on the left —" if i == "none"
                                      else entry_caption(by_id[i], with_client=not client))
                    entry = by_id.get(chosen)

            data = name = None
            if entry is not None:
                try:
                    data, name = library_read(entry), entry["filename"]
                    st.info(f"Using saved register: **{entry['label']}** ({entry['filename']}, "
                            f"saved {entry['saved_at']})" +
                            (". The uploaded file is ignored while a saved register is selected." if upload else ""))
                except ReconError as error:
                    st.error(str(error))
            elif upload is not None:
                data, name = upload.getvalue(), upload.name
            default_label = entry["label"] if entry else guess_month_label(name or "", title)
            label = st.text_input(f"{title} label", value=default_label, key=f"{side}_label_{default_label}")
            if data is not None:
                try:
                    month = parse_month(data, name, label or title)
                    with st.expander(f"Preview: {name} - {len(month['records'])} employees, "
                                     f"heading row {month['header_row']}"):
                        st.write(f"**Deduction convention:** {month['convention_text']}")
                        st.dataframe(pd.DataFrame([{"Column": c["heading"], "Treatment": c["role"],
                                                    "Category": c["category"], "How classified": c["basis"]}
                                                   for c in month["columns"]]),
                                     hide_index=True, use_container_width=True)
                        st.dataframe(pd.DataFrame([[safe_text(v) for v in r["raw"]] for r in month["records"][:10]],
                                                  columns=month["headings"]).astype(str),
                                     hide_index=True, use_container_width=True)
                except ReconError as error:
                    st.error(str(error))
                except Exception as error:
                    st.error(f"{name}: could not be read ({error}).")
            sides[side] = {"data": data, "name": name, "label": label, "from_upload": entry is None and data is not None}

    save_new = st.checkbox("Save newly uploaded registers to the library for next time", value=True,
                           help="An exact copy is kept in the 'Payroll Register Library' folder next to app.py. "
                                "The same file is never stored twice for a client.")

    if st.button("Run Reconciliation", type="primary", use_container_width=True):
        p, c = sides["prev"], sides["curr"]
        if p["data"] is None or c["data"] is None:
            st.error("Please choose both the previous-month and current-month registers "
                     "(upload a file or pick a saved one).")
        else:
            try:
                with st.spinner("Reconciling..."):
                    st.session_state["result"] = run_reconciliation(
                        p["data"], p["name"], p["label"], c["data"], c["name"], c["label"], client=client)
                if save_new:
                    for s in (p, c):
                        if s["from_upload"]:
                            stored, is_new = library_save(s["data"], s["name"], client, s["label"])
                            if is_new:
                                st.toast(f"Saved {stored['label']} to the library ({stored['client']}).")
                            else:
                                st.toast(f"{s['name']} is already saved as {stored['label']}.")
            except ReconError as error:
                st.session_state.pop("result", None)
                st.error(str(error))
            except Exception as error:
                st.session_state.pop("result", None)
                st.error(f"Unexpected error - nothing was produced: {error}")
                st.exception(error)

    res = st.session_state.get("result")
    if res:
        show_results(st, res)

    with st.expander(f"Manage saved registers ({len(saved)})"):
        if not saved:
            st.write("Nothing saved yet.")
        else:
            st.caption(f"Stored in: {DEFAULT_LIBRARY_DIR}")
            st.dataframe(pd.DataFrame([{
                "Client": e["client"], "Month": e["label"], "File": e["filename"], "Employees": e["employees"],
                "Gross ₹": inr_text(e["gross"]), "Net pay ₹": inr_text(e["net"]), "Saved on": e["saved_at"]}
                for e in saved]), hide_index=True, use_container_width=True)
            target = st.selectbox("Register to delete", [e["id"] for e in saved],
                                  format_func=lambda i: entry_caption(next(e for e in saved if e["id"] == i)))
            sure = st.checkbox("Yes, delete this saved copy (your original file is not affected)")
            if st.button("Delete saved register", disabled=not sure):
                library_delete(target)
                st.rerun()


def show_results(st, res):
    S, G, N, H = res["status"], res["gross"], res["net"], res["headcount"]
    PL, CL = res["prev"]["label"], res["curr"]["label"]
    if S["overall"]:
        st.success("FULLY RECONCILED - headcount, gross and net bridges agree to the rupee, every component "
                   "reconciles and all source data checks passed.")
    else:
        failed = [k.replace("_", " ") for k, v in S.items() if k != "overall" and not v]
        st.error("NOT FULLY RECONCILED - the workbook was produced but these checks failed: " + ", ".join(failed)
                 + ". See the Dashboard, Summary and Data Checks sheets.")

    def rupees(d):
        return ("-" if d < 0 else "") + "₹" + inr_text(abs(d))

    m = st.columns(5)
    m[0].metric(f"Headcount {CL}", H["curr"], f"{H['curr'] - H['prev']:+d} vs {PL}")
    m[1].metric(f"Gross {CL}", rupees(G["curr"]), rupees(G["curr"] - G["prev"]))
    m[2].metric(f"Deductions {CL}", rupees(N["ded_curr"]), rupees(N["ded_curr"] - N["ded_prev"]),
                delta_color="inverse")
    m[3].metric(f"Net pay {CL}", rupees(N["curr"]), rupees(N["curr"] - N["prev"]))
    m[4].metric("Employees with differences", len(res["differences"]))

    st.subheader("Matching")
    st.write(f"Continuing: **{len(res['continuing'])}** · Joiners: **{len(res['joiners'])}** · "
             f"Leavers: **{len(res['leavers'])}** · Duplicate IDs: **{len(res['dup_ids'])}** · "
             f"Data-check FAIL items: **{res['fail_count']}**")

    st.subheader("Checks")
    st.dataframe(pd.DataFrame([{"Check": k.replace("_", " ").capitalize(), "Result": "PASS" if v else "FAIL"}
                               for k, v in S.items() if k != "overall"]), hide_index=True)
    lines = [(PL, G["prev"], N["prev"]), ("Joiners", G["joiners"], N["joiners"]),
             ("Leavers", G["leavers"], N["leavers"]),
             ("Continuing employees' change", G["cont"], N["cont"]),
             ("Duplicate-ID rows", G["dup_prev"] + G["dup_curr"], N["dup_prev"] + N["dup_curr"]),
             (f"Calculated {CL}", G["calc"], N["calc"]), (f"Actual {CL}", G["curr"], N["curr"]),
             ("Difference", G["diff"], N["diff"])]
    st.dataframe(pd.DataFrame([{"Line": t, "Gross ₹": inr_text(g, True), "Net pay ₹": inr_text(n, True)}
                               for t, g, n in lines]),
                 hide_index=True, column_config={"Gross ₹": st.column_config.TextColumn(width="medium"),
                                                 "Net pay ₹": st.column_config.TextColumn(width="medium")})
    problems = [i for i in res["issues"] if i["severity"] in ("FAIL", "REVIEW")]
    if problems:
        with st.expander(f"Exceptions and review items ({len(problems)})"):
            st.dataframe(pd.DataFrame([{**{k: v for k, v in i.items() if k != "amount"},
                                        "amount": "" if i["amount"] is None else inr_text(i["amount"], True)}
                                       for i in problems]), hide_index=True, use_container_width=True)

    def safe(text):
        return re.sub(r'[\\/:*?"<>|]+', "-", text).strip() or "Month"
    prefix = f"{safe(res['client'])}_" if res.get("client") else ""
    st.download_button("Download reconciliation workbook (.xlsx)", data=res["workbook"],
                       file_name=f"{prefix}Payroll_Reco_{safe(CL)}_vs_{safe(PL)}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       type="primary", use_container_width=True)


if __name__ == "__main__":
    main()
