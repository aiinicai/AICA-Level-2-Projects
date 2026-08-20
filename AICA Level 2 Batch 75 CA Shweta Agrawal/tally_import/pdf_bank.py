"""
Reads a (optionally password-protected) bank statement PDF into a DataFrame,
so it can flow through the exact same column-mapping UI/endpoints already
built for Excel/CSV bank statements -- no separate PDF-specific mapping logic
needed. Bank statement PDFs vary wildly between banks, so this makes no
assumption about which columns mean what; it just gets a table out.
"""
from __future__ import annotations

import io

import pandas as pd
import pdfplumber
import pypdf


def _decrypt(data: bytes, password: str | None) -> io.BytesIO:
    buf = io.BytesIO(data)
    reader = pypdf.PdfReader(buf)
    if not reader.is_encrypted:
        buf.seek(0)
        return buf

    if not password:
        raise ValueError("This PDF is password-protected -- enter the password to open it.")

    result = reader.decrypt(password)
    if result == pypdf.PasswordType.NOT_DECRYPTED:
        raise ValueError("Incorrect password for this PDF.")

    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out


def extract_table(file_obj, password: str | None = None) -> pd.DataFrame:
    """Picks the LARGEST table found across all pages as the transaction table,
    then merges any other table whose header row exactly matches it (a repeated
    header on a later page, i.e. a continuation) -- rather than just taking the
    first table found. Bank statement PDFs commonly have a small letterhead/
    address block that a naive "first table" scan can mistake for the real
    data, especially once we fall back to text-alignment detection (no ruled
    lines to tell letterhead text apart from a real table); the real
    transaction table is reliably much larger than that.

    Tries pdfplumber's default ruled-line table detection first; many bank
    statements have no visible cell borders at all (text is just aligned into
    columns), so this falls back to text-alignment-based detection if the
    default strategy finds nothing."""
    data = file_obj.read()
    buf = _decrypt(data, password)

    def _all_tables(table_settings=None):
        found = []
        with pdfplumber.open(buf) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables(table_settings) if table_settings else page.extract_tables()
                for table in tables:
                    if table and len(table) >= 1:
                        found.append(table)
        return found

    tables = _all_tables()
    if not tables:
        buf.seek(0)
        tables = _all_tables({"vertical_strategy": "text", "horizontal_strategy": "text"})

    if not tables:
        raise ValueError(
            "Could not find a table in this PDF -- it may be a scanned image "
            "rather than a real text/table PDF, or use a layout this tool can't "
            "detect. Try exporting the statement as Excel/CSV instead if your "
            "bank offers that option."
        )

    main = max(tables, key=len)
    header = main[0]
    rows = list(main[1:])
    for table in tables:
        if table is main:
            continue
        if table[0] == header:
            rows.extend(table[1:])  # continuation of the same table on another page

    width = len(header)
    header = [str(h).strip() if h else f"Col{i+1}" for i, h in enumerate(header)]
    # pad/truncate any ragged rows so pandas doesn't choke on column-count mismatches
    fixed_rows = [((r + [None] * width)[:width]) for r in rows]
    return pd.DataFrame(fixed_rows, columns=header)
