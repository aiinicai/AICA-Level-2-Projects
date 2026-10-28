"""Configurable account mapping: TB account -> financial statement line.

Deterministic keyword rules (config/mapping_rules.json) + per-client overrides. Nothing is hidden:
every account carries a mapping method (rule / hint-default / override / unmapped) and the
user must review anything that was not mapped by an explicit rule or override.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .models import Account, load_json

_MAP = None


def mapping_config() -> dict:
    global _MAP
    if _MAP is None:
        _MAP = load_json("mapping_rules.json")
        _MAP["_lines_by_key"] = {l["key"]: l for l in _MAP["lines"]}
        for r in _MAP["rules"]:
            r["_re"] = re.compile(r["pattern"], re.I)
    return _MAP


def reload_config():
    global _MAP
    _MAP = None
    return mapping_config()


def fs_lines() -> dict:
    return mapping_config()["_lines_by_key"]


def normalise_name(name: str) -> str:
    s = (name or "").lower().replace("’", "'")
    s = re.sub(r"[\n\r\t]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalise_hint(hint: Optional[str]) -> Optional[str]:
    if not hint:
        return None
    h = hint.strip().lower()
    syn = mapping_config()["hint_synonyms"]
    for cls, words in syn.items():
        if h in words:
            return cls
    for cls, words in syn.items():          # loose containment, e.g. 'Current Asset - Bank'
        if any(w in h for w in words if len(w) > 4):
            return cls
    return None


@dataclass
class MappedAccount:
    account: Account
    line: str                       # fs line key
    method: str                     # rule | hint-default | override | unmapped
    rule_id: str = ""
    hint_class: Optional[str] = None
    flags: list = field(default_factory=list)   # human-readable review flags
    from_code: bool = False                     # class was inferred from the account-code convention, not given by the TB

    @property
    def statement(self) -> str:
        return fs_lines()[self.line]["statement"]

    @property
    def needs_review(self) -> bool:
        return self.method in ("hint-default", "unmapped") or bool(self.flags)


def infer_classes(accounts: list) -> dict:
    """Infer ASSET/LIABILITY/EQUITY/INCOME/EXPENSE from the first digit of numeric account codes - but ONLY when the
    balances in this TB confirm the convention (digit 1 mostly debit, 2-4 mostly credit, 5-9 mostly debit).
    Returns {account key: class}; empty if the TB has no usable code structure."""
    coded = [a for a in accounts if re.fullmatch(r"\d{3,}", (a.code or "").strip())]
    if len(accounts) < 8 or len(coded) < 0.8 * len(accounts):
        return {}
    exp = {"1": ("ASSET", 1), "2": ("LIABILITY", -1), "3": ("EQUITY", -1), "4": ("INCOME", -1)}
    for d in "56789":
        exp[d] = ("EXPENSE", 1)
    seen = {}
    for a in coded:
        d = a.code.strip()[0]
        if d in exp and abs(a.net) > 0.005:
            seen.setdefault(d, []).append(1 if a.net > 0 else -1)
    if "1" not in seen or not any(d in seen for d in "456"):
        return {}
    for d, signs in seen.items():
        ok = sum(1 for s in signs if s == exp[d][1]) / len(signs)
        if len(signs) >= 2 and ok < 0.7:
            return {}
    return {a.key(): exp[a.code.strip()[0]][0] for a in coded if a.code.strip()[0] in exp}


def map_account(acc: Account, overrides: Optional[dict] = None, inferred: Optional[str] = None) -> MappedAccount:
    cfg = mapping_config()
    overrides = overrides or {}
    hint_class = normalise_hint(acc.hint)
    from_code = False
    if hint_class is None and inferred:
        hint_class, from_code = inferred, True
    name = normalise_name(acc.name)
    ov = overrides.get(acc.key())
    if ov and ov in cfg["_lines_by_key"]:
        return MappedAccount(acc, ov, "override", "", hint_class)
    sign = "debit" if acc.net > 0 else ("credit" if acc.net < 0 else None)

    def first_rule(nm):
        for r in cfg["rules"]:
            types = r.get("types")
            if types and hint_class and hint_class not in types:
                continue
            if r.get("sign"):
                if hint_class is not None:
                    if not types:
                        continue          # sign-only rules are fallbacks for accounts without any classification
                elif sign != r["sign"]:
                    continue
            if r["_re"].search(nm):
                return r
        return None

    r = first_rule(name)
    if r:
        m = MappedAccount(acc, r["line"], "rule", r["id"], hint_class)
        m.from_code = from_code
        _consistency_flags(m)
        return m
    # a ledger named after a person/company (Tally 'Sundry Debtors' etc.): try the groups it sits under, nearest first
    for gname in reversed([x.strip() for x in (acc.group or "").split(">") if x.strip()]):
        r = first_rule(normalise_name(gname))
        if r:
            m = MappedAccount(acc, r["line"], "rule", r["id"], hint_class,
                              [f"The ledger name matched no rule; mapped from its source group '{gname}' - please confirm."])
            m.from_code = from_code
            _consistency_flags(m)
            return m
    if hint_class and hint_class in cfg["hint_defaults"]:
        m = MappedAccount(acc, cfg["hint_defaults"][hint_class], "hint-default", "", hint_class,
                          ["No keyword rule matched; placed in the default line for its " + ("account-code class." if from_code else "source classification.")])
        m.from_code = from_code
        _consistency_flags(m)
        return m
    return MappedAccount(acc, "UNMAPPED", "unmapped", "", None, ["No rule matched and the TB gives no classification."])


def _consistency_flags(m: MappedAccount) -> None:
    """Flag contradictions between the TB's own classification, the mapped line and the sign of the balance."""
    st = m.statement
    h = m.hint_class
    if h:
        src_stmt = "PL" if h in ("INCOME", "EXPENSE") else "BS"
        if st != src_stmt:
            src = "Account-code convention suggests " + h.lower() if m.from_code else f"TB classification '{m.account.hint}'"
            m.flags.append(f"{src} but the account is mapped to the {st} statement. Review.")
    income_lines = {"P_REV", "P_DIV", "P_INT_INC", "P_GAIN_REAL", "P_FV", "P_OTHER_INC"}
    if h == "EXPENSE" and m.line in income_lines and m.account.net < 0:
        m.flags.append("TB classification says Expense but the account is income in nature (credit balance) - mapped to income.")
    if h == "INCOME" and m.line in {"P_STAFF", "P_PROF", "P_BANK", "P_RENT", "P_MKT", "P_ENT", "P_DON", "P_FINES", "P_GEN", "P_FIN", "P_DEP"} and m.account.net < 0:
        m.flags.append("Expense-type account carries a credit balance (net credit) - check for reversals/sign errors.")
    # abnormal balances on balance-sheet accounts
    abn = {"A_CASH": "credit", "A_FIN_INV": "credit", "A_LOANS": "credit", "A_TRADE_REC": "credit", "A_PPE": "credit",
           "L_TRADE_PAY": "debit", "L_BORR": "debit", "E_CAPITAL": "debit"}
    side = "credit" if m.account.net < 0 else ("debit" if m.account.net > 0 else None)
    contra = re.search(r"accumulated|allowance|provision|impairment|depreciation|amortis", m.account.name, re.I)
    if m.line in abn and side == abn[m.line] and abs(m.account.net) > 0.5 and not contra:
        m.flags.append(f"Abnormal {side} balance for this type of account (e.g. overdrawn bank / negative investment) - check.")


def map_all(accounts: list, overrides: Optional[dict] = None) -> list:
    inf = infer_classes(accounts)
    return [map_account(a, overrides, inf.get(a.key())) for a in accounts]


def line_options(statement: Optional[str] = None) -> list:
    """List of (key, label) for the mapping combo boxes."""
    return [(l["key"], l["label"]) for l in sorted(mapping_config()["lines"], key=lambda x: x["order"])
            if statement is None or l["statement"] == statement]
