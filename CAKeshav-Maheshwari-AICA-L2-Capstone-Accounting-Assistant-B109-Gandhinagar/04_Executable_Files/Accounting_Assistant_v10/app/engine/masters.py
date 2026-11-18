"""Read-side helpers over the cached Tally masters of one company."""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import MasterCache

PRIMARY_GROUPS = {"Sundry Creditors", "Sundry Debtors", "Duties & Taxes", "Direct Expenses", "Indirect Expenses",
                  "Purchase Accounts", "Fixed Assets", "Current Assets", "Current Liabilities", "Bank Accounts",
                  "Cash-in-Hand", "Provisions", "Loans & Advances (Asset)", "Capital Account", "Sales Accounts",
                  "Direct Incomes", "Indirect Incomes", "Branch / Divisions", "Loans (Liability)",
                  "Investments", "Misc. Expenses (ASSET)", "Reserves & Surplus", "Secured Loans",
                  "Unsecured Loans", "Stock-in-Hand", "Deposits (Asset)", "Bank OD A/c", "Suspense A/c"}


@dataclass
class Masters:
    ledgers: dict[str, dict] = field(default_factory=dict)     # name -> data (+ _group, _primary)
    stock_items: dict[str, dict] = field(default_factory=dict)
    voucher_types: dict[str, dict] = field(default_factory=dict)
    godowns: list[str] = field(default_factory=list)

    # ---- classification
    def under(self, name: str, primary: str) -> bool:
        return self.ledgers.get(name, {}).get("_primary") == primary

    def names_under(self, *primaries: str) -> list[str]:
        return sorted(n for n, d in self.ledgers.items() if d.get("_primary") in primaries)

    def party_by_gstin(self, gstin: str) -> str:
        for n, d in self.ledgers.items():
            if gstin and d.get("_gstin", "").upper() == gstin.upper():
                return n
        return ""

    def fuzzy(self, name: str, pool: list[str] | None = None, cutoff: float = 0.72) -> tuple[str, float]:
        """Closest name in the pool. Results are remembered, and only candidates sharing a few letters with
        the name are compared in full (a full comparison against thousands of ledgers was slow)."""
        if not name:
            return "", 0.0
        pool = pool if pool is not None else list(self.ledgers)
        cache = self.__dict__.setdefault("_fuzzy", {})
        key = (name, cutoff, len(pool), pool[0] if pool else "")
        if key in cache:
            return cache[key]
        norm = lambda s: re.sub(r"\b(pvt|private|ltd|limited|llp|co|company|the|m/s)\b|[^a-z0-9]", "", s.lower())
        target = norm(name)
        grams = {target[i:i + 3] for i in range(max(1, len(target) - 2))}
        normed = self.__dict__.setdefault("_normed", {})
        best, score = "", 0.0
        sm = difflib.SequenceMatcher(None, "", target)          # target cached as seq2
        for cand in pool:
            nc = normed.get(cand)
            if nc is None:
                nc = normed[cand] = norm(cand)
            if grams and len(target) > 3 and not any(g in nc for g in grams):
                continue
            sm.set_seq1(nc)
            if sm.real_quick_ratio() <= score or sm.quick_ratio() <= score:
                continue
            r = sm.ratio()
            if r > score:
                best, score = cand, r
        res = (best, score) if score >= cutoff else ("", score)
        cache[key] = res
        return res

    def gst_ledger(self, head: str, rate=None, rcm: bool = False, output: bool = False) -> str:
        """head: cgst|sgst|igst|cess. Prefer names carrying the rate and Input/Output/RCM wording."""
        duty = {"cgst": "Central Tax", "sgst": "State Tax", "igst": "Integrated Tax", "cess": "Cess"}[head]
        alias = {"cgst": r"cgst|central", "sgst": r"sgst|utgst|state|ut\s*tax", "igst": r"igst|integrated",
                 "cess": r"cess"}[head]
        cands = [n for n, d in self.ledgers.items() if d.get("_primary") == "Duties & Taxes" and
                 (d.get("GSTDUTYHEAD") == duty or re.search(alias, n, re.I))]

        def score(n: str) -> float:
            s, low = 0.0, n.lower()
            if rcm == bool(re.search(r"rcm|reverse", low)):
                s += 3
            want_out = output or False
            if want_out and re.search(r"output|payable", low):
                s += 2
            if not want_out and re.search(r"input|itc|receivable", low):
                s += 2
            if not want_out and re.search(r"output|payable", low):
                s -= 3
            if rate is not None:
                r = f"{rate.normalize():f}" if hasattr(rate, "normalize") else str(rate)
                if re.search(rf"(?<![\d.]){re.escape(r)}\s*%", low):
                    s += 1.5
                elif re.search(r"\d+(\.\d+)?\s*%", low):
                    s -= 1
            return s
        return max(cands, key=score) if cands else ""

    def find(self, pattern: str, primary: str | None = None) -> str:
        for n, d in sorted(self.ledgers.items()):
            if re.search(pattern, n, re.I) and (primary is None or d.get("_primary") == primary):
                return n
        return ""


def load(session: Session, company_id: str) -> Masters:
    rows = session.scalars(select(MasterCache).where(MasterCache.company_id == company_id)).all()
    groups = {r.name: r.parent for r in rows if r.kind == "group"}

    def primary_of(group: str) -> str:
        seen = set()
        g = group
        while g and g not in PRIMARY_GROUPS and g in groups and g not in seen:
            seen.add(g)
            nxt = groups.get(g, "")
            if not nxt or nxt.lower() in ("primary", "&#4; primary"):
                break
            g = nxt
        return g

    m = Masters()
    for r in rows:
        if r.kind == "ledger":
            d = dict(r.data or {})
            d["_group"] = r.parent
            d["_primary"] = primary_of(r.parent)
            m.ledgers[r.name] = d
        elif r.kind == "stock_item":
            m.stock_items[r.name] = dict(r.data or {}, _parent=r.parent)
        elif r.kind == "voucher_type":
            m.voucher_types[r.name] = dict(r.data or {}, _parent=r.parent)
        elif r.kind == "godown":
            m.godowns.append(r.name)
    return m
