"""Verification and merging of rule-based and LLM candidates.

Anti-hallucination controls:
  * every LLM quote must be found in the document (exact or fuzzy >= 0.85) — otherwise the
    value is marked UNVERIFIED and its confidence is cut;
  * the value must be supported by its own quote (amount/date/number present in the quote);
  * rule and LLM values that agree raise confidence; disagreements are CONFLICTS for review.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any, Optional

from .rules import Candidate, Evidence
from .schema import FIELD_MAP
from .textnum import find_amounts, find_dates, find_durations, find_percents, normalise, words_to_number


@dataclass
class FieldResult:
    key: str
    label: str
    group: str
    value: Any = None
    confidence: float = 0.0
    status: str = "MISSING"         # AGREED | RULE | AI_VERIFIED | AI_UNVERIFIED | CONFLICT | DERIVED | MISSING | USER
    method: str = ""
    page: Optional[int] = None
    quote: str = ""
    note: str = ""
    boxes: list = field(default_factory=list)
    alternatives: list = field(default_factory=list)
    essential: bool = False
    ind_as_ref: str = ""
    type: str = "text"


def verify_quote(quote: str, pages: list[tuple[int, str]], claimed_page: Optional[int] = None) -> tuple[bool, Optional[int], float]:
    q = normalise(quote or "")
    if len(q) < 6:
        return False, None, 0.0
    order = sorted(pages, key=lambda p: 0 if p[0] == claimed_page else 1)
    best = (False, None, 0.0)
    for no, text in order:
        t = normalise(text)
        if q in t:
            return True, no, 1.0
        # fuzzy: locate the longest common block and score a window around it
        sm = SequenceMatcher(None, t, q, autojunk=False)
        m = sm.find_longest_match(0, len(t), 0, len(q))
        if m.size < 8:
            continue
        start = max(0, m.a - m.b)
        window = t[start: start + len(q) + 20]
        ratio = SequenceMatcher(None, window, q, autojunk=False).ratio()
        if ratio > best[2]:
            best = (ratio >= 0.85, no, ratio)
    return best


def value_supported(ftype: str, value: Any, quote: str) -> Optional[bool]:
    if value in (None, "") or not quote:
        return None
    try:
        if ftype == "amount":
            v = Decimal(str(value))
            vals = {a.value for a in find_amounts(quote)}
            nums = {Decimal(x.replace(",", "")) for x in re.findall(r"\d[\d,]*(?:\.\d+)?", quote) if x.replace(",", "")}
            w = words_to_number(quote)
            return v in vals or v in nums or (w is not None and w == v)
        if ftype == "date":
            d = date.fromisoformat(str(value)[:10])
            return any(f.value == d for f in find_dates(quote))
        if ftype == "percent":
            v = Decimal(str(value))
            return any(p[0] == v for p in find_percents(quote)) or str(value) in quote
        if ftype == "int":
            v = int(Decimal(str(value)))
            if any(d[0] == v for d in find_durations(quote)):
                return True
            return str(v) in re.findall(r"\d+", quote) or (words_to_number(quote) == v)
    except (InvalidOperation, ValueError):
        return False
    return None


def _norm_value(ftype: str, v: Any) -> Any:
    if v is None or v == "":
        return None
    try:
        if ftype in ("amount", "percent", "number"):
            s = str(v).replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").replace("%", "").strip()
            d = Decimal(s)
            return format(d.normalize(), "f")
        if ftype == "int":
            return int(Decimal(str(v).replace(",", "")))
        if ftype == "date":
            return date.fromisoformat(str(v)[:10]).isoformat()
        if ftype == "bool":
            if isinstance(v, bool):
                return v
            return str(v).strip().lower() in ("true", "yes", "y", "1")
        if ftype == "choice":
            return str(v).strip().upper().replace(" ", "_").replace("-", "_") if FIELD_MAP else v
    except (InvalidOperation, ValueError):
        return None
    return str(v).strip()


def _same(ftype: str, a: Any, b: Any) -> bool:
    if a is None or b is None:
        return False
    if ftype in ("amount", "percent", "number"):
        try:
            return Decimal(str(a)) == Decimal(str(b))
        except InvalidOperation:
            return False
    if ftype == "text":
        na, nb = normalise(str(a)), normalise(str(b))
        return na == nb or na in nb or nb in na or SequenceMatcher(None, na, nb).ratio() > 0.85
    return a == b


def merge_field(key: str, rule_cands: list[Candidate], llm_item: Optional[dict], pages: list[tuple[int, str]],
                provider: str = "") -> FieldResult:
    fd = FIELD_MAP[key]
    ftype = fd.type
    res = FieldResult(key, fd.label, fd.group, essential=fd.essential, ind_as_ref=fd.ind_as_ref, type=ftype)
    rbest = sorted(rule_cands, key=lambda c: -c.confidence)[0] if rule_cands else None
    if ftype == "choice" and rbest:
        rbest_val = rbest.value
    else:
        rbest_val = _norm_value(ftype, rbest.value) if rbest else None
    lval = None
    lquote = ""
    lpage = None
    lconf = 0.0
    verified = False
    if llm_item and llm_item.get("value") not in (None, "", "null", "None"):
        lval = _norm_value(ftype, llm_item.get("value"))
        if ftype == "choice" and lval and fd.choices:
            match = [c for c in fd.choices if c.upper().replace(" ", "_") == str(lval)]
            lval = match[0] if match else (lval if str(lval).title() not in fd.choices else str(lval).title())
            if lval not in fd.choices:
                cands = [c for c in fd.choices if c.lower() == str(llm_item.get("value")).lower()]
                lval = cands[0] if cands else None
        lquote = (llm_item.get("quote") or "").strip()
        try:
            lpage = int(llm_item.get("page")) if llm_item.get("page") not in (None, "") else None
        except (TypeError, ValueError):
            lpage = None
        try:
            lconf = float(llm_item.get("confidence") or 0.6)
        except (TypeError, ValueError):
            lconf = 0.6
        ok, vpage, ratio = verify_quote(lquote, pages, lpage)
        verified = ok
        if ok:
            lpage = vpage
        sup = value_supported(ftype, lval, lquote)
        if sup is False:
            lconf *= 0.6
        if not ok:
            lconf = min(lconf, 0.35)
    if rbest and lval is not None:
        if _same(ftype, rbest_val, lval):
            res.value, res.status = rbest_val, "AGREED"
            res.confidence = min(0.99, max(rbest.confidence, lconf) + 0.08)
            res.method = f"{rbest.method} + llm:{provider}"
            ev = rbest.evidence
            res.page, res.quote = (ev.page, ev.quote) if ev else (lpage, lquote)
            res.note = rbest.note
        else:
            use_llm = verified and lconf > rbest.confidence + 0.1
            res.value = lval if use_llm else rbest_val
            res.status = "CONFLICT"
            res.confidence = min(rbest.confidence, max(lconf, 0.3))
            res.method = f"llm:{provider}" if use_llm else rbest.method
            ev = rbest.evidence
            res.page, res.quote = (lpage, lquote) if use_llm else ((ev.page, ev.quote) if ev else (None, ""))
            res.alternatives.append({"value": rbest_val if use_llm else lval, "method": rbest.method if use_llm else f"llm:{provider}",
                                     "quote": (ev.quote if ev else "") if use_llm else lquote,
                                     "page": (ev.page if ev else None) if use_llm else lpage, "verified": True if use_llm else verified})
            res.note = "Rule engine and AI disagree — select the correct value."
    elif rbest:
        res.value = rbest_val
        res.status = "DERIVED" if rbest.method == "derived" else "RULE"
        res.confidence = rbest.confidence
        res.method = rbest.method
        if rbest.evidence:
            res.page, res.quote = rbest.evidence.page, rbest.evidence.quote
        res.note = rbest.note
    elif lval is not None:
        res.value = lval
        res.status = "AI_VERIFIED" if verified else "AI_UNVERIFIED"
        res.confidence = lconf
        res.method = f"llm:{provider}"
        res.page, res.quote = lpage, lquote
        if not verified:
            res.note = "AI value could not be matched to the document text — treat as unverified."
    # other rule alternatives
    for c in rule_cands:
        v = c.value if ftype == "choice" else _norm_value(ftype, c.value)
        if v is not None and not _same(ftype, v, res.value) and all(not _same(ftype, v, a["value"]) for a in res.alternatives):
            res.alternatives.append({"value": v, "method": c.method, "quote": c.evidence.quote if c.evidence else "",
                                     "page": c.evidence.page if c.evidence else None, "verified": True})
    res.confidence = round(float(res.confidence), 2)
    return res
