"""Load a Tally Prime Day Book export (XML, Excel or CSV) into one normalised table.

Output: one row per ledger line with the columns in COLUMNS. `side` is "Dr" or "Cr" and
`amount` is always positive. XML is the recommended input because it carries every
ledger line of every voucher; Excel/CSV is best-effort (see _from_table).
"""
from __future__ import annotations

import csv
import io
import re
from collections import Counter
import xml.etree.ElementTree as ET

import pandas as pd

COLUMNS = ["voucher_id", "date", "vch_type", "vch_no", "ledger", "side", "amount", "narration"]

# Tally writes some control characters (e.g. &#4;) that XML parsers reject.
_BAD_ENTITY = re.compile(r"&#(?:[0-8]|1[12]|1[4-9]|2\d|3[01]);")
_BAD_CHAR = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_XML_DECL = re.compile(r"^\s*<\?xml[^>]*\?>")

_ALIASES = {
    "date": ["date"],
    "ledger": ["particulars", "ledger", "ledger name", "account"],
    "vch_type": ["vch type", "voucher type", "vchtype"],
    "vch_no": ["vch no.", "vch no", "voucher no", "voucher no.", "voucher number", "vch. no."],
    "debit": ["debit amount", "debit", "dr", "dr amount", "debit (₹)"],
    "credit": ["credit amount", "credit", "cr", "cr amount", "credit (₹)"],
    "amount": ["amount", "amount (₹)", "amt"],      # one amount column; Dr/Cr then comes from a suffix or number format
    "narration": ["narration", "remarks"],
}
_SIDE_FMT = re.compile(r"\b(Dr|Cr)\b", re.I)
_SIDE_TXT = re.compile(r"^\s*([\d,]*\.?\d+)\s*(Dr|Cr)\s*$", re.I)


def load_daybook(name: str, data: bytes) -> tuple[pd.DataFrame, dict]:
    """Return (ledger-line table, meta). Raises ValueError with a readable message."""
    ext = name.lower().rsplit(".", 1)[-1]
    if ext == "xml":
        df, meta = _from_xml(data)
    elif ext in ("xlsx", "xlsm"):
        df, meta = _from_table(_xlsx_raw(data))
    elif ext in ("csv", "txt"):
        text = _decode(data)
        raw = pd.DataFrame(list(csv.reader(io.StringIO(text))))
        df, meta = _from_table(raw)
    else:
        raise ValueError(f"Unsupported file type '.{ext}'. Upload the Day Book as XML, XLSX or CSV.")
    if df.empty:
        raise ValueError("No vouchers found in the file. Export the Day Book (not a ledger or trial balance).")
    # With hidden dates the file's own order (chronological in a Tally export) is the only time information left.
    undated = df.groupby("voucher_id")["date"].first().isna().sum()
    df = df.sort_values(["voucher_id"] if undated else ["date", "voucher_id"], kind="stable").reset_index(drop=True)
    meta["undated"] = int(undated)
    # If no voucher has more than one line, the export is condensed (one row per voucher)
    # and ledger-level rules (cash, TDS, GST, Dr = Cr) cannot be applied reliably.
    meta["ledger_level"] = bool(df.groupby("voucher_id").size().gt(1).any())
    meta["vouchers"] = int(df["voucher_id"].nunique())
    return df, meta


