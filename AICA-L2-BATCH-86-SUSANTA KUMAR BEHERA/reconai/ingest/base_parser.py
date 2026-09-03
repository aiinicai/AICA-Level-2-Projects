import io
import os
import re
import shutil
import tempfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd


def read_file_bytes_safely(source: Union[str, Path, bytes]) -> bytes:
    """Reads file bytes safely even if the file is currently locked/open in Microsoft Excel or Adobe Acrobat."""
    if isinstance(source, bytes):
        return source
    path_str = str(source)
    try:
        with open(path_str, "rb") as f:
            return f.read()
    except (PermissionError, IOError):
        # Fallback for Windows locked files
        tmp_name = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_name = tmp.name
            shutil.copyfile(path_str, tmp_name)
            with open(tmp_name, "rb") as f:
                data = f.read()
            return data
        finally:
            if tmp_name and os.path.exists(tmp_name):
                try:
                    os.remove(tmp_name)
                except Exception:
                    pass


def get_excel_sheets_info(source: Union[str, Path, bytes]) -> List[Dict[str, Any]]:
    """Inspect an Excel workbook and return sheet names, row counts, and detected title."""
    try:
        data = read_file_bytes_safely(source)
        excel_file = pd.ExcelFile(io.BytesIO(data))
        sheets_info = []
        for s in excel_file.sheet_names:
            try:
                df_sample = excel_file.parse(s, nrows=10)
                title = ""
                for row in df_sample.values:
                    for val in row:
                        if pd.notna(val) and any(k in str(val).lower() for k in ["bank", "ca", "book", "account", "sun", "care", "hospital"]):
                            title = str(val).strip()
                            break
                    if title:
                        break
                full_len = len(excel_file.parse(s))
                sheets_info.append({"sheet_name": s, "rows": full_len, "title": title})
            except Exception:
                sheets_info.append({"sheet_name": s, "rows": 0, "title": ""})
        return sheets_info
    except Exception:
        return []


def parse_flexible_date(val: Any) -> Optional[date]:
    """Parse various date formats commonly seen in Indian & global bank statements / ledgers."""
    if val is None or pd.isna(val) or str(val).strip() == "":
        return None

    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()
    if isinstance(val, date):
        return val

    s = str(val).strip()
    date_formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%d %b %y",
        "%d-%B-%Y", "%d %B %Y",
        "%m/%d/%Y", "%m-%d-%Y"
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    try:
        from dateutil import parser
        dt = parser.parse(s, dayfirst=True)
        return dt.date()
    except Exception:
        return None


def clean_monetary_amount(val: Any) -> Optional[Decimal]:
    """Normalize string, float, or integer to positive Decimal amount."""
    if val is None or pd.isna(val) or str(val).strip() == "":
        return None

    s = str(val).strip()
    s = re.sub(r"[₹$,\s]", "", s)
    s = re.sub(r"(?i)(dr|cr|inr|usd|eur|gbp)", "", s).strip()

    if not s or s == "-":
        return None

    try:
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1]
        amt = Decimal(s)
        return abs(amt)
    except (InvalidOperation, ValueError):
        return None


def match_column_name(col_name: str, candidate_patterns: List[str]) -> bool:
    """Check if normalized column name matches any candidate regex patterns."""
    clean = re.sub(r"[^a-zA-Z0-9]", "", col_name.lower())
    for pattern in candidate_patterns:
        pat_clean = re.sub(r"[^a-zA-Z0-9]", "", pattern.lower())
        if pat_clean in clean or re.search(pattern, col_name, re.IGNORECASE):
            return True
    return False


def detect_statement_columns(columns: List[str]) -> Dict[str, Optional[str]]:
    """Auto-detect column mappings for bank statements."""
    mapping = {
        "date": None,
        "description": None,
        "debit": None,
        "credit": None,
        "amount": None,
        "type": None,
        "balance": None,
        "ref_no": None
    }

    col_list = list(columns)

    for col in col_list:
        c = str(col).strip()
        if not mapping["date"] and match_column_name(c, ["date", "txn date", "value date", "post date", "trans date"]):
            mapping["date"] = col
        elif not mapping["description"] and match_column_name(c, ["narration", "description", "particulars", "details", "remarks", "transaction remarks"]):
            mapping["description"] = col
        elif not mapping["debit"] and match_column_name(c, ["withdrawal", "debit", "dr", "dr amount", "withdrawal amt"]):
            mapping["debit"] = col
        elif not mapping["credit"] and match_column_name(c, ["deposit", "credit", "cr", "cr amount", "deposit amt"]):
            mapping["credit"] = col
        elif not mapping["amount"] and match_column_name(c, ["amount", "txn amount", "trans amount", "total"]):
            mapping["amount"] = col
        elif not mapping["type"] and match_column_name(c, ["type", "dr/cr", "cr/dr", "d/c"]):
            mapping["type"] = col
        elif not mapping["balance"] and match_column_name(c, ["balance", "closing balance", "running balance", "bal"]):
            mapping["balance"] = col
        elif not mapping["ref_no"] and match_column_name(c, ["ref no", "reference", "chq", "cheque", "utr", "txn id"]):
            mapping["ref_no"] = col

    return mapping


def detect_ledger_columns(columns: List[str]) -> Dict[str, Optional[str]]:
    """Auto-detect column mappings for client ledgers (Tally, ERP, etc.)."""
    mapping = {
        "date": None,
        "description": None,
        "account_name": None,
        "voucher_type": None,
        "voucher_no": None,
        "debit": None,
        "credit": None,
        "amount": None,
        "type": None,
        "approver": None,
        "gstin": None,
        "tds_section": None
    }

    for col in columns:
        c = str(col).strip()
        if not mapping["date"] and match_column_name(c, ["date", "voucher date", "entry date"]):
            mapping["date"] = col
        elif not mapping["description"] and match_column_name(c, ["particulars", "narration", "description", "item description"]):
            mapping["description"] = col
        elif not mapping["account_name"] and match_column_name(c, ["party", "ledger name", "account", "vendor", "customer", "head"]):
            mapping["account_name"] = col
        elif not mapping["voucher_type"] and match_column_name(c, ["vch type", "voucher type", "type"]):
            mapping["voucher_type"] = col
        elif not mapping["voucher_no"] and match_column_name(c, ["vch no", "voucher no", "voucher number", "doc no", "invoice no"]):
            mapping["voucher_no"] = col
        elif not mapping["debit"] and match_column_name(c, ["debit", "dr", "debit amount", "payment"]):
            mapping["debit"] = col
        elif not mapping["credit"] and match_column_name(c, ["credit", "cr", "credit amount", "receipt"]):
            mapping["credit"] = col
        elif not mapping["amount"] and match_column_name(c, ["amount", "net amount"]):
            mapping["amount"] = col
        elif not mapping["type"] and match_column_name(c, ["type", "dr/cr", "cr/dr"]):
            mapping["type"] = col
        elif not mapping["approver"] and match_column_name(c, ["approver", "authorized by", "approved by", "auth"]):
            mapping["approver"] = col
        elif not mapping["gstin"] and match_column_name(c, ["gstin", "gst no", "gstin/uin"]):
            mapping["gstin"] = col
        elif not mapping["tds_section"] and match_column_name(c, ["tds section", "tds", "section", "194"]):
            mapping["tds_section"] = col

    return mapping
