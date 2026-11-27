"""Read the documented demonstration layouts, retaining evidence for every row."""
from __future__ import annotations

import hashlib
import re
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook
from pypdf import PdfReader


class InputError(ValueError):
    """An actionable problem with the selected reporting folder."""


FILES = {
    "Model": ("Starting Model", ".xlsx"),
    "Summary": ("CF", ".pdf"),
    "Detail": ("CF-Detailed", ".pdf"),
    "Projection": ("CF-Proj", ".pdf"),
    "Cheques": ("PDC", ".pdf"),
    "Creditors": ("Creditors", ".xlsx"),
    "Expenses": ("Other Creditors", ".xlsx"),
    "Facilities": ("LC", ".xlsx"),
    "Costs": ("Material Purchase", ".xlsx"),
}
ALIASES = {"Summary": ("ACTCF",), "Creditors": ("Ceditors",), "Facilities": ("LCs",)}
PDF_HEADERS = {
    "Summary": ("Category", "Amount"),
    "Detail": ("Date", "Reference", "Project", "Category", "Amount"),
    "Projection": ("Month", "Category", "Amount"),
    "Cheques": ("Cheque", "Party", "Cheque date", "Amount", "Status", "LTR"),
}
TITLES = {"Summary": "Actual cash summary", "Detail": "Actual cash detail",
          "Projection": "Projected payments", "Cheques": "Cheque register"}
MILLS = Decimal("0.001")


def amount(value, where):
    try:
        n = Decimal(str(value))
        if not n.is_finite() or abs(n) >= 10**11 or n != n.quantize(MILLS):
            raise InvalidOperation
        return n.quantize(MILLS)
    except (ValueError, InvalidOperation):
        raise InputError(f"{where} — expected an amount with up to three decimal places, got {value!r}.") from None


def iso_date(value, where):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise InputError(f"{where} — use a date in YYYY-MM-DD format.") from None


def month(value, where):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", str(value)):
        raise InputError(f"{where} — expected a month in YYYY-MM format.")
    return iso_date(str(value) + "-01", where)


def shift(value, offset):
    year, index = divmod(value.year * 12 + value.month - 1 + offset, 12)
    return date(year, index + 1, 1)


@dataclass(frozen=True)
class Source:
    role: str
    name: str
    digest: str
    data: bytes


def discover(folder, *, require_demo_model=True):
    folder = Path(folder)
    if not folder.is_dir():
        raise InputError("Select a folder containing the weekly source files.")
    paths = [p for p in folder.iterdir() if p.is_file() and not p.name.startswith("~$")]
    found, errors = {}, []
    for role, (stem, extension) in FILES.items():
        if role == "Model" and not require_demo_model:
            continue
        names = (stem,) + ALIASES.get(role, ())
        pattern = "(?:" + "|".join(re.escape(name) for name in names) + r")(?:\s*-\s*\d{2}-\d{2}-\d{4})?"
        hits = [p for p in paths if p.suffix.lower() == extension and re.fullmatch(pattern, p.stem, re.I)]
        if len(hits) == 1:
            found[role] = hits[0]
        else:
            errors.append(f"Missing {stem}{extension}" if not hits else
                          f"Multiple files for {role}: " + ", ".join(p.name for p in hits))
    if errors:
        raise InputError("\n".join(errors))
    return found


def snapshots(folder, paths=None):
    result = {}
    for role, path in (paths or discover(folder)).items():
        content = path.read_bytes()
        result[role] = Source(role, path.name, hashlib.sha256(content).hexdigest(), content)
    return result


@dataclass
class Table:
    cutoff: date
    currency: str
    rows: list


def xls_table(source, sheet, headers):
    book = load_workbook(BytesIO(source.data), read_only=True, data_only=False)
    try:
        if sheet not in book.sheetnames:
            raise InputError(f"{source.name} — missing sheet '{sheet}'.")
        rows = book[sheet].values
        meta = next(rows, ())
        if len(meta) < 3 or meta[0] != source.role:
            raise InputError(f"{source.name} / {sheet}!A1:C1 — expected role, cutoff date and currency.")
        cutoff = iso_date(meta[1], f"{source.name} / {sheet}!B1")
        fields = list(next(rows, ()))
        while fields and fields[-1] is None:
            fields.pop()
        if fields != list(headers):
            raise InputError(f"{source.name} / {sheet}!2 — expected columns: {', '.join(headers)}.")
        records = []
        for i, row in enumerate(rows, 3):
            if all(v is None for v in row):
                continue
            locator = f"{source.name} / {sheet}!{i}"
            values = tuple(row[:len(headers)])
            if any(isinstance(v, str) and v.startswith("=") for v in values):
                raise InputError(f"{locator} — demo inputs require explicit values. A formula was found.")
            records.append((dict(zip(headers, values)), locator))
        return Table(cutoff, str(meta[2]), records)
    finally:
        book.close()


def page_lines(page):
    """Group text by baseline, using composed PDF text/user coordinates."""
    lines = {}
    def collect(text, cm, tm, font, size):
        text = text.strip()
        if not text:
            return
        x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
        y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
        lines.setdefault(round(y, 1), []).append((x, text))
    page.extract_text(visitor_text=collect)
    return [sorted(cells) for _, cells in sorted(lines.items(), reverse=True)]


def pdf_table(source):
    headers = PDF_HEADERS[source.role]
    result = []
    cutoff = currency = None
    for i, page in enumerate(PdfReader(BytesIO(source.data)).pages, 1):
        where = f"{source.name} / p.{i}"
        lines = page_lines(page)
        if len(lines) < 4 or TITLES[source.role] not in [v for _, v in lines[0]]:
            raise InputError(f"{where} — expected a text PDF in the '{TITLES[source.role]}' demo layout.")
        meta = re.fullmatch(r"As of (\d{4}-\d{2}-\d{2}) \| Currency ([A-Z]{3}) \| Demo v1", lines[1][0][1])
        if not meta:
            raise InputError(f"{where} — missing internal report date or currency.")
        current = iso_date(meta[1], where)
        if cutoff and (current != cutoff or meta[2] != currency):
            raise InputError(f"{where} — the period or currency changes between pages.")
        cutoff, currency = current, meta[2]
        if tuple(v for _, v in lines[2]) != headers:
            raise InputError(f"{where} — unexpected table headers.")
        # Fields in the sample PDFs are left-aligned under their column heading.
        boundaries = [x - 2 for x, _ in lines[2][1:]]
        items = lines[3:-1]
        if lines[-1][0][1] != f"Records on page: {len(items)}":
            raise InputError(f"{where} — the footer record count does not reconcile.")
        for rownum, cells in enumerate(items, 1):
            fields = [""] * len(headers)
            for x, text in cells:
                col = bisect_right(boundaries, x)
                if fields[col]:
                    raise InputError(f"{where}, row {rownum} — ambiguous text in column {headers[col]}.")
                fields[col] = text
            result.append((dict(zip(headers, fields)), f"{where}, row {rownum}"))
    if cutoff is None:
        raise InputError(f"{source.name} — empty report.")
    return Table(cutoff, currency, result)