def _decode(raw: bytes) -> str:
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _text(el: ET.Element, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _amount(s: str) -> float:
    # Handles "-1,000.00" and forex strings like "$10 @ ₹83 = ₹830" (last number wins).
    nums = re.findall(r"-?\d+(?:\.\d+)?", s.replace(",", ""))
    return float(nums[-1]) if nums else 0.0


def _from_xml(raw: bytes) -> tuple[pd.DataFrame, dict]:
    text = _XML_DECL.sub("", _BAD_CHAR.sub("", _BAD_ENTITY.sub("", _decode(raw))))
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise ValueError(f"Could not read the XML file: {e}") from e

    rows, skipped = [], 0
    for i, v in enumerate(root.iter("VOUCHER")):
        if _text(v, "ISCANCELLED").lower() == "yes" or _text(v, "ISOPTIONAL").lower() == "yes":
            skipped += 1
            continue
        date = pd.to_datetime(_text(v, "DATE"), format="%Y%m%d", errors="coerce")
        vtype = _text(v, "VOUCHERTYPENAME") or v.get("VCHTYPE", "")
        vno = _text(v, "VOUCHERNUMBER")
        narration = _text(v, "NARRATION")
        vid = f"V{i + 1:05d}"

        entries = v.findall("ALLLEDGERENTRIES.LIST") + v.findall("LEDGERENTRIES.LIST")
        for inv in ("ALLINVENTORYENTRIES.LIST", "INVENTORYENTRIES.LIST"):
            for item in v.findall(inv):
                entries += item.findall("ACCOUNTINGALLOCATIONS.LIST")
        for e in entries:
            amt = _amount(_text(e, "AMOUNT"))
            if amt == 0:
                continue
            # Tally convention: negative = debit, positive = credit.
            rows.append([vid, date, vtype, vno, _text(e, "LEDGERNAME"),
                         "Dr" if amt < 0 else "Cr", abs(amt), narration])
    return pd.DataFrame(rows, columns=COLUMNS), {"skipped": skipped, "format": "xml"}


def _norm(cell) -> str:
    return "" if pd.isna(cell) else re.sub(r"\s+", " ", str(cell)).strip().lower()


def _amount_side(v) -> tuple[float, str | None]:
    """(amount, 'Dr'/'Cr' if the cell says so). Handles numbers, '1,234.50' and '1234.50 Dr'."""
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return 0.0, None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return abs(float(v)), None
    s = str(v).strip()
    m = _SIDE_TXT.match(s)
    if m:
        return float(m.group(1).replace(",", "")), m.group(2).capitalize()
    try:
        return abs(float(s.replace(",", "") or 0)), None
    except ValueError:
        return 0.0, None


def _num(cell) -> float:
    return _amount_side(cell)[0]


def _clean_no(v) -> str:
    """Voucher numbers arrive as 17, 17.0 or '17': show them as 17."""
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    s = str(v).strip()
    return s[:-2] if re.fullmatch(r"\d+\.0", s) else s


def _xlsx_raw(data: bytes) -> pd.DataFrame:
    """The sheet holding the Day Book as a raw grid. Tally keeps Dr/Cr in a cell's number format
    (`0.00" Dr"`), which pandas discards, so such cells are turned into text like '1234.5 Dr'."""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(data), data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open the file as an Excel workbook: {e}") from e
    pick = None
    for ws in wb.worksheets:
        for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 40), values_only=True):
            cells = [_norm(c) for c in row]
            if "date" in cells and any(c in _ALIASES["ledger"] for c in cells):
                pick = ws
                break
        if pick is not None:
            break
    ws = pick or wb.worksheets[0]
    rows = []
    for row in ws.iter_rows():
        out = []
        for c in row:
            v = c.value
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v != 0:
                m = _SIDE_FMT.search((c.number_format or "").replace('"', " "))
                if m:
                    v = f"{abs(float(v))} {m.group(1).capitalize()}"
            out.append(v)
        rows.append(out)
    return pd.DataFrame(rows, dtype=object)


