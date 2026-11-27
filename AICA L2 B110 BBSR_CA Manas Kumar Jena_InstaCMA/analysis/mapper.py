"""
Mapper: classifies each line of the client's statement into a CMA head.

Order of preference
  1. Learned mappings (labels the user remapped earlier, saved on this PC)  -> 100
  2. Keyword taxonomy (config.constants.KEYWORD_RULES), statement-aware     -> 85-95
  3. Fuzzy match on the keyword phrases (RapidFuzz if installed, else difflib) -> 60-80
Lines that are totals / headings are marked 'ignore'.
"""
import difflib
import json
import os
import re

from config.constants import (KEYWORD_RULES, TOTAL_MARKERS, PL_KEYS, LIAB_KEYS, ASSET_KEYS)
from config.settings import SETTINGS_DIR

try:  # optional, faster and better fuzzy matching
    from rapidfuzz import fuzz as _rf_fuzz
except Exception:  # pragma: no cover
    _rf_fuzz = None

LEARNED_FILE = os.path.join(SETTINGS_DIR, "learned_mappings.json")

PL_ALLOWED = set(PL_KEYS)
BS_ALLOWED = set(LIAB_KEYS + ASSET_KEYS + ["drawings", "capital_introduced"])

# heads that mean something different on each statement
PL_TO_BS = {"closing_stock": "stock"}
BS_TO_PL = {"stock": "closing_stock"}

_PREFIX = re.compile(r"^(to|by|less|add|less:|add:|\(?[ivx]+\)|\(?[a-z]\)|\d+[\.\)])\s+", re.I)


def normalise(label):
    s = str(label or "").strip().lower()
    s = s.replace("&amp;", "&").replace("’", "'")
    s = re.sub(r"\s+", " ", s)
    for _ in range(3):
        s2 = _PREFIX.sub("", s)
        if s2 == s:
            break
        s = s2
    s = s.strip(" :-.,")
    return s


def _load_learned():
    try:
        with open(LEARNED_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def learn(label, statement, head):
    """Remember a manual remap for next time (stored on this PC only)."""
    data = _load_learned()
    data["%s|%s" % (statement, normalise(label))] = head
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    with open(LEARNED_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)


def _is_total(norm):
    if not norm:
        return True
    for m in TOTAL_MARKERS:
        if norm == m:
            return True
        if " " in m and (norm.startswith(m + " ") or norm.startswith(m + ":")):
            return True
        if m in ("total", "grand total", "sub total", "subtotal") and (
                norm.startswith(m + " ") or norm.endswith(" " + m)):
            return True
    return False


def _fix_statement(head, statement):
    """Translate a head to its meaning on the given statement ('' if not applicable)."""
    if statement == "BS" and head not in BS_ALLOWED:
        return PL_TO_BS.get(head, "")
    if statement == "PL" and head not in PL_ALLOWED:
        return BS_TO_PL.get(head, "")
    return head


def map_label(label, statement="PL", learned=None):
    """Return (head, confidence, reason)."""
    norm = normalise(label)
    if learned is None:
        learned = _load_learned()
    key = "%s|%s" % (statement, norm)
    if key in learned:
        return learned[key], 100, "learned"
    if re.match(r"^(net profit|profit for the year|excess of income over expenditure)\b", norm):
        return ("_reported_net_profit" if statement == "PL" else "ignore"), 90, "net profit line"
    if norm in ("grand total", "total") or norm.startswith("total "):
        return "ignore", 95, "total line"
    if _is_total(norm):
        return "ignore", 85, "heading / total"
    if statement == "BS" and re.search(r"\bdepreciation\b", norm):
        return "ignore", 80, "depreciation shown under fixed assets"
    if "certified" in norm:
        return "ignore", 90, "certification note"
    if statement == "BS" and re.search(r"\bnet profit\b|\bopening balance\b|\bopening capital\b|\bprofit for the year\b", norm):
        return "ignore", 80, "capital account movement"

    allowed = BS_ALLOWED if statement == "BS" else PL_ALLOWED
    for head, words in KEYWORD_RULES:
        h = _fix_statement(head, statement)
        if h not in allowed:
            continue
        for w in words:
            if re.search(r"(^|[^a-z])" + re.escape(w) + r"(s|es)?($|[^a-z])", norm):
                conf = 95 if norm == w else 88
                return h, conf, "keyword '%s'" % w

    # fuzzy fallback
    best, best_head = 0, ""
    for head, words in KEYWORD_RULES:
        if _fix_statement(head, statement) not in allowed:
            continue
        for w in words:
            if _rf_fuzz is not None:
                sc = _rf_fuzz.token_set_ratio(norm, w)
            else:
                sc = difflib.SequenceMatcher(None, norm, w).ratio() * 100
            if sc > best:
                best, best_head = sc, head
    if best >= 75:
        h = _fix_statement(best_head, statement)
        if h:
            return h, int(best * 0.8), "fuzzy %.0f%%" % best
    default = "misc_exp" if statement == "PL" else ""
    return default, 30 if default else 0, "no match - please review"


def map_lines(lines):
    learned = _load_learned()
    for ln in lines:
        if ln.head and ln.confidence >= 90:
            continue
        head, conf, why = map_label(ln.label, ln.statement, learned)
        ln.head, ln.confidence, ln.note = head, conf, why
    return lines
