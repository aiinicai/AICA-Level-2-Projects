"""Supplier layout memory: learn where each supplier prints invoice no., date and amounts, so the next invoice
from the same supplier is read offline (no Gemini) whenever the offline reading passes every check.

What is stored is only label text (e.g. "Bill No", "Net Payable") and whether the value sits on the same line or
below - never names, GSTINs or amounts."""
from __future__ import annotations

import re
from decimal import Decimal

from .parser import amounts_in, parse_date, squeeze, to_dec

FIELDS = ["invoice_no", "invoice_date", "taxable_total", "cgst_total", "sgst_total", "igst_total", "cess_total",
          "tcs", "round_off", "grand_total"]
MONEY = {"taxable_total", "cgst_total", "sgst_total", "igst_total", "cess_total", "tcs", "round_off", "grand_total"}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9/\-_.]{0,24}")


def _money_forms(v: Decimal) -> list[str]:
    v = abs(v)
    plain = f"{v:.2f}"
    whole, frac = plain.split(".")
    intl = f"{int(whole):,}.{frac}"
    head, tail = whole[:-3], whole[-3:]
    ind = (",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1]) + "," + tail
           if head else tail) + "." + frac
    return list(dict.fromkeys([ind, intl, plain, whole if frac == "00" else plain]))


def _date_forms(d: str) -> list[str]:
    y, m, dd = d[:4], d[4:6], d[6:8]
    mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(m) - 1]
    return [f"{dd}/{m}/{y}", f"{dd}-{m}-{y}", f"{dd}.{m}.{y}", f"{dd}-{mon}-{y}", f"{dd} {mon} {y}",
            f"{dd}-{mon}-{y[2:]}", f"{dd}/{m}/{y[2:]}", f"{dd}-{m}-{y[2:]}", f"{y}-{m}-{dd}"]


HINTS = {"cgst_total": r"cgst|central", "sgst_total": r"sgst|utgst|state", "igst_total": r"igst|integrated",
         "cess_total": r"cess", "tcs": r"tcs", "round_off": r"round", "invoice_date": r"date|dt|dated",
         "invoice_no": r"no|num|#|inv|bill", "grand_total": r"total|payable|amount|net|grand",
         "taxable_total": r"taxable|value|sub|basic|net"}


def _label_before(line: str, pos: int) -> str:
    """Label just left of the value: the text after the previous wide gap (2+ spaces), letters only."""
    seg = [x for x in re.split(r"\s{2,}|\t", line[:pos]) if x.strip()]
    left = seg[-1] if seg else ""
    left = re.sub(r"[^A-Za-z ./#]", " ", left)
    words = [w for w in left.split() if len(w) > 1 or w in ("#",)]
    return " ".join(words[-4:]).strip(" .:/")


def learn_fields(inv, text: str) -> dict:
    """field -> {"label": str, "below": bool} for every value of the final (approved) invoice found in the text."""
    lines = text.splitlines()
    out = {}
    for f in FIELDS:
        val = getattr(inv, f, None)
        if not val:
            continue
        forms = (_money_forms(Decimal(str(val))) if f in MONEY else _date_forms(val) if f == "invoice_date"
                 else [str(val)])
        hits = []
        for i, ln in enumerate(lines):
            for form in forms:
                p = ln.find(form)
                if p < 0:
                    continue
                before = ln[p - 1] if p else " "
                after = ln[p + len(form)] if p + len(form) < len(ln) else " "
                if before.isdigit() or after.isdigit():
                    continue                      # part of a longer number
                lab = _label_before(ln, p)
                if len(lab) >= 2:
                    hits.append({"label": lab, "below": False})
                else:
                    prev = next((lines[j] for j in range(i - 1, max(-1, i - 3), -1) if lines[j].strip()), "")
                    lab = _label_before(prev, len(prev))
                    if len(lab) >= 2:
                        hits.append({"label": lab, "below": True})
                break
        if not hits:
            continue
        hint = HINTS.get(f)
        good = [h for h in hits if hint and re.search(hint, h["label"], re.I)] or hits
        out[f] = good[-1] if f in MONEY else good[0]
    return out


def merge(old: dict, new: dict) -> dict:
    """Keep up to 3 labels per field; the most recent first."""
    res = dict(old or {})
    for f, h in new.items():
        cur = res.get(f, {"labels": [], "below": h["below"]})
        labels = [h["label"]] + [l for l in cur.get("labels", []) if l != h["label"]]
        res[f] = {"labels": labels[:3], "below": h["below"]}
    return res


def read(fields: dict, text: str) -> dict:
    """Apply a learned layout to a new invoice's text: field -> value (Decimal / YYYYMMDD / str)."""
    lines = text.splitlines()
    sq = [squeeze(ln) for ln in lines]
    out = {}
    for f, spec in (fields or {}).items():
        for label in spec.get("labels", []):
            key = squeeze(label)
            if not key:
                continue
            idx = [i for i, s in enumerate(sq) if key in s]
            if not idx:
                continue
            i = idx[-1] if f in MONEY else idx[0]
            ln = lines[i]
            # position after the label in the original line (spaces may differ)
            m = re.search(r"\s*".join(map(re.escape, re.sub(r"\s+", "", label))), ln, re.I)
            rest = ln[m.end():] if m else ln
            cands = [rest] + ([lines[j] for j in range(i + 1, min(len(lines), i + 3))] if spec.get("below") else [])
            val = None
            for c in cands:
                if f in MONEY:
                    nums = [n for n in amounts_in(re.sub(r"\d+(\.\d+)?\s*%", " ", c)) if n]
                    if nums:
                        val = abs(nums[-1] if f == "grand_total" else nums[0])
                elif f == "invoice_date":
                    val = parse_date(c) or None
                else:
                    t = re.sub(r"^[\s:.#\-]+", "", c)
                    mm = _ID.match(t)
                    if mm and re.search(r"\d", mm.group(0)):
                        val = mm.group(0).rstrip(".")
                if val:
                    break
            if val:
                out[f] = val
                break
    return out


def apply(inv, fields: dict, text: str):
    """Overwrite the local reading with values found through the learned layout (confidence 0.95)."""
    got = read(fields, text)
    for f, v in got.items():
        setattr(inv, f, to_dec(str(v)) if f in MONEY else v)
        inv.field_confidence[f] = 0.95
    return inv, got
