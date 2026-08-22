"""
Persistent narration-pattern rules for Bank Statement import.

Bank narrations are messy free text ("NEFT-HDFC0001234-VENDOR NAME-CHQ123"),
so exact/fuzzy name matching against Tally ledgers often fails. This lets the
firm build up a small set of "if narration contains X, it's ledger Y" rules
that persist across imports -- once a recurring counterparty or a fixed
narration like "Bank Charges" has been mapped once, every future statement
auto-categorizes it instead of asking again.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "tally_import_data"
RULES_FILE = DATA_DIR / "bank_narration_rules.json"


def _ensure_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not RULES_FILE.exists():
        RULES_FILE.write_text(json.dumps([], indent=2), encoding="utf-8")


def load_rules() -> list[dict]:
    """[{'contains': 'text to match in narration', 'ledger': 'Tally ledger name'}, ...]
    Checked in list order; first match wins, so more specific rules should be
    listed first if two patterns could both match the same narration."""
    _ensure_file()
    try:
        return json.loads(RULES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_rules(rules: list[dict]) -> None:
    _ensure_file()
    RULES_FILE.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")


def add_rule(contains: str, ledger: str) -> None:
    contains = contains.strip()
    ledger = ledger.strip()
    if not contains or not ledger:
        return
    rules = load_rules()
    # replace an existing rule for the same pattern rather than duplicating
    rules = [r for r in rules if r.get("contains", "").strip().lower() != contains.lower()]
    rules.insert(0, {"contains": contains, "ledger": ledger})
    save_rules(rules)


def match(narration: str) -> str | None:
    if not narration:
        return None
    text = narration.lower()
    for rule in load_rules():
        pattern = (rule.get("contains") or "").strip().lower()
        if pattern and pattern in text:
            return rule.get("ledger")
    return None
