"""
database.py
-----------
SQLite database management module for LC Analyser.
Stores analysis records, metadata, document text, and individual clause points
with user verdicts and custom remarks. Provides multi-criteria search by
LC Number, Issuer Name, Amount, Beneficiary, etc.
"""

from __future__ import annotations

import os
import re
import sys
import sqlite3
import datetime
from typing import Dict, List, Optional, Tuple, Any

from models import AnalysisResult, ClausePoint

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_DB_PATH = os.path.join(APP_DIR, "lc_database.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Creates a database connection with foreign key support enabled."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes database tables, columns and indexes if they do not exist."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lc_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dc_number TEXT,
                    lc_type TEXT,
                    source_filename TEXT,
                    issuer_name TEXT,
                    applicant_bank_name TEXT,
                    applicant_name TEXT,
                    beneficiary_name TEXT,
                    currency TEXT,
                    amount_text TEXT,
                    amount_num REAL,
                    issue_date TEXT,
                    expiry_date TEXT,
                    shipment_date TEXT,
                    status TEXT DEFAULT 'Analysed',
                    total_points INTEGER DEFAULT 0,
                    amendment_count INTEGER DEFAULT 0,
                    clarification_count INTEGER DEFAULT 0,
                    correct_count INTEGER DEFAULT 0,
                    full_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS lc_clauses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id INTEGER NOT NULL REFERENCES lc_records(id) ON DELETE CASCADE,
                    sl_no INTEGER,
                    point_no TEXT,
                    header TEXT,
                    summary TEXT,
                    raw_text TEXT,
                    section TEXT,
                    subsection TEXT,
                    suggested_verdict TEXT,
                    analysis_note TEXT,
                    user_verdict TEXT,
                    user_remarks TEXT
                )
            """)

            # Ensure applicant_bank_name column exists for pre-existing tables
            try:
                conn.execute("ALTER TABLE lc_records ADD COLUMN applicant_bank_name TEXT")
            except Exception:
                pass

            # Indexes for fast search
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lc_records_dc_number ON lc_records(dc_number)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lc_records_issuer ON lc_records(issuer_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lc_records_app_bank ON lc_records(applicant_bank_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lc_records_beneficiary ON lc_records(beneficiary_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lc_records_amount_num ON lc_records(amount_num)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lc_records_updated_at ON lc_records(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lc_clauses_record_id ON lc_clauses(record_id)")

            # Auto-clean legacy records with unparsed prefixes (e.g. 'Name and Address:')
            _backfill_existing_records(conn)
    finally:
        conn.close()


def _backfill_existing_records(conn: sqlite3.Connection) -> None:
    """Updates legacy or improperly formatted party/bank names in existing database records."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, issuer_name, applicant_bank_name, beneficiary_name 
            FROM lc_records
        """)
        records = cur.fetchall()
        for r in records:
            rid = r[0]
            curr_iss = r[1] or ""
            curr_app_bank = r[2] or ""
            curr_ben = r[3] or ""

            needs_update = (
                not curr_app_bank
                or curr_ben.strip() == "Name and Address:"
                or curr_ben.startswith("/")
                or curr_iss.strip() == "Name and Address:"
            )
            if not needs_update:
                continue

            cur.execute("SELECT point_no, header, raw_text, summary FROM lc_clauses WHERE record_id = ?", (rid,))
            clauses = cur.fetchall()
            found_app_bank, found_iss_bank, found_ben = "", "", ""
            found_drawee = ""
            for c in clauses:
                tag = (c[0] or "").upper().strip()
                hdr = (c[1] or "").lower().strip()
                raw_t = c[2] or ""
                summ_t = c[3] or ""
                if (tag in ("51A", "51D") or hdr == "applicant bank") and not found_app_bank:
                    found_app_bank = _clean_party_text(raw_t, summ_t)
                elif (tag in ("52A", "52D") or hdr == "issuing bank") and not found_iss_bank:
                    found_iss_bank = _clean_party_text(raw_t, summ_t)
                elif (tag == "59" or hdr == "beneficiary") and not found_ben:
                    found_ben = _clean_party_text(raw_t, summ_t)
                elif tag in ("42A", "42D") and not found_drawee:
                    found_drawee = _clean_party_text(raw_t, summ_t)

            final_app_bank = found_app_bank or curr_app_bank or found_iss_bank or found_drawee or curr_iss
            final_iss_bank = found_iss_bank or curr_iss or found_app_bank or found_drawee
            final_ben = found_ben or _clean_party_text(curr_ben, "")

            if final_iss_bank.strip() == "Name and Address:":
                final_iss_bank = final_app_bank if final_app_bank != "Name and Address:" else ""
            if final_app_bank.strip() == "Name and Address:":
                final_app_bank = final_iss_bank if final_iss_bank != "Name and Address:" else ""

            cur.execute("""
                UPDATE lc_records SET
                    applicant_bank_name = ?,
                    issuer_name = ?,
                    beneficiary_name = ?
                WHERE id = ?
            """, (final_app_bank, final_iss_bank, final_ben, rid))
    except Exception:
        pass


def _clean_party_text(raw_text: str, summary: str = "") -> str:
    """
    Extracts the clean party or bank name from raw clause text or summary.
    Correctly handles bank headers (e.g. 'Name and Address:'), account numbers,
    leading slashes, and SWIFT message artifacts.
    """
    raw_lines = [l.strip() for l in (raw_text or "").splitlines() if l.strip()]

    ignore_prefixes = (
        "name and address", "name & address", "party identifier",
        "identifier code", "account", "a/c", "applicant bank",
        "issuing bank", "beneficiary", "applicant", "drawee",
        "message text", "page of", "page ", "swift output",
        "documentary credit number", "currency code, amount",
        "date of issue", "date and place of expiry",
    )

    tag_pattern = re.compile(r"^\s*:?F?\d{2}[A-Za-z]{0,2}\s*:\s*(.*)$", re.I)
    candidate_lines = []

    for line in raw_lines:
        m = tag_pattern.match(line)
        text = m.group(1).strip() if m else line.strip()

        # Handle SWIFT lines starting with /
        if text.startswith("/"):
            # Skip SWIFT account-only lines, e.g. /12345678 or /D/12345678
            if re.match(r"^/(?:[A-Z]/)?\d[\d\s-]*$", text):
                continue
            # Strip leading slash if followed by company/party name, e.g. /UNISTAR FABRICS PVT LTD.
            text = text.lstrip("/ ").strip()

        lower = text.lower().rstrip(":")
        if not lower:
            continue

        if any(lower == ign or lower.startswith(ign + ":") or lower.startswith(ign + " :") for ign in ignore_prefixes):
            if ":" in text:
                after = text.split(":", 1)[1].strip()
                if after:
                    candidate_lines.append(after)
            continue

        candidate_lines.append(text)

    if candidate_lines:
        res = candidate_lines[0]
        res = re.sub(r"^[/:#\s]+", "", res).strip()
        if res:
            return res

    # Fallback to summary
    if summary:
        s = summary.strip()
        s = re.sub(
            r"^(?:name\s*(?:and|&)\s*address\s*:?|party\s*identifier\s*:?|beneficiary\s*:?|applicant(?:\s*bank)?\s*:?|issuing\s*bank\s*:?)\s*",
            "", s, flags=re.I
        ).strip()
        s = re.sub(r"^[/:#\s]+", "", s).strip()
        if s:
            return s.splitlines()[0].strip()

    return ""


def _parse_amount_and_currency(text: str) -> Tuple[str, str, Optional[float]]:
    """
    Extracts currency code, formatted amount string, and numeric value.
    Example: 'USD 250000,00' or 'USD 250,000.00' -> ('USD', 'USD 250,000.00', 250000.0)
    """
    if not text:
        return "", "", None

    # Filter out header line if present
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    clean_lines = []
    for l in lines:
        if re.match(r"^\s*:?F?\d{2}[A-Za-z]{0,2}\s*:\s*(?:currency|amount)", l, re.I):
            # Check if value is on same line after colon
            parts = l.split(":", 2)
            if len(parts) > 2 and any(c.isdigit() for c in parts[-1]):
                clean_lines.append(parts[-1].strip())
        else:
            clean_lines.append(l)

    search_target = " ".join(clean_lines) if clean_lines else text

    # Look for 3-uppercase letters currency followed by numbers
    m = re.search(r"\b([A-Z]{3})\s*([0-9][0-9.,\s]*)", search_target)
    if m:
        currency = m.group(1).upper()
        raw_amt = m.group(2).strip()
        amt_clean = raw_amt.replace(" ", "")
        
        if "," in amt_clean and "." in amt_clean:
            if amt_clean.rfind(",") > amt_clean.rfind("."):
                num_str = amt_clean.replace(".", "").replace(",", ".")
            else:
                num_str = amt_clean.replace(",", "")
        elif "," in amt_clean:
            parts = amt_clean.split(",")
            if len(parts) == 2 and len(parts[1]) == 2:
                num_str = amt_clean.replace(",", ".")
            else:
                num_str = amt_clean.replace(",", "")
        else:
            num_str = amt_clean
            
        try:
            val = float(num_str)
            formatted_amt = f"{currency} {val:,.2f}"
            return currency, formatted_amt, val
        except ValueError:
            return currency, f"{currency} {raw_amt}", None

    # Fallback to any number
    m2 = re.search(r"\b([0-9][0-9.,]*)\b", search_target)
    if m2:
        raw_amt = m2.group(1).strip().replace(",", "")
        try:
            val = float(raw_amt)
            return "", f"{val:,.2f}", val
        except ValueError:
            return "", raw_amt, None

    return "", text.strip(), None


def extract_metadata_from_analysis(result: AnalysisResult) -> Dict[str, Any]:
    """
    Extracts key searchable metadata from an AnalysisResult object by inspecting
    its clauses and document fields.
    """
    metadata: Dict[str, Any] = {
        "dc_number": result.dc_number or "",
        "lc_type": result.lc_type or "Draft LC",
        "source_filename": result.source_filename or "",
        "issuer_name": "",
        "applicant_bank_name": "",
        "applicant_name": "",
        "beneficiary_name": "",
        "currency": "",
        "amount_text": "",
        "amount_num": None,
        "issue_date": "",
        "expiry_date": "",
        "shipment_date": "",
        "status": "Analysed",
        "total_points": len(result.clauses),
        "amendment_count": 0,
        "clarification_count": 0,
        "correct_count": 0,
    }

    # Count verdicts
    for clause in result.clauses:
        verdict = clause.effective_verdict()
        if verdict == "Requires Amendment":
            metadata["amendment_count"] += 1
        elif verdict == "Needs Clarification":
            metadata["clarification_count"] += 1
        elif verdict == "Correct / In Order":
            metadata["correct_count"] += 1

    if metadata["amendment_count"] > 0:
        metadata["status"] = f"Amendment Required ({metadata['amendment_count']})"
    else:
        metadata["status"] = "In Order"

    drawee_bank = ""

    # Scan clauses for key SWIFT tags and headers
    for clause in result.clauses:
        tag = clause.point_no.upper().strip()
        hdr = (clause.header or "").lower().strip()
        raw_txt = (clause.raw_text or "").strip()
        summary_val = (clause.summary or "").strip()

        if tag == "20" and not metadata["dc_number"]:
            metadata["dc_number"] = _clean_party_text(raw_txt, summary_val) or summary_val
        elif (tag in ("51A", "51D") or hdr == "applicant bank") and not metadata["applicant_bank_name"]:
            metadata["applicant_bank_name"] = _clean_party_text(raw_txt, summary_val)
        elif (tag in ("52A", "52D") or hdr == "issuing bank") and not metadata["issuer_name"]:
            metadata["issuer_name"] = _clean_party_text(raw_txt, summary_val)
        elif (tag == "50" or hdr == "applicant") and not metadata["applicant_name"]:
            metadata["applicant_name"] = _clean_party_text(raw_txt, summary_val)
        elif (tag == "59" or hdr == "beneficiary") and not metadata["beneficiary_name"]:
            metadata["beneficiary_name"] = _clean_party_text(raw_txt, summary_val)
        elif tag in ("42A", "42D") and not drawee_bank:
            drawee_bank = _clean_party_text(raw_txt, summary_val)
        elif tag in ("32B", "39B") and not metadata["amount_text"]:
            ccy, amt_str, amt_val = _parse_amount_and_currency(raw_txt or summary_val)
            metadata["currency"] = ccy
            metadata["amount_text"] = amt_str
            metadata["amount_num"] = amt_val
        elif tag == "31C" and not metadata["issue_date"]:
            metadata["issue_date"] = summary_val
        elif tag == "31D" and not metadata["expiry_date"]:
            metadata["expiry_date"] = summary_val
        elif tag in ("44C", "44D") and not metadata["shipment_date"]:
            metadata["shipment_date"] = summary_val

    # Ensure applicant_bank_name and issuer_name cross-populate if one is missing
    if not metadata["applicant_bank_name"] and metadata["issuer_name"]:
        metadata["applicant_bank_name"] = metadata["issuer_name"]
    if not metadata["issuer_name"] and metadata["applicant_bank_name"]:
        metadata["issuer_name"] = metadata["applicant_bank_name"]

    # Fallback search in full text if any key bank is missing
    if not metadata["applicant_bank_name"] and not metadata["issuer_name"]:
        if drawee_bank:
            metadata["applicant_bank_name"] = drawee_bank
            metadata["issuer_name"] = drawee_bank
        else:
            m = re.search(r"(?:applicant bank|issuing bank|drawn on|available with|sender)[:\s]+([^\n\r]{3,60})", result.full_text, re.I)
            if m:
                bank_found = _clean_party_text(m.group(1).strip())
                metadata["applicant_bank_name"] = bank_found
                metadata["issuer_name"] = bank_found

    if not metadata["beneficiary_name"]:
        m = re.search(r"(?:beneficiary|in favou?r of)[:\s]+([^\n\r]{3,60})", result.full_text, re.I)
        if m:
            metadata["beneficiary_name"] = _clean_party_text(m.group(1).strip())

    return metadata


def save_or_update_analysis(
    result: AnalysisResult,
    record_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> int:
    """
    Saves an AnalysisResult into the SQLite database.
    If record_id is provided, updates that existing record and replaces its clauses.
    Returns the database record ID.
    """
    init_db(db_path)
    meta = extract_metadata_from_analysis(result)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection(db_path)
    try:
        with conn:
            if record_id is not None:
                conn.execute("""
                    UPDATE lc_records SET
                        dc_number = ?,
                        lc_type = ?,
                        source_filename = ?,
                        issuer_name = ?,
                        applicant_bank_name = ?,
                        applicant_name = ?,
                        beneficiary_name = ?,
                        currency = ?,
                        amount_text = ?,
                        amount_num = ?,
                        issue_date = ?,
                        expiry_date = ?,
                        shipment_date = ?,
                        status = ?,
                        total_points = ?,
                        amendment_count = ?,
                        clarification_count = ?,
                        correct_count = ?,
                        full_text = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (
                    meta["dc_number"],
                    meta["lc_type"],
                    meta["source_filename"],
                    meta["issuer_name"],
                    meta["applicant_bank_name"],
                    meta["applicant_name"],
                    meta["beneficiary_name"],
                    meta["currency"],
                    meta["amount_text"],
                    meta["amount_num"],
                    meta["issue_date"],
                    meta["expiry_date"],
                    meta["shipment_date"],
                    meta["status"],
                    meta["total_points"],
                    meta["amendment_count"],
                    meta["clarification_count"],
                    meta["correct_count"],
                    result.full_text,
                    now_str,
                    record_id,
                ))
                conn.execute("DELETE FROM lc_clauses WHERE record_id = ?", (record_id,))
                current_id = record_id
            else:
                cursor = conn.execute("""
                    INSERT INTO lc_records (
                        dc_number, lc_type, source_filename, issuer_name,
                        applicant_bank_name, applicant_name, beneficiary_name,
                        currency, amount_text, amount_num, issue_date, expiry_date,
                        shipment_date, status, total_points, amendment_count,
                        clarification_count, correct_count, full_text, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    meta["dc_number"],
                    meta["lc_type"],
                    meta["source_filename"],
                    meta["issuer_name"],
                    meta["applicant_bank_name"],
                    meta["applicant_name"],
                    meta["beneficiary_name"],
                    meta["currency"],
                    meta["amount_text"],
                    meta["amount_num"],
                    meta["issue_date"],
                    meta["expiry_date"],
                    meta["shipment_date"],
                    meta["status"],
                    meta["total_points"],
                    meta["amendment_count"],
                    meta["clarification_count"],
                    meta["correct_count"],
                    result.full_text,
                    now_str,
                    now_str,
                ))
                current_id = cursor.lastrowid

            clause_rows = []
            for c in result.clauses:
                clause_rows.append((
                    current_id,
                    c.sl_no,
                    c.point_no,
                    c.header,
                    c.summary,
                    c.raw_text,
                    c.section,
                    c.subsection,
                    c.suggested_verdict,
                    c.analysis_note,
                    c.user_verdict,
                    c.user_remarks,
                ))

            conn.executemany("""
                INSERT INTO lc_clauses (
                    record_id, sl_no, point_no, header, summary, raw_text,
                    section, subsection, suggested_verdict, analysis_note,
                    user_verdict, user_remarks
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, clause_rows)

        return current_id
    finally:
        conn.close()


def get_analysis_by_id(
    record_id: int, db_path: Optional[str] = None
) -> Optional[Tuple[AnalysisResult, Dict[str, Any]]]:
    """
    Retrieves an AnalysisResult and its metadata dictionary from the database by ID.
    Reconstructs exact ClausePoint objects preserving all verdicts and remarks.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM lc_records WHERE id = ?", (record_id,))
        rec = cur.fetchone()
        if not rec:
            return None

        meta = dict(rec)

        cur.execute("""
            SELECT * FROM lc_clauses WHERE record_id = ? ORDER BY sl_no ASC, id ASC
        """, (record_id,))
        clause_rows = cur.fetchall()

        clauses: List[ClausePoint] = []
        for cr in clause_rows:
            clauses.append(ClausePoint(
                sl_no=cr["sl_no"],
                point_no=cr["point_no"] or "",
                header=cr["header"] or "",
                summary=cr["summary"] or "",
                raw_text=cr["raw_text"] or "",
                section=cr["section"] or "",
                subsection=cr["subsection"],
                suggested_verdict=cr["suggested_verdict"] or "Correct / In Order",
                analysis_note=cr["analysis_note"] or "",
                user_verdict=cr["user_verdict"],
                user_remarks=cr["user_remarks"] or "",
            ))

        result = AnalysisResult(
            lc_type=meta.get("lc_type") or "Draft LC",
            dc_number=meta.get("dc_number") or None,
            source_filename=meta.get("source_filename") or "",
            full_text=meta.get("full_text") or "",
            clauses=clauses,
        )

        return result, meta
    finally:
        conn.close()


def search_analyses(
    lc_no: str = "",
    issuer: str = "",
    amount: str = "",
    beneficiary: str = "",
    general_query: str = "",
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Searches saved analysis records matching any/all provided criteria:
    - lc_no: partial or exact match on documentary credit number
    - issuer: partial match on applicant bank name or issuing bank name
    - amount: match on amount text or numeric amount
    - beneficiary: partial match on beneficiary name
    - general_query: broad search across all metadata and document text
    """
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        conditions = []
        params: List[Any] = []

        if lc_no.strip():
            conditions.append("dc_number LIKE ?")
            params.append(f"%{lc_no.strip()}%")

        if issuer.strip():
            conditions.append("(applicant_bank_name LIKE ? OR issuer_name LIKE ?)")
            params.extend([f"%{issuer.strip()}%", f"%{issuer.strip()}%"])

        if beneficiary.strip():
            conditions.append("beneficiary_name LIKE ?")
            params.append(f"%{beneficiary.strip()}%")

        if amount.strip():
            amt_clean = amount.strip().replace(",", "")
            try:
                num_val = float(amt_clean)
                conditions.append("(amount_num = ? OR amount_text LIKE ?)")
                params.extend([num_val, f"%{amount.strip()}%"])
            except ValueError:
                conditions.append("amount_text LIKE ?")
                params.append(f"%{amount.strip()}%")

        if general_query.strip():
            q = f"%{general_query.strip()}%"
            conditions.append("""
                (dc_number LIKE ? OR applicant_bank_name LIKE ? OR issuer_name LIKE ? OR beneficiary_name LIKE ? 
                 OR applicant_name LIKE ? OR amount_text LIKE ? OR source_filename LIKE ? 
                 OR full_text LIKE ?)
            """)
            params.extend([q, q, q, q, q, q, q, q])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT id, dc_number, lc_type, source_filename, issuer_name,
                   applicant_bank_name, applicant_name, beneficiary_name,
                   currency, amount_text, amount_num, issue_date, expiry_date,
                   shipment_date, status, total_points, amendment_count,
                   clarification_count, correct_count, created_at, updated_at
            FROM lc_records
            {where_clause}
            ORDER BY updated_at DESC
        """

        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_analyses(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns all saved analyses ordered from newest to oldest."""
    return search_analyses(db_path=db_path)


def delete_analysis(record_id: int, db_path: Optional[str] = None) -> bool:
    """Deletes an analysis record and its clauses by ID."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            cur = conn.execute("DELETE FROM lc_records WHERE id = ?", (record_id,))
            return cur.rowcount > 0
    finally:
        conn.close()