def _from_table(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Best-effort reader for Tally's Excel/CSV Day Book export.

    A row with a date starts a voucher; following rows without a date are its ledger
    lines (or narration when they carry no amount).
    """
    hdr = None
    for i in range(min(len(raw), 40)):
        cells = [_norm(c) for c in raw.iloc[i].tolist()]
        if "date" in cells and any(c in _ALIASES["ledger"] for c in cells):
            hdr = i
            break
    if hdr is None:
        raise ValueError("Could not find a header row with 'Date' and 'Particulars'. "
                         "Export the Day Book from Tally as XML for best results.")
    cols = [_norm(c) for c in raw.iloc[hdr].tolist()]
    idx: dict[str, int] = {}
    for key, names in _ALIASES.items():
        for j, c in enumerate(cols):
            if c in names:
                idx.setdefault(key, j)
    if "debit" not in idx and "credit" not in idx and "amount" not in idx:
        raise ValueError("Could not find Debit/Credit (or Amount) columns in the file.")

    def cell(r, key):
        j = idx.get(key)
        return r.iloc[j] if j is not None and j < len(r) else None

    def text(v) -> str:
        return "" if v is None or (not isinstance(v, str) and pd.isna(v)) else str(v).strip()

    vouchers: list[dict] = []
    masked_labels: Counter = Counter()
    cur = None
    for rowno, r in raw.iloc[hdr + 1:].iterrows():
        ledger = text(cell(r, "ledger"))
        low = ledger.lower()
        if low.startswith(("grand total", "opening balance", "closing balance")) or low == "total":
            continue
        dr, cr = _num(cell(r, "debit")), _num(cell(r, "credit"))
        if "amount" in idx and dr == 0 and cr == 0:
            amt, side = _amount_side(cell(r, "amount"))
            if amt:
                if side is None:
                    raise ValueError(f"Row {rowno + 1}: cannot tell whether {amt:,.2f} is a debit or a credit. "
                                     "The Amount column needs a Dr/Cr marker; export the Day Book from Tally again "
                                     "in its default Excel format, or as XML.")
                dr, cr = (amt, 0.0) if side == "Dr" else (0.0, amt)
        raw_date = cell(r, "date")
        date = pd.to_datetime(raw_date, dayfirst=True, errors="coerce")
        # Text in the date column that is not a date means the date is hidden, not repeated: TallyPrime Educational
        # Mode writes the word "Educational" for every date except the 1st, 2nd and 31st.
        masked = text(raw_date) if pd.isna(date) else ""
        vtype, vno = text(cell(r, "vch_type")), _clean_no(cell(r, "vch_no"))
        # A dated row starts a voucher. So does an undated row that names a voucher type or number: Tally shows
        # the date only once for the vouchers of a day.
        new_voucher = pd.notna(date) or bool(masked) or (cur is not None and bool(vtype or vno))
        if new_voucher:
            if masked:
                masked_labels[masked] += 1
            cur = {"date": date if pd.notna(date) else (pd.NaT if masked else cur["date"]), "vch_type": vtype,
                   "vch_no": vno, "narration": text(cell(r, "narration")), "lines": []}
            vouchers.append(cur)
        elif cur is None or not ledger:
            continue
        if dr == 0 and cr == 0:
            if not new_voucher and ledger:  # amount-less continuation row = narration text
                cur["narration"] = (cur["narration"] + " " + ledger).strip()
            continue
        if dr:
            cur["lines"].append((ledger, "Dr", dr))
        if cr:
            cur["lines"].append((ledger, "Cr", cr))

    rows = []
    # Some exports repeat the voucher total on the first row; Tally's own does not (the first row is a real ledger line).
    # Only correct for it when most multi-line vouchers fail to balance as they stand.
    multi = [v for v in vouchers if len(v["lines"]) >= 2]
    first_row_is_a_total = bool(multi) and sum(abs(_balance(v["lines"])) <= 0.5 for v in multi) / len(multi) < 0.9
    for n, v in enumerate(vouchers, start=1):
        lines = _drop_header_line(v["lines"]) if first_row_is_a_total else v["lines"]
        for ledger, side, amt in lines:
            rows.append([f"V{n:05d}", v["date"], v["vch_type"], v["vch_no"], ledger, side, amt, v["narration"]])
    meta = {"skipped": 0, "format": "table", "date_label": masked_labels.most_common(1)[0][0] if masked_labels else ""}
    return pd.DataFrame(rows, columns=COLUMNS), meta


def _balance(lines: list[tuple]) -> float:
    return sum(a for _, s, a in lines if s == "Dr") - sum(a for _, s, a in lines if s == "Cr")


def _drop_header_line(lines: list[tuple]) -> list[tuple]:
    """Detailed exports that repeat the voucher total on the first row: drop it if doing so
    makes an unbalanced voucher balance."""
    if len(lines) >= 3 and abs(_balance(lines)) > 0.5 and abs(_balance(lines[1:])) <= 0.5:
        return lines[1:]
    return lines
