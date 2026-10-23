"""Local Excel loading, column mapping and validation helpers for the audit tool."""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

CONFIG_FILE = Path("audit_column_mapping.json")

DAYBOOK_DEFAULTS = {
    "date": "Posting Date", "voucher_no": "Document Number", "voucher_type": "Document Type",
    "ledger": "G/L Account Name", "ledger_code": "G/L Account", "party": "Customer/Vendor Name",
    "narration": "Text", "amount": "Amount in Local Currency", "drcr": "Debit/Credit Ind.",
    "debit": "", "credit": "",
}
TB_DEFAULTS = {
    "ledger": "G/L Account Name", "ledger_code": "G/L Account", "opening": "Balance Carried Forward",
    "debit": "Debit (Report Period)", "credit": "Credit (Report Period)", "closing": "Cumulative Balance",
}
VOUCHER_LABELS = {
    "KZ": "KZ – Vendor Payment", "DZ": "DZ – Customer Receipt", "SA": "SA – G/L Journal",
    "KR": "KR – Vendor Invoice", "RV": "RV – Customer Invoice",
}


def load_saved_mapping() -> dict[str, dict[str, str]]:
    """Read a locally saved mapping. It never sends information anywhere."""
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"daybook": DAYBOOK_DEFAULTS.copy(), "tb": TB_DEFAULTS.copy()}


def save_mapping(daybook_map: dict, tb_map: dict) -> None:
    CONFIG_FILE.write_text(json.dumps({"daybook": daybook_map, "tb": tb_map}, indent=2), encoding="utf-8")


def excel_sheets_and_headers(uploaded_file) -> tuple[list[str], dict[str, list[str]]]:
    """Find sheets and likely header rows in an Excel upload without changing the file."""
    raw = uploaded_file.getvalue()
    book = pd.ExcelFile(io.BytesIO(raw))
    headers = {}
    for sheet in book.sheet_names:
        preview = pd.read_excel(io.BytesIO(raw), sheet_name=sheet, header=None, nrows=20)
        candidates = []
        for index, row in preview.iterrows():
            words = " ".join(str(v) for v in row.dropna().tolist()).lower()
            if ("g/l account" in words or "ledger" in words or "posting date" in words or
                    ("date" in words and "amount" in words)):
                candidates.append(int(index))
        headers[sheet] = candidates or [0]
    return book.sheet_names, headers


def read_excel(uploaded_file, sheet_name: str, header_row: int) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(uploaded_file.getvalue()), sheet_name=sheet_name, header=header_row, dtype=object)


def parse_amount(value: Any) -> float:
    """Accept SAP trailing-minus amounts, commas, parentheses, blanks and normal numbers."""
    if pd.isna(value) or str(value).strip() in {"", "nan", "None", "-"}:
        return 0.0
    text = str(value).strip().replace(",", "").replace("₹", "")
    negative = text.endswith("-") or (text.startswith("(") and text.endswith(")"))
    text = text.rstrip("-").strip("()")
    try:
        number = float(text)
        return -abs(number) if negative else number
    except ValueError:
        return np.nan


def parse_sap_date(series: pd.Series) -> pd.Series:
    """Convert Excel serial dates or DD-MM-YYYY style text into dates."""
    numeric = pd.to_numeric(series, errors="coerce")
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    serial_mask = numeric.between(20000, 70000)
    result.loc[serial_mask] = pd.to_datetime(numeric.loc[serial_mask], unit="D", origin="1899-12-30", errors="coerce")
    result.loc[~serial_mask] = pd.to_datetime(series.loc[~serial_mask], dayfirst=True, errors="coerce")
    return result


def _col(frame: pd.DataFrame, mapping: dict, key: str, default="") -> pd.Series:
    name = mapping.get(key, "")
    return frame[name] if name and name in frame.columns else pd.Series(default, index=frame.index)


