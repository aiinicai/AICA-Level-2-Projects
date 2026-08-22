"""
database.py
-----------
Simple JSON-file "database" for invoices. No external DB engine is used so
that the application works fully offline and the data file can be copied /
backed up like any ordinary file.

Storage layout (database/invoices.json):
{
    "invoices": {
        "LC/26-27/Aug/01": { ... full invoice record ... },
        "LC/26-27/Aug/02": { ... },
        ...
    }
}

Keying by invoice number gives O(1) lookup/update/delete and also guards
against accidentally saving two invoices with the same number.
"""

import json
import os
import shutil
from datetime import datetime

from app import config


def ensure_folders():
    """Create /database and /invoices_pdf if they don't exist yet."""
    os.makedirs(config.DATABASE_DIR, exist_ok=True)
    os.makedirs(config.INVOICES_PDF_DIR, exist_ok=True)


def _empty_db():
    return {"invoices": {}}


def load_db() -> dict:
    """Load the JSON database, auto-creating it (with an empty structure)
    if it does not exist yet, and repairing it if the file is corrupt."""
    ensure_folders()
    if not os.path.exists(config.DATABASE_FILE):
        db = _empty_db()
        save_db(db)
        return db

    try:
        with open(config.DATABASE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "invoices" not in data:
            raise ValueError("Unexpected database structure")
        return data
    except (json.JSONDecodeError, ValueError, OSError):
        # Back up the corrupt file so no data is silently lost, then start
        # fresh with an empty database.
        if os.path.exists(config.DATABASE_FILE):
            backup_name = config.DATABASE_FILE + f".corrupt-{int(datetime.now().timestamp())}.bak"
            try:
                shutil.copy2(config.DATABASE_FILE, backup_name)
            except OSError:
                pass
        db = _empty_db()
        save_db(db)
        return db


def save_db(db: dict):
    """Atomically write the database dict to disk."""
    ensure_folders()
    tmp_path = config.DATABASE_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, config.DATABASE_FILE)


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------
def get_all_invoice_numbers() -> list:
    db = load_db()
    return list(db["invoices"].keys())


def get_all_invoices() -> list:
    """Return all invoice records, most recently updated first."""
    db = load_db()
    records = list(db["invoices"].values())
    records.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
    return records


def get_invoice(invoice_number: str):
    db = load_db()
    return db["invoices"].get(invoice_number)


def save_invoice(invoice: dict, overwrite: bool = True) -> dict:
    """
    Insert or update an invoice record. `invoice` must contain
    'invoice_number'. Returns the saved record (with timestamps set).
    """
    if not invoice.get("invoice_number"):
        raise ValueError("invoice_number is required to save an invoice")

    db = load_db()
    number = invoice["invoice_number"].strip()

    now = datetime.now().isoformat(timespec="seconds")
    existing = db["invoices"].get(number)

    if existing and not overwrite:
        raise ValueError(f"Invoice {number} already exists")

    invoice["created_at"] = existing["created_at"] if existing else now
    invoice["updated_at"] = now
    invoice["invoice_number"] = number

    db["invoices"][number] = invoice
    save_db(db)
    return invoice


def delete_invoice(invoice_number: str) -> bool:
    db = load_db()
    if invoice_number in db["invoices"]:
        del db["invoices"][invoice_number]
        save_db(db)
        return True
    return False


def invoice_number_exists(invoice_number: str) -> bool:
    db = load_db()
    return invoice_number.strip() in db["invoices"]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
def search_invoices(query: str = "", date_from: str = "", date_to: str = "") -> list:
    """
    Search invoices by (case-insensitive) substring match against invoice
    number or customer name, optionally narrowed by an invoice-date range
    (both bounds are 'YYYY-MM-DD' strings, inclusive).
    """
    records = get_all_invoices()
    query = (query or "").strip().lower()

    def matches(rec):
        if query:
            haystack = " ".join([
                rec.get("invoice_number", ""),
                rec.get("customer", {}).get("name", ""),
                rec.get("customer", {}).get("gstin", ""),
                rec.get("customer", {}).get("mobile", ""),
            ]).lower()
            if query not in haystack:
                return False
        inv_date = rec.get("invoice_date", "")
        if date_from and inv_date < date_from:
            return False
        if date_to and inv_date > date_to:
            return False
        return True

    return [r for r in records if matches(r)]
