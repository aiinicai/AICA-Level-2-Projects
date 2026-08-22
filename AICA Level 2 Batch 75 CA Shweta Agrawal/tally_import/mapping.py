"""
Persistent, user-editable ledger mapping table.

Maps raw source names (bank contra description, GSTR-2B supplier name,
GSTR-1 recipient name) to exact Tally ledger names. Fuzzy-matches against
the live Tally ledger list first; falls back to whatever the user has saved
in the mapping table; never auto-creates a ledger in Tally.
"""
from __future__ import annotations

import json
from pathlib import Path

from rapidfuzz import fuzz, process

DATA_DIR = Path(__file__).resolve().parent.parent / "tally_import_data"
MAPPING_FILE = DATA_DIR / "ledger_mapping.json"

FUZZY_THRESHOLD = 85  # score out of 100; below this, treat as unmatched


def _ensure_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not MAPPING_FILE.exists():
        MAPPING_FILE.write_text(json.dumps({}, indent=2), encoding="utf-8")


def load_mapping() -> dict[str, str]:
    """{'raw source name': 'exact tally ledger name'}"""
    _ensure_file()
    try:
        return json.loads(MAPPING_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_mapping(mapping: dict[str, str]) -> None:
    _ensure_file()
    MAPPING_FILE.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")


def set_mapping(raw_name: str, ledger_name: str) -> None:
    mapping = load_mapping()
    mapping[raw_name.strip()] = ledger_name.strip()
    save_mapping(mapping)


def resolve(raw_name: str, tally_ledgers: list[str]) -> dict:
    """
    Resolve raw_name to a Tally ledger.
    Returns {'status': 'exact'|'saved'|'fuzzy'|'unmatched', 'ledger': str|None, 'score': int|None}
    Priority: saved mapping (if still a valid Tally ledger) > exact name match > fuzzy match.
    """
    raw = raw_name.strip()
    if not raw:
        return {"status": "unmatched", "ledger": None, "score": None}

    saved = load_mapping()
    if raw in saved and saved[raw] in tally_ledgers:
        return {"status": "saved", "ledger": saved[raw], "score": 100}

    if raw in tally_ledgers:
        return {"status": "exact", "ledger": raw, "score": 100}

    if not tally_ledgers:
        return {"status": "unmatched", "ledger": None, "score": None}

    match = process.extractOne(raw, tally_ledgers, scorer=fuzz.WRatio)
    if match and match[1] >= FUZZY_THRESHOLD:
        return {"status": "fuzzy", "ledger": match[0], "score": int(match[1])}

    best = match[0] if match else None
    best_score = int(match[1]) if match else None
    return {"status": "unmatched", "ledger": None, "score": best_score, "suggestion": best}
