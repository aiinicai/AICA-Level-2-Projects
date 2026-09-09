"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
CII Master Module
Author: Senior Python Developer & Tax-Audit Software Architect
"""

import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from database import get_db_connection, log_audit


class CIINotFoundError(Exception):
    """Raised when Cost Inflation Index for a specified Financial Year is missing."""
    pass


def normalize_fy(fy_str: str) -> str:
    """
    Normalizes any FY string into standard 'YYYY-YY' format.
    Examples:
      'FY 2010-11' -> '2010-11'
      '2010-2011'  -> '2010-11'
      '2010-11'    -> '2010-11'
    """
    if not fy_str:
        return ""
    cleaned = fy_str.strip().upper().replace("FY", "").strip()
    match = re.match(r"^(\d{4})[-/](\d{2,4})$", cleaned)
    if match:
        start_year = match.group(1)
        end_year = match.group(2)
        if len(end_year) == 4:
            end_year = end_year[2:]
        return f"{start_year}-{end_year}"
    return cleaned


def date_to_fy(d: Any) -> str:
    """
    Converts a date object or date string into Indian Financial Year (YYYY-YY).
    In India:
      April 1, YYYY to March 31, YYYY+1 belongs to FY YYYY-(YY+1).
    """
    if isinstance(d, str):
        # Support formats: DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                d = datetime.strptime(d.strip(), fmt).date()
                break
            except ValueError:
                continue
        if isinstance(d, str):
            raise ValueError(f"Invalid date string format: '{d}'. Expected DD/MM/YYYY or YYYY-MM-DD.")

    if not isinstance(d, (date, datetime)):
        raise ValueError(f"Expected date or datetime object, got {type(d)}")

    year = d.year
    month = d.month

    if month >= 4:
        start_year = year
        end_year = (year + 1) % 100
    else:
        start_year = year - 1
        end_year = year % 100

    return f"{start_year}-{end_year:02d}"


def fy_to_ay(fy_str: str) -> str:
    """
    Converts Financial Year (e.g. '2024-25') to Assessment Year (e.g. '2025-26').
    """
    normalized = normalize_fy(fy_str)
    parts = normalized.split("-")
    if len(parts) == 2 and len(parts[0]) == 4:
        start_year = int(parts[0]) + 1
        end_year = (start_year + 1) % 100
        return f"{start_year}-{end_year:02d}"
    return fy_str


def get_all_cii(conn=None) -> List[Dict[str, Any]]:
    """Retrieves all CII records sorted by Financial Year ascending."""
    owns_conn = False
    if conn is None:
        conn = get_db_connection()
        owns_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT financial_year, cii_value, is_notified, notification_ref, updated_at FROM cii_master ORDER BY financial_year ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        if owns_conn:
            conn.close()


def get_cii_for_fy(fy_str: str, conn=None) -> int:
    """
    Fetches the CII value for a given Financial Year.
    Raises CIINotFoundError if the CII is not in the database.
    """
    normalized = normalize_fy(fy_str)
    owns_conn = False
    if conn is None:
        conn = get_db_connection()
        owns_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT cii_value FROM cii_master WHERE financial_year = ?", (normalized,))
        row = cursor.fetchone()
        if not row:
            raise CIINotFoundError(
                f"Cost Inflation Index (CII) for Financial Year '{normalized}' is not available in the CII Master. "
                f"Please update the CII Master before calculating indexed cost."
            )
        return int(row["cii_value"])
    finally:
        if owns_conn:
            conn.close()


def get_cii_for_date(d: Any, is_acquisition: bool = False, conn=None) -> Tuple[int, str]:
    """
    Returns (cii_value, fy_str) for a given date.
    For acquisition dates prior to 01-04-2001 (Section 55(2)(b)), the base FY 2001-02 CII (100) is returned.
    """
    if isinstance(d, str):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                d = datetime.strptime(d.strip(), fmt).date()
                break
            except ValueError:
                continue

    if is_acquisition and d < date(2001, 4, 1):
        # Grandfathered base year for pre-01/04/2001 acquisitions is FY 2001-02
        fy = "2001-02"
        cii = get_cii_for_fy(fy, conn=conn)
        return cii, fy

    fy = date_to_fy(d)
    cii = get_cii_for_fy(fy, conn=conn)
    return cii, fy


def add_or_update_cii(financial_year: str, cii_value: int, is_notified: int = 1, notification_ref: str = "", conn=None) -> None:
    """Adds a new CII record or updates an existing one."""
    normalized = normalize_fy(financial_year)
    if not normalized or len(normalized) != 7 or "-" not in normalized:
        raise ValueError(f"Invalid Financial Year format '{financial_year}'. Expected YYYY-YY (e.g. 2026-27).")
    if cii_value <= 0:
        raise ValueError("CII Value must be a positive integer.")

    owns_conn = False
    if conn is None:
        conn = get_db_connection()
        owns_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO cii_master (financial_year, cii_value, is_notified, notification_ref, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(financial_year) DO UPDATE SET
                cii_value = excluded.cii_value,
                is_notified = excluded.is_notified,
                notification_ref = excluded.notification_ref,
                updated_at = datetime('now')
            """,
            (normalized, cii_value, is_notified, notification_ref),
        )
        conn.commit()
        log_audit(
            action="UPDATE_CII",
            entity_type="CII_MASTER",
            entity_id=normalized,
            details=f"Set CII for FY {normalized} to {cii_value} (Notified={is_notified})",
            conn=conn,
        )
    finally:
        if owns_conn:
            conn.close()


