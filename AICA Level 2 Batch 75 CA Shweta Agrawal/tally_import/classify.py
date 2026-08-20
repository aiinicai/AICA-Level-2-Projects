"""
Classifies Tally ledgers into the "debit side" categories relevant to a
GSTR-2B Purchase voucher -- Purchase / Direct Expense / Indirect Expense /
Capital Asset -- by walking each ledger's PARENT up the account-group tree
until it reaches one of Tally's reserved top-level groups.

Also holds the persistent "vendor -> expense/purchase/capital-asset ledger"
learning table: once a row for a given vendor is posted with a chosen ledger,
that choice is remembered and offered as the default next time the same
vendor shows up (e.g. every Interglobe Aviation row defaults to Travelling
Expense after the first one is posted that way).
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "tally_import_data"
VENDOR_EXPENSE_FILE = DATA_DIR / "vendor_expense_mapping.json"

# Tally reserved top-level group name -> category label surfaced in the UI
RESERVED_TO_CATEGORY = {
    "Purchase Accounts": "Purchase",
    "Direct Expenses": "Direct Expense",
    "Indirect Expenses": "Indirect Expense",
    "Fixed Assets": "Capital Asset",
    "Duties & Taxes": "Duties & Taxes",
}


def classify_ledgers(ledgers: list[dict], groups: list[dict]) -> list[dict]:
    """Returns ledgers with an added 'category' key (one of RESERVED_TO_CATEGORY's
    values, or None if the ledger isn't under any of those four groups)."""
    parent_of = {g["name"]: g["parent"] for g in groups}
    reserved_of = {g["name"]: g["reserved_name"] for g in groups}

    def walk(group_name: str, seen: set) -> str | None:
        if not group_name or group_name in seen:
            return None
        seen.add(group_name)
        reserved = reserved_of.get(group_name, "")
        if reserved in RESERVED_TO_CATEGORY:
            return RESERVED_TO_CATEGORY[reserved]
        if group_name in RESERVED_TO_CATEGORY:  # the group itself is a reserved name
            return RESERVED_TO_CATEGORY[group_name]
        return walk(parent_of.get(group_name, ""), seen)

    out = []
    for led in ledgers:
        category = walk(led.get("parent", ""), set())
        out.append({**led, "category": category})
    return out


# Common Indirect Expense heads offered in the picker even before the firm has
# created them in Tally -- picking one that doesn't exist yet just means it needs
# to be created in Tally first (see the LedgerNotFound-style flow), same as any
# other unmatched ledger. Saves re-typing the same dozen categories for every firm.
STARTER_INDIRECT_EXPENSES = [
    "Travelling Expense", "Conveyance", "Freight & Cartage", "Repairs & Maintenance",
    "Printing & Stationery", "Telephone Expenses", "Office Expenses", "Professional Fees",
    "Rent", "Bank Charges", "Insurance", "Legal & Professional Charges",
    "Business Promotion", "Staff Welfare", "Internet & Communication Expenses",
]


def expense_side_ledgers(classified_ledgers: list[dict]) -> list[dict]:
    """The subset of classified ledgers usable on the debit side of a Purchase
    voucher, plus the starter Indirect Expense heads for names not yet in Tally."""
    out = [l for l in classified_ledgers if l.get("category")]
    existing_names = {l["name"] for l in out}
    for name in STARTER_INDIRECT_EXPENSES:
        if name not in existing_names:
            out.append({"name": name, "category": "Indirect Expense", "exists_in_tally": False})
    for l in out:
        l.setdefault("exists_in_tally", True)
    return out


# ── vendor -> expense ledger learning table ─────────────────────────────────

def _ensure_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not VENDOR_EXPENSE_FILE.exists():
        VENDOR_EXPENSE_FILE.write_text(json.dumps({}, indent=2), encoding="utf-8")


def load_vendor_expense_map() -> dict[str, str]:
    """{'vendor ledger name': 'expense/purchase/capital-asset ledger name'}"""
    _ensure_file()
    try:
        return json.loads(VENDOR_EXPENSE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_vendor_expense_map(mapping: dict[str, str]) -> None:
    _ensure_file()
    VENDOR_EXPENSE_FILE.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")


def remember_vendor_expense(vendor_ledger: str, expense_ledger: str) -> None:
    if not vendor_ledger or not expense_ledger:
        return
    m = load_vendor_expense_map()
    m[vendor_ledger.strip()] = expense_ledger.strip()
    save_vendor_expense_map(m)


def suggest_expense_ledger(vendor_ledger: str) -> str | None:
    if not vendor_ledger:
        return None
    return load_vendor_expense_map().get(vendor_ledger.strip())