def normalise_daybook(raw: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Create one consistent Day Book format from SAP or separate debit/credit exports."""
    df = raw.copy()
    output = pd.DataFrame(index=df.index)
    output["Date"] = parse_sap_date(_col(df, mapping, "date"))
    output["Voucher No."] = _col(df, mapping, "voucher_no").astype(str).replace("nan", "")
    output["Voucher Type"] = _col(df, mapping, "voucher_type").astype(str).replace("nan", "")
    output["Voucher Type (Friendly)"] = output["Voucher Type"].map(VOUCHER_LABELS).fillna(output["Voucher Type"])
    output["Ledger Code"] = _col(df, mapping, "ledger_code").astype(str).replace("nan", "")
    output["Ledger"] = _col(df, mapping, "ledger").astype(str).replace("nan", "")
    output["Party"] = _col(df, mapping, "party").astype(str).replace("nan", "")
    output["Narration"] = _col(df, mapping, "narration").astype(str).replace("nan", "")
    output["Reference"] = _col(df, mapping, "reference").astype(str).replace("nan", "")
    amount_col = mapping.get("amount", "")
    if amount_col and amount_col in df.columns:
        amount = _col(df, mapping, "amount").map(parse_amount)
        indicator = _col(df, mapping, "drcr").astype(str).str.upper().str.strip()
        # SAP S = debit and H = credit. Preserve the sign if already supplied in Amount.
        output["Debit"] = np.where(indicator.isin(["S", "D", "DR", "DEBIT"]), abs(amount), 0.0)
        output["Credit"] = np.where(indicator.isin(["H", "C", "CR", "CREDIT"]), abs(amount), 0.0)
    else:
        output["Debit"] = _col(df, mapping, "debit").map(parse_amount).abs()
        output["Credit"] = _col(df, mapping, "credit").map(parse_amount).abs()
    output["Debit"] = pd.to_numeric(output["Debit"], errors="coerce").fillna(0.0)
    output["Credit"] = pd.to_numeric(output["Credit"], errors="coerce").fillna(0.0)
    output["Amount"] = output[["Debit", "Credit"]].max(axis=1)
    output["Row ID"] = np.arange(1, len(output) + 1)
    # Blank and report-total rows are not accounting entries.
    useful = (output["Voucher No."].ne("") | output["Ledger"].ne("")) & ~output["Ledger"].str.lower().eq("total")
    return output.loc[useful].reset_index(drop=True)


def normalise_tb(raw: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    df = raw.copy()
    out = pd.DataFrame(index=df.index)
    for key, title in [("ledger_code", "Ledger Code"), ("ledger", "Ledger")]:
        out[title] = _col(df, mapping, key).astype(str).replace("nan", "")
    for key, title in [("opening", "Opening"), ("debit", "Debit"), ("credit", "Credit"), ("closing", "Closing")]:
        out[title] = _col(df, mapping, key).map(parse_amount)
    out = out[(out["Ledger"].str.strip() != "") & ~out["Ledger"].str.lower().eq("total")].copy()
    out["Group"] = out["Ledger Code"].map(classify_group)
    return out.reset_index(drop=True)


def classify_group(code: str) -> str:
    try:
        first = str(code).strip()[0]
    except IndexError:
        return "Unclassified"
    return {"1": "Assets", "2": "Liabilities", "3": "Equity", "4": "Income", "5": "Expenses", "6": "Expenses"}.get(first, "Unclassified")


def validation_checks(daybook: pd.DataFrame, tb: pd.DataFrame | None, fy_start: pd.Timestamp, fy_end: pd.Timestamp) -> pd.DataFrame:
    """Return a friendly, auditable list of checks and exceptions."""
    checks = []
    debit, credit = daybook["Debit"].sum(), daybook["Credit"].sum()
    checks.append(["Day Book debit equals credit", "Pass" if np.isclose(debit, credit) else "Review", f"Debit ₹{debit:,.2f}; Credit ₹{credit:,.2f}"])
    bad_dates = daybook["Date"].isna().sum()
    checks.append(["Missing or invalid posting dates", "Pass" if not bad_dates else "Review", f"{bad_dates:,} row(s) need attention"])
    outside = ((daybook["Date"] < fy_start) | (daybook["Date"] > fy_end)).sum()
    checks.append(["Entries outside selected financial year", "Pass" if not outside else "Review", f"{outside:,} row(s) outside {fy_start:%d-%b-%Y} to {fy_end:%d-%b-%Y}"])
    duplicates = daybook.duplicated(subset=["Date", "Voucher No.", "Ledger", "Debit", "Credit"], keep=False).sum()
    checks.append(["Potential duplicate journal lines", "Pass" if not duplicates else "Review", f"{duplicates:,} duplicate-looking row(s)"])
    if tb is not None and not tb.empty:
        tb_debit, tb_credit = tb["Debit"].sum(), tb["Credit"].sum()
        checks.append(["Trial Balance movement debit equals credit", "Pass" if np.isclose(tb_debit, tb_credit) else "Review", f"Debit ₹{tb_debit:,.2f}; Credit ₹{tb_credit:,.2f}"])
        db_move = daybook.groupby("Ledger").agg(**{"DayBook Debit": ("Debit", "sum"), "DayBook Credit": ("Credit", "sum")}).reset_index()
        tb_move = tb.groupby("Ledger").agg(**{"TB Debit": ("Debit", "sum"), "TB Credit": ("Credit", "sum")}).reset_index()
        merged = db_move.merge(tb_move, on="Ledger", how="outer").fillna(0)
        mismatch = ((merged["DayBook Debit"] - merged["TB Debit"]).abs() > 1) | ((merged["DayBook Credit"] - merged["TB Credit"]).abs() > 1)
        checks.append(["Day Book movement reconciles to Trial Balance by ledger", "Pass" if not mismatch.any() else "Review", f"{mismatch.sum():,} ledger(s) differ; this may be because files cover different periods."])
    return pd.DataFrame(checks, columns=["Check", "Result", "Plain-language detail"])


def validation_exceptions(daybook: pd.DataFrame, fy_start: pd.Timestamp, fy_end: pd.Timestamp) -> pd.DataFrame:
    flagged = daybook[daybook["Date"].isna() | (daybook["Date"] < fy_start) | (daybook["Date"] > fy_end)].copy()
    flagged["Reason"] = np.where(flagged["Date"].isna(), "Invalid or missing date", "Outside selected financial year")
    duplicate = daybook[daybook.duplicated(subset=["Date", "Voucher No.", "Ledger", "Debit", "Credit"], keep=False)].copy()
    duplicate["Reason"] = "Possible duplicate journal line"
    return pd.concat([flagged, duplicate], ignore_index=True).drop_duplicates()


def combine_uploads(files, normaliser, mapping, sheet_name, header_row) -> pd.DataFrame:
    frames = []
    for upload in files:
        raw = read_excel(upload, sheet_name, header_row)
        frames.append(normaliser(raw, mapping))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