def delete_cii(financial_year: str, conn=None) -> bool:
    """Deletes a CII record by Financial Year."""
    normalized = normalize_fy(financial_year)
    owns_conn = False
    if conn is None:
        conn = get_db_connection()
        owns_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cii_master WHERE financial_year = ?", (normalized,))
        rows_affected = cursor.rowcount
        conn.commit()
        if rows_affected > 0:
            log_audit(
                action="DELETE_CII",
                entity_type="CII_MASTER",
                entity_id=normalized,
                details=f"Deleted CII record for FY {normalized}",
                conn=conn,
            )
            return True
        return False
    finally:
        if owns_conn:
            conn.close()


def export_cii_to_excel(file_path: str, conn=None) -> None:
    """Exports the complete CII Master table to an Excel file (.xlsx)."""
    records = get_all_cii(conn=conn)
    df = pd.DataFrame(records)
    # Rename columns for clarity
    df = df.rename(columns={
        "financial_year": "Financial Year",
        "cii_value": "Cost Inflation Index (CII)",
        "is_notified": "Is Officially Notified (1=Yes, 0=No)",
        "notification_ref": "CBDT Notification Ref",
        "updated_at": "Last Updated"
    })
    df.to_excel(file_path, index=False, sheet_name="CII Master")


def import_cii_from_excel(file_path: str, conn=None) -> Tuple[int, List[str]]:
    """
    Imports CII records from an Excel file (.xlsx).
    Returns (count_imported, list_of_error_messages).
    """
    errors = []
    imported_count = 0

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return 0, [f"Failed to read Excel file: {str(e)}"]

    # Identify relevant columns
    fy_col = None
    cii_col = None
    notified_col = None
    ref_col = None

    for col in df.columns:
        c_lower = str(col).lower()
        if "financial" in c_lower or "fy" in c_lower or "year" in c_lower:
            fy_col = col
        elif "cii" in c_lower or "index" in c_lower or "value" in c_lower:
            cii_col = col
        elif "notif" in c_lower and "ref" not in c_lower:
            notified_col = col
        elif "ref" in c_lower:
            ref_col = col

    if not fy_col or not cii_col:
        return 0, [f"Could not identify 'Financial Year' and 'CII Value' columns in Excel. Found columns: {list(df.columns)}"]

    for idx, row in df.iterrows():
        raw_fy = str(row[fy_col]).strip()
        raw_cii = row[cii_col]

        if pd.isna(raw_fy) or pd.isna(raw_cii):
            continue

        try:
            norm_fy = normalize_fy(raw_fy)
            val_cii = int(float(raw_cii))
            is_notified = 1
            if notified_col and not pd.isna(row[notified_col]):
                is_notified = 1 if int(row[notified_col]) == 1 else 0
            ref_val = str(row[ref_col]) if (ref_col and not pd.isna(row[ref_col])) else "Imported via Excel"

            add_or_update_cii(norm_fy, val_cii, is_notified, ref_val, conn=conn)
            imported_count += 1
        except Exception as ex:
            errors.append(f"Row {idx + 2} ('{raw_fy}'): {str(ex)}")

    return imported_count, errors
