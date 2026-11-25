"""Upload safety checks and raw readers (.xlsx / .csv -> list of rows).

Checks, in order: extension allow-list, size limit, content matches extension, and for .xlsx:
no macros (vbaProject / macro sheets / macro content types), no zip bomb (entry count,
total uncompressed size, compression ratio), no path tricks. Old binary .xls is refused.
The file is never executed or extracted to disk; openpyxl reads it from memory with
data_only=True (cached values only, formulas are not evaluated).
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import PurePath

import openpyxl

MAX_ZIP_ENTRIES = 2000
MAX_UNCOMPRESSED = 150 * 1024 * 1024
MAX_RATIO = 250
MAX_ROWS = 100_000
SKIP_SHEETS = {"example", "example (wide)", "instructions", "hand check"}
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class UploadRejected(ValueError):
    """Raised with a user-readable reason; nothing is stored except the hash log entry."""


@dataclass
class RawTable:
    rows: list[list]          # cell values as read (str / int / float / datetime / None)
    sheet: str
    sha256: str
    size: int
    extension: str


def safe_filename(name: str) -> str:
    base = PurePath(name.replace("\\", "/")).name
    base = re.sub(r"[^A-Za-z0-9._ -]+", "_", base).strip(" .") or "upload"
    return base[:120]


def sha256_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def check_upload(filename: str, content: bytes, max_bytes: int,
                 allowed: tuple[str, ...] = (".xlsx", ".csv")) -> str:
    """Return the (lower-case) extension or raise UploadRejected."""
    ext = PurePath(filename).suffix.lower()
    if ext not in allowed:
        hint = " Save it as .xlsx (Excel Workbook) first." if ext in (".xls", ".xlsm", ".xlsb") else ""
        raise UploadRejected(f"File type '{ext or '(none)'}' is not accepted. Use {' or '.join(allowed)}.{hint}")
    if not content:
        raise UploadRejected("The file is empty.")
    if len(content) > max_bytes:
        raise UploadRejected(f"The file is {len(content) / 1048576:.1f} MB; the limit is {max_bytes / 1048576:.0f} MB.")
    if content.startswith(OLE_MAGIC):
        raise UploadRejected("This is an old binary Excel file (.xls) renamed. Save it as .xlsx first.")
    is_zip = content[:4] == b"PK\x03\x04"
    if ext == ".csv":
        if is_zip:
            raise UploadRejected("The file is named .csv but is an Excel workbook. Rename it to .xlsx.")
        if b"\x00" in content[:65536]:
            raise UploadRejected("The CSV contains binary data. Export it again as plain CSV (UTF-8).")
        return ext
    if not is_zip:
        raise UploadRejected("The file is named .xlsx but is not an Excel workbook.")
    _check_xlsx_container(content)
    return ext


def _check_xlsx_container(content: bytes) -> None:
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise UploadRejected("The workbook is damaged and cannot be opened.") from exc
    with zf:
        infos = zf.infolist()
        if len(infos) > MAX_ZIP_ENTRIES:
            raise UploadRejected("The workbook has an unusual structure (too many parts).")
        names = {i.filename for i in infos}
        if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
            raise UploadRejected("The file is not a standard Excel workbook.")
        total = 0
        for i in infos:
            n = i.filename
            if n.startswith(("/", "\\")) or ".." in PurePath(n).parts:
                raise UploadRejected("The workbook contains unsafe internal paths.")
            low = n.lower()
            if low.endswith("vbaproject.bin") or "/macrosheets/" in low or low.endswith(".bin") and "vba" in low:
                raise UploadRejected("The workbook contains macros. Save it as a macro-free .xlsx and upload again.")
            total += i.file_size
            if i.compress_size and i.file_size / i.compress_size > MAX_RATIO and i.file_size > 1_000_000:
                raise UploadRejected("The workbook is abnormally compressed and was refused.")
        if total > MAX_UNCOMPRESSED:
            raise UploadRejected("The workbook is too large when opened.")
        ct = zf.read("[Content_Types].xml").decode("utf-8", "replace").lower()
        if "macroenabled" in ct or "vbaproject" in ct:
            raise UploadRejected("The workbook is macro-enabled. Save it as a macro-free .xlsx and upload again.")


def read_table(filename: str, content: bytes, max_bytes: int, sheet: str | None = None) -> RawTable:
    ext = check_upload(filename, content, max_bytes)
    digest = sha256_of(content)
    if ext == ".csv":
        rows, name = _read_csv(content), "csv"
    else:
        rows, name = _read_xlsx(content, sheet)
    return RawTable(rows=rows, sheet=name, sha256=digest, size=len(content), extension=ext)


def _read_csv(content: bytes) -> list[list]:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = []
    for i, row in enumerate(csv.reader(io.StringIO(text), dialect)):
        if i >= MAX_ROWS:
            raise UploadRejected(f"More than {MAX_ROWS:,} rows; split the file.")
        rows.append([c if c != "" else None for c in row])
    return rows


def _read_xlsx(content: bytes, sheet: str | None) -> tuple[list[list], str]:
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True, keep_links=False)
    except Exception as exc:  # openpyxl raises many types for corrupt files
        raise UploadRejected("The workbook could not be read. Open it in Excel and save it again.") from exc
    try:
        names = wb.sheetnames
        if sheet:
            pick = next((n for n in names if n.lower() == sheet.lower()), None)
            if pick is None:
                raise UploadRejected(f"Sheet '{sheet}' not found. Sheets: {', '.join(names)}.")
        else:
            pick = next((n for n in names if n.lower() == "data"), None)
            if pick is None:
                pick = next((n for n in names if n.lower() not in SKIP_SHEETS), names[0])
        ws = wb[pick]
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= MAX_ROWS:
                raise UploadRejected(f"More than {MAX_ROWS:,} rows; split the file.")
            rows.append(list(row))
        # drop trailing empty columns (read-only mode pads to the sheet's dimension)
        width = max((max((j for j, v in enumerate(r) if v not in (None, "")), default=-1) for r in rows),
                    default=-1) + 1
        return [r[:width] for r in rows], pick
    finally:
        wb.close()
