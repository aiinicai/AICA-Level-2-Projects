"""Rule-based (offline, deterministic) extraction of Ind AS 116 inputs from agreement text.

Designed around the drafting conventions of Indian lease deeds and leave-and-licence
agreements (licensor/licensee, lock-in, "on or before the 7th of each English calendar
month", "Rs. X/- (Rupees ... only)", e-stamp certificates, CAM charges, 3+3+3 renewals).
Every candidate carries its evidence: page, character span and the quoted sentence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from .textnum import (Amount, find_amounts, find_dates, find_durations, find_percents, words_to_number)

ABBREV = ("rs", "no", "m/s", "pvt", "ltd", "sq", "ft", "i.e", "e.g", "w.e.f", "viz", "mr", "mrs", "ms", "dr", "shri", "smt",
          "st", "nos", "approx", "etc", "p.m", "p.a", "vs", "co", "inc", "cl", "para", "govt", "dt", "ref", "incl", "sr")

LESSOR_WORDS = r"(?:lessors?|licensors?|landlords?|owners?)"
LESSEE_WORDS = r"(?:lessees?|licensees?|tenants?)"


@dataclass
class Evidence:
    page: int
    quote: str
    start: int
    end: int


@dataclass
class Candidate:
    field: str
    value: Any
    confidence: float
    method: str
    evidence: Optional[Evidence] = None
    note: str = ""


class DocText:
    """Full text with page offsets."""

    def __init__(self, pages: list[tuple[int, str]]):
        parts = []
        self.spans = []
        pos = 0
        for no, txt in pages:
            t = txt or ""
            self.spans.append((no, pos, pos + len(t)))
            parts.append(t)
            pos += len(t) + 2
        self.text = "\n\n".join(parts)
        self.lower = self.text.lower()

    def page_of(self, idx: int) -> int:
        for no, a, b in self.spans:
            if a <= idx <= b + 1:
                return no
        return self.spans[-1][0] if self.spans else 1

    _CLAUSE_NO = re.compile(r"\d{1,2}(?:\.\d{1,2})*")

    def ends_sentence(self, p: int) -> bool:
        """True if the '.' at position p (followed by whitespace or the end of the text) closes a sentence.

        Not a sentence end: abbreviations ('Rs.', 'Pvt.', 'No.' ...) and clause / list numbers such as '1.' or '2.3.' at the
        start of a line, after a colon or after the previous sentence. A sentence that ends with a figure does end there
        ('... commencing from 1st April, 2025.', '... a deposit of Rs. 9,00,000.')."""
        t = self.text
        prev = re.search(r"([A-Za-z/\.]+)$", t[max(0, p - 12):p])
        if prev and prev.group(1).lower().rstrip(".") in ABBREV:
            return False
        num = re.search(r"(\d[\d.,/]*)$", t[max(0, p - 24):p])
        if num and self._CLAUSE_NO.fullmatch(num.group(1)):
            j = p - len(num.group(1)) - 1
            while j >= 0 and t[j] in " \t":
                j -= 1
            if j < 0 or t[j] in "\n:;.(":
                return False
        return True

    def sentence(self, idx: int, max_len: int = 700) -> tuple[int, int]:
        t = self.text
        a = idx
        lo = max(0, idx - max_len)
        while a > lo:
            ch = t[a - 1]
            if ch == "\n" and a >= 2 and t[a - 2] == "\n":
                break
            if ch == ";":
                break
            if ch == "." and a < len(t) and t[a:a + 1].isspace() and self.ends_sentence(a - 1):
                break
            a -= 1
        b = idx
        hi = min(len(t), idx + max_len)
        while b < hi:
            ch = t[b]
            if ch == "\n" and b + 1 < len(t) and t[b + 1] == "\n":
                break
            if ch == ";":
                b += 1
                break
            if ch == "." and (b + 1 >= len(t) or t[b + 1].isspace()) and self.ends_sentence(b):
                b += 1
                break
            b += 1
        return a, b

    def ev(self, a: int, b: int) -> Evidence:
        quote = re.sub(r"\s+", " ", self.text[a:b]).strip()
        return Evidence(self.page_of(a), quote[:600], a, b)


def _cands_for_keyword_dates(dt: DocText, pattern: str, field: str, conf: float, window: int = 160,
                             exclude: str | None = None, method: str = "") -> list[Candidate]:
    out = []
    for m in re.finditer(pattern, dt.lower):
        if exclude and re.search(exclude, dt.lower[max(0, m.start() - 60): m.end() + 20]):
            continue
        before = dt.lower[max(0, m.start() - 14): m.start()]
        if re.search(r"\(\s*(?:the\s*)?[\"“'‘]?\s*$", before):
            # defined term, e.g. '... from 1st April, 2025 (the "Commencement Date")' — the date precedes the term
            back = dt.text[max(0, m.start() - 170): m.start()]
            ds = find_dates(back)
            if ds:
                a, b = dt.sentence(m.start())
                out.append(Candidate(field, ds[-1].value.isoformat(), min(0.97, conf + 0.02), f"rule:{method or field}-defined-term",
                                     dt.ev(a, b)))
            continue
        seg = dt.text[m.start(): m.end() + window]
        ds = find_dates(seg)
        if not ds:
            continue
        d = ds[0]
        a, b = dt.sentence(m.start())
        out.append(Candidate(field, d.value.isoformat(), conf, f"rule:{method or field}", dt.ev(a, max(b, m.start() + d.end))))
    return out


def _best(cands: list[Candidate]) -> Optional[Candidate]:
    if not cands:
        return None
    return sorted(cands, key=lambda c: -c.confidence)[0]


class RuleExtractor:
    def __init__(self, pages: list[tuple[int, str]]):
        self.dt = DocText(pages)
        self.c: dict[str, list[Candidate]] = {}

    def add(self, cand: Candidate | None):
        if cand is None or cand.value is None:
            return
        self.c.setdefault(cand.field, []).append(cand)

    def extend(self, cands):
        for c in cands:
            self.add(c)

    # ------------------------------------------------------------------ run
    def run(self) -> dict[str, list[Candidate]]:
        for fn in (self.agreement_type, self.parties, self.agreement_date, self.term_dates, self.tenure, self.lock_in,
                   self.rent, self.area_rate, self.timing, self.escalation, self.rent_free, self.deposit, self.cam,
                   self.variable, self.stamp_duty, self.brokerage, self.renewal, self.termination, self.purchase_option,
                   self.rvg, self.restoration, self.sublease, self.substitution, self.gst, self.currency, self.asset):
            try:
                fn()
            except Exception as exc:  # a failing rule must never break extraction
                self.add(Candidate("_errors", f"{fn.__name__}: {exc}", 0, "rule:error"))
        self.derive()
        return self.c

    # ------------------------------------------------------------------ rules
    def agreement_type(self):
        L = self.dt.lower[:3000]
        mapping = [(r"leave\s+(and|&)\s+licen[cs]e", "LEAVE_AND_LICENSE", 0.95), (r"lease\s+deed|deed\s+of\s+lease", "LEASE_DEED", 0.9),
                   (r"equipment\s+lease|master\s+lease\s+agreement|lease\s+of\s+equipment", "EQUIPMENT_LEASE", 0.85),
                   (r"vehicle\s+lease|car\s+lease|lease\s+of\s+(the\s+)?vehicle", "VEHICLE_LEASE", 0.85),
                   (r"rent(al)?\s+agreement|tenancy\s+agreement", "RENT_AGREEMENT", 0.85), (r"lease\s+agreement", "LEASE_AGREEMENT", 0.8)]
        for pat, val, conf in mapping:
            m = re.search(pat, L)
            if m:
                a, b = self.dt.sentence(m.start(), 200)
                self.add(Candidate("agreement_type", val, conf, "rule:title", self.dt.ev(a, b)))
                return

    def parties(self):
        pat = re.compile(r"hereinafter\s*(?:jointly\s*|collectively\s*|individually\s*)?(?:called|referred\s*to\s*as|to\s*be\s*referred\s*(?:to\s*)?as|"
                         r"referred\s*as)\s*(?:the\s*)?[\"“'‘]?(?P<role>" + LESSOR_WORDS + "|" + LESSEE_WORDS + r")[\"”'’]?", re.I)
        text = self.dt.text
        for m in pat.finditer(text):
            role = m.group("role").lower()
            field = "lessor_name" if re.match(LESSOR_WORDS, role) else "lessee_name"
            back = text[max(0, m.start() - 900): m.start()]
            starts = [mm.end() for mm in re.finditer(r"(?:\b[Bb]etween\b|\bBETWEEN\b|\bAND\b|(?<=[\"”'’)])\s*and\b|"
                                                     r"(?<=[\"”'’)]\.)\s*and\b|\bBY\s+AND\s+BETWEEN\b|\n\s*\n)", back)]
            s0 = starts[-1] if starts else 0
            seg = back[s0:].strip(" \n:,")
            seg = re.sub(r"^\s*(?:\d+[\.\)]\s*|\(\w\)\s*)", "", seg)
            name = re.split(r",|\s+a\s+(?:company|private|public|partnership|limited|proprietorship|firm|body)|\s+having\s|\s+residing\s|"
                            r"\s+aged\s|\s+through\s|\s+represented\s|\s+\(PAN|\s+PAN\s|\s+incorporated\s|\s+s/o\s|\s+d/o\s|\s+w/o\s|\s+son\s+of\s|"
                            r"\s+daughter\s+of|\s+wife\s+of|\s+an\s+individual|\s+CIN", seg, maxsplit=1, flags=re.I)[0]
            name = re.sub(r"\s+", " ", name).strip(" .\"“”'")
            name = re.sub(r"^(?:M/s\.?|Messrs\.?|Mr\.?|Mrs\.?|Ms\.?|Shri\.?|Smt\.?)\s*", "", name, flags=re.I).strip()
            if 3 <= len(name) <= 140 and not re.search(r"hereinafter|agreement", name, re.I):
                a = m.start() - len(back) + s0
                self.add(Candidate(field, name, 0.88, "rule:hereinafter", self.dt.ev(max(0, a), m.end())))
        # "Licensor: XYZ" label style
        for fld, words in (("lessor_name", LESSOR_WORDS), ("lessee_name", LESSEE_WORDS)):
            for m in re.finditer(r"(?:^|\n)\s*(?:name\s+of\s+(?:the\s+)?)?" + words + r"\s*[:\-]\s*(?P<n>[^\n,]{3,120})", text, re.I):
                name = re.sub(r"^(?:M/s\.?|Mr\.?|Mrs\.?|Ms\.?|Shri\.?|Smt\.?)\s*", "", m.group("n").strip(), flags=re.I)
                self.add(Candidate(fld, name.strip(" ."), 0.8, "rule:label", self.dt.ev(m.start(), m.end())))

    def agreement_date(self):
        head = self.dt.text[:3500]
        for m in re.finditer(r"(made|entered\s+into|executed|dated|signed)\b[^.]{0,120}?", head, re.I):
            ds = find_dates(head[m.start(): m.start() + 200])
            if ds:
                a, b = self.dt.sentence(m.start())
                self.add(Candidate("agreement_date", ds[0].value.isoformat(), 0.85, "rule:made-on", self.dt.ev(a, b)))
                return
        m = re.search(r"this\s+\w+\s+day\s+of", head, re.I)
        if m:
            ds = find_dates(head[m.start(): m.start() + 80])
            if ds:
                self.add(Candidate("agreement_date", ds[0].value.isoformat(), 0.8, "rule:day-of", self.dt.ev(m.start(), m.end() + 40)))

    def term_dates(self):
        dt = self.dt
        rc_pat = r"rent\s+commencement\s+date|(rent|licen[cs]e\s+fee|compensation)\s+shall\s+(commence|be\s+payable|start)\s+(from|on|w\.?e\.?f\.?)|" \
                 r"(rent|licen[cs]e\s+fee)\s+(payable\s+)?w\.?e\.?f\.?"
        self.extend(_cands_for_keyword_dates(dt, rc_pat, "rent_commencement_date", 0.9, method="rent-commencement"))
        pats = [(r"(lease|licen[cs]e|agreement)?\s*commencement\s+date", 0.95),
                (r"(period|term|tenure)\s+of\s+[^.]{0,120}?(commencing|starting|beginning|w\.?e\.?f\.?|with\s+effect)\s+(from|on)?", 0.93),
                (r"commenc(e|es|ing|ement)\s+(on|from|w\.?e\.?f\.?)", 0.9),
                (r"with\s+effect\s+from|w\.?e\.?f\.?", 0.8),
                (r"(possession|handover|hand\s+over)\s+[^.]{0,80}?(on|from|w\.?e\.?f\.?)", 0.72)]
        for p, conf in pats:
            self.extend(_cands_for_keyword_dates(dt, p, "commencement_date", conf, window=170,
                                                 exclude=r"rent\s+commencement|fee\s+shall\s+(commence|be\s+payable)|rent\s+shall\s+commence",
                                                 method="commencement"))
        epats = [(r"expir(e|es|ing|y)\s+(on|date)", 0.9), (r"ending\s+on|end\s+on", 0.9),
                 (r"(till|until|upto|up\s+to)(\s+and\s+including)?", 0.75), (r"expiry\s+date", 0.92)]
        for p, conf in epats:
            self.extend(_cands_for_keyword_dates(dt, p, "expiry_date", conf, window=90, method="expiry"))
        # "from <d1> to/till <d2>"
        for m in re.finditer(r"from\s+(?P<a>.{6,40}?)\s+(?:to|till|until|upto|up\s+to)\s+(?P<b>.{6,40}?)(?:[\s,.;(]|$)", dt.text, re.I):
            da, db = find_dates(m.group("a")), find_dates(m.group("b"))
            if da and db and db[0].value > da[0].value:
                a, b = dt.sentence(m.start())
                if re.search(r"period|term|licen|lease|tenure", dt.lower[a:b]):
                    self.add(Candidate("commencement_date", da[0].value.isoformat(), 0.9, "rule:from-to", dt.ev(a, b)))
                    self.add(Candidate("expiry_date", db[0].value.isoformat(), 0.9, "rule:from-to", dt.ev(a, b)))

    def tenure(self):
        dt = self.dt
        for m in re.finditer(r"(?:(?:period|term|tenure|duration)\s+of\s+(?:the\s+)?(?:said\s+)?(?:lease|licen[cs]e|agreement)?|"
                             r"for\s+a\s+(?:total\s+)?(?:period|term)\s+of|licen[cs]e\s+period|lease\s+period|lease\s+term)", dt.lower):
            ctx = dt.lower[max(0, m.start() - 70): m.start()]
            if re.search(r"lock|notice|renew|extend|rent[- ]free|fit[- ]?out|grace|defect", ctx):
                continue
            seg = dt.text[m.end(): m.end() + 110]
            durs = [d for d in find_durations(seg) if d[3] == "months" and d[0] > 0]
            if durs:
                pre = dt.lower[m.end(): m.end() + durs[0][1]]
                if re.search(r"lock|notice|renew", pre):
                    continue
                a, b = dt.sentence(m.start())
                self.add(Candidate("tenure_months", durs[0][0], 0.9, "rule:period-of", dt.ev(a, b)))

    def lock_in(self):
        dt = self.dt
        for m in re.finditer(r"lock[\s\-]?in", dt.lower):
            seg = dt.text[m.start(): m.start() + 160]
            durs = [d for d in find_durations(seg) if d[0] != 0]
            a, b = dt.sentence(m.start())
            if durs:
                v = durs[0][0] if durs[0][0] > 0 else max(1, round(-durs[0][0] / 30))
                self.add(Candidate("lock_in_months", v, 0.9, "rule:lock-in", dt.ev(a, b)))
            s = dt.lower[a:b]
            local = dt.lower[m.start(): m.start() + 90]
            if re.search(r"for\s+(?:the\s+)?(?:" + LESSEE_WORDS + r")(?!\s+and)", local):
                who = "LESSEE"
            elif re.search(r"for\s+(?:the\s+)?(?:" + LESSOR_WORDS + r")(?!\s+and)", local):
                who = "LESSOR"
            elif re.search(r"both\s+(the\s+)?parties|either\s+party|parties\s+hereto|mutual", s):
                who = "BOTH"
            elif re.search(LESSEE_WORDS, s) and not re.search(LESSOR_WORDS, s):
                who = "LESSEE"
            elif re.search(LESSOR_WORDS, s) and not re.search(LESSEE_WORDS, s):
                who = "LESSOR"
            elif re.search(LESSOR_WORDS, s) and re.search(LESSEE_WORDS, s):
                who = "BOTH"
            else:
                who = None
            if who:
                self.add(Candidate("lock_in_applies_to", who, 0.75, "rule:lock-in-party", dt.ev(a, b)))

    def _amount_near(self, idx: int, span: int = 220, exclude_re: str | None = None) -> list[tuple[Amount, int]]:
        seg = self.dt.text[idx: idx + span]
        out = []
        for am in find_amounts(seg):
            ctx = seg[max(0, am.start - 60): am.start].lower()
            if exclude_re and re.search(exclude_re, ctx):
                continue
            out.append((am, idx + am.start))
        return out

    def rent(self):
        dt = self.dt
        kw = re.compile(r"(?:monthly\s*|annual\s*|quarterly\s*)?(?:rent(?:al)?|licen[cs]e\s*fees?|lease\s*rent(?:al)?|compensation|"
                        r"hire\s*charges|lease\s*charges)(?![a-np-z])", re.I)
        best = []
        for m in kw.finditer(dt.text):
            a, b = dt.sentence(m.start())
            sent = dt.lower[a:b]
            if re.search(r"security\s+deposit|stamp\s+duty|brokerage|penalty|liquidated|interest\s+at|late\s+payment", sent) and \
                    not re.search(r"(monthly|per\s+month).{0,40}(rent|licen[cs]e\s+fee)|(rent|licen[cs]e\s+fee).{0,60}per\s+month", sent):
                continue
            for am, pos in self._amount_near(m.start(), 260):
                if pos > b + 5:
                    continue
                post = dt.lower[pos: pos + len(am.raw) + 70]
                pre = dt.lower[max(a, pos - 90): pos]
                if re.search(r"per\s+sq|/\s*sq|psf|per\s+square", post[:len(am.raw) + 25]):
                    continue
                if re.search(r"deposit|maintenance|cam\b|stamp|brokerage|penalty|interest", pre[-50:]):
                    continue
                conf = 0.7
                freq = None
                tail = post[len(am.raw) - 0:]
                if re.search(r"^\W{0,5}(?:\(.*?\)\s*)?(per\s+month|p\.\s?m\.|pm\b|monthly|per\s+mensem|a\s+month|every\s+month|each\s+month)", tail) \
                        or re.search(r"monthly\s+(rent|licen[cs]e|compensation)", pre):
                    freq, conf = "MONTHLY", conf + 0.18
                elif re.search(r"^\W{0,5}(?:\(.*?\)\s*)?(per\s+quarter|quarterly|every\s+quarter)", tail) or "quarterly" in pre[-40:]:
                    freq, conf = "QUARTERLY", conf + 0.15
                elif re.search(r"^\W{0,5}(?:\(.*?\)\s*)?(per\s+half|half[\s\-]yearly|every\s+six\s+months)", tail):
                    freq, conf = "HALF_YEARLY", conf + 0.15
                elif re.search(r"^\W{0,5}(?:\(.*?\)\s*)?(per\s+annum|p\.\s?a\.|annually|per\s+year|yearly)", tail) or "annual" in pre[-40:]:
                    freq, conf = "ANNUAL", conf + 0.12
                if am.words_match:
                    conf += 0.07
                if re.search(r"exclusive\s+of|plus\s+gst|excluding", sent):
                    conf += 0.02
                best.append((conf, am, freq, a, b))
        if not best:
            return
        best.sort(key=lambda x: -x[0])
        seen = set()
        for conf, am, freq, a, b in best[:4]:
            if am.value in seen:
                continue
            seen.add(am.value)
            self.add(Candidate("rent_amount", str(am.value), round(min(conf, 0.97), 2), "rule:rent-amount", dt.ev(a, b),
                               note=("Amount in words matches figures." if am.words_match else
                                     "Amount in words does NOT match figures — verify." if am.words_match is False else "")))
            if freq:
                self.add(Candidate("rent_frequency", freq, round(min(conf, 0.95), 2), "rule:rent-frequency", dt.ev(a, b)))

    def area_rate(self):
        dt = self.dt
        for m in re.finditer(r"(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?:\(\s*[a-z\s\-]+\)\s*)?(?:sq\.?\s*ft\.?|square\s+feet|sft|sq\.\s*feet)", dt.text, re.I):
            pre = dt.lower[max(0, m.start() - 40): m.start()]
            if re.search(r"rs\.?|inr|₹|per\s*$", pre[-12:]):
                continue
            a, b = dt.sentence(m.start())
            try:
                v = Decimal(m.group("n").replace(",", ""))
            except Exception:
                continue
            if v >= 50:
                self.add(Candidate("area_sqft", str(v), 0.8, "rule:area", dt.ev(a, b)))
        for m in re.finditer(r"per\s+sq(?:uare)?\.?\s*f(?:ee)?t|/\s*sq\.?\s*ft|psf", dt.lower):
            seg_start = max(0, m.start() - 60)
            ams = find_amounts(dt.text[seg_start: m.start() + 5])
            if ams:
                am = ams[-1]
                a, b = dt.sentence(m.start())
                self.add(Candidate("rate_per_sqft", str(am.value), 0.8, "rule:psf", dt.ev(a, b)))

    def timing(self):
        dt = self.dt
        for m in re.finditer(r"(?:on\s+or\s+before|by|before|within|not\s+later\s+than)\s+(?:the\s+)?(?P<d>\d{1,2})(?:st|nd|rd|th)?\s+(?:day\s+)?"
                             r"(?:of\s+)?(?:each|every|the)\s+(?:english\s+)?(?:calendar\s+)?(?P<which>following\s+|succeeding\s+|next\s+)?month", dt.lower):
            a, b = dt.sentence(m.start())
            s = dt.lower[a:b]
            if not re.search(r"rent|licen[cs]e\s+fee|compensation|payable|paid", s):
                continue
            d = int(m.group("d"))
            if 1 <= d <= 31:
                self.add(Candidate("payment_due_day", d, 0.88, "rule:due-day", dt.ev(a, b)))
            if m.group("which"):
                self.add(Candidate("payment_timing", "ARREARS", 0.8, "rule:due-following-month", dt.ev(a, b)))
            elif re.search(r"in\s+advance|advance", s):
                self.add(Candidate("payment_timing", "ADVANCE", 0.92, "rule:advance", dt.ev(a, b)))
            else:
                self.add(Candidate("payment_timing", "ADVANCE", 0.78, "rule:due-in-month", dt.ev(a, b),
                                   note="Rent for the month payable within the same month — treated as in advance."))
        for m in re.finditer(r"in\s+advance", dt.lower):
            a, b = dt.sentence(m.start())
            if re.search(r"rent|licen[cs]e\s+fee|compensation|hire", dt.lower[a:b]) and not re.search(r"deposit", dt.lower[a:b]):
                self.add(Candidate("payment_timing", "ADVANCE", 0.9, "rule:in-advance", dt.ev(a, b)))
        for m in re.finditer(r"in\s+arrears|at\s+the\s+end\s+of\s+(each|every)\s+(month|quarter|year)", dt.lower):
            a, b = dt.sentence(m.start())
            if re.search(r"rent|licen[cs]e\s+fee|compensation|hire|payable", dt.lower[a:b]):
                self.add(Candidate("payment_timing", "ARREARS", 0.9, "rule:in-arrears", dt.ev(a, b)))

    def escalation(self):
        dt = self.dt
        for m in re.finditer(r"escalat\w*|increas\w*|enhanc\w*|revis\w*\s+upward", dt.lower):
            a, b = dt.sentence(m.start())
            s = dt.text[a:b]
            sl = s.lower()
            if not re.search(r"rent|licen[cs]e\s+fee|compensation|rental", sl) or re.search(r"renew", sl[:max(0, m.start() - a)] or ""):
                continue
            pcts = [p for p in find_percents(s) if Decimal("0") < p[0] <= Decimal("50")]
            if not pcts:
                continue
            if re.search(r"on\s+renewal|upon\s+renewal|renewed\s+term|at\s+the\s+time\s+of\s+renewal", sl):
                self.add(Candidate("renewal_escalation_pct", str(pcts[0][0]), 0.8, "rule:renewal-escalation", dt.ev(a, b)))
                continue
            self.add(Candidate("escalation_pct", str(pcts[0][0]), 0.88, "rule:escalation", dt.ev(a, b)))
            every = None
            fm = re.search(r"(?:every|each|after\s+every|after\s+each|after|on\s+completion\s+of\s+every|on\s+expiry\s+of\s+every|at\s+the\s+end\s+of\s+every|"
                           r"on\s+the\s+expiry\s+of\s+every|upon\s+completion\s+of\s+every|on\s+completion\s+of)\s+(?P<rest>.{0,40})", sl)
            if fm:
                durs = find_durations(fm.group("rest"))
                if durs and durs[0][0] > 0:
                    every = durs[0][0]
                elif re.match(r"(?:year|annum|anniversary)", fm.group("rest").strip()):
                    every = 12
                else:
                    wm = re.match(r"(?P<w>[a-z]+|\d+)\s*(?:\(\d+\)\s*)?(?:years?|yrs?)", fm.group("rest").strip())
                    if wm:
                        n = words_to_number(wm.group("w")) if not wm.group("w").isdigit() else Decimal(wm.group("w"))
                        if n:
                            every = int(n) * 12
            if every is None and re.search(r"per\s+annum|annually|every\s+year|each\s+year|year\s+on\s+year|yoy|yearly|p\.\s?a\.", sl):
                every = 12
            if every:
                self.add(Candidate("escalation_every_months", every, 0.85, "rule:escalation-frequency", dt.ev(a, b)))
            if re.search(r"last\s+(paid|payable|drawn)|prevailing|then\s+(current|existing)|compound", sl):
                self.add(Candidate("escalation_basis", "COMPOUND", 0.85, "rule:escalation-basis", dt.ev(a, b)))
            elif re.search(r"(base|initial|original|starting)\s+(rent|licen[cs]e\s+fee)|simple", sl):
                self.add(Candidate("escalation_basis", "SIMPLE", 0.85, "rule:escalation-basis", dt.ev(a, b)))

    def rent_free(self):
        dt = self.dt
        for m in re.finditer(r"(?:rent|licen[cs]e\s+fee)[\s\-]*free|fit[\s\-]?out\s+period|moratorium|rent\s+holiday", dt.lower):
            a, b = dt.sentence(m.start())
            seg = dt.text[m.start(): min(b, m.start() + 200)]
            durs = [d for d in find_durations(seg) if d[0] != 0]
            if not durs:
                seg = dt.text[a:b]
                durs = [d for d in find_durations(seg) if d[0] != 0]
            if durs:
                v = durs[0][0]
                days = -v if v < 0 else int(v * 30)
                self.add(Candidate("rent_free_days", days, 0.85, "rule:rent-free", dt.ev(a, b),
                                   note="" if v < 0 else f"{v} month(s) converted to ~{days} days; exact dates set from commencement."))

    def deposit(self):
        dt = self.dt
        for m in re.finditer(r"(?:interest[\s\-]free\s+)?(?:refundable\s+)?(?:security|caution)?\s*deposit", dt.lower):
            a, b = dt.sentence(m.start())
            s = dt.lower[a:b]
            if "stamp" in s[:max(0, m.start() - a)]:
                continue
            ams = [x for x in self._amount_near(max(a, m.start() - 10), (b - m.start()) + 20) if x[1] <= b]
            if ams:
                am, pos = ams[0]
                conf = 0.9 if "security" in s or "interest" in s else 0.75
                self.add(Candidate("deposit_amount", str(am.value), conf + (0.05 if am.words_match else 0), "rule:deposit", dt.ev(a, b)))
            else:
                mm = re.search(r"equivalent\s+to\s+(?P<n>\d+|[a-z]+)\s*(?:\(\d+\)\s*)?months?", s)
                if mm:
                    n = int(mm.group("n")) if mm.group("n").isdigit() else int(words_to_number(mm.group("n")) or 0)
                    if n:
                        self.add(Candidate("deposit_amount", f"=months:{n}", 0.6, "rule:deposit-months", dt.ev(a, b),
                                           note=f"Deposit equal to {n} months' rent — amount derived from rent."))
            if re.search(r"interest[\s\-]free|without\s+(any\s+)?interest|shall\s+not\s+(carry|bear|earn|attract)\s+(any\s+)?interest|free\s+of\s+interest|no\s+interest", s):
                self.add(Candidate("deposit_interest_free", True, 0.9, "rule:interest-free", dt.ev(a, b)))
            elif re.search(r"interest\s+(at|@)\s+\d", s):
                self.add(Candidate("deposit_interest_free", False, 0.8, "rule:interest-bearing", dt.ev(a, b)))

    def cam(self):
        dt = self.dt
        for m in re.finditer(r"(?:common\s+area\s+)?maintenance\s+charges?|\bcam\b(?:\s+charges?)?|service\s+charges?|society\s+charges?", dt.lower):
            a, b = dt.sentence(m.start())
            ams = [x for x in self._amount_near(m.start(), 220) if x[1] <= b]
            if ams:
                am, pos = ams[0]
                post = dt.lower[pos: pos + len(am.raw) + 40]
                if re.search(r"per\s+sq|/\s*sq|psf", post):
                    self.add(Candidate("cam_amount", f"=psf:{am.value}", 0.6, "rule:cam-psf", dt.ev(a, b),
                                       note="CAM quoted per sq ft — monthly amount derived using area."))
                else:
                    self.add(Candidate("cam_amount", str(am.value), 0.82, "rule:cam", dt.ev(a, b)))

    def variable(self):
        dt = self.dt
        for m in re.finditer(r"revenue\s+share|turnover\s+rent|\d+(?:\.\d+)?\s*%\s+of\s+(?:the\s+)?(?:gross\s+|net\s+)?(?:sales|revenue|turnover|receipts)|"
                             r"minimum\s+guarantee(?:d)?\s+(?:rent|amount)?|\bMG\b", dt.text, re.I):
            a, b = dt.sentence(m.start())
            self.add(Candidate("variable_rent", re.sub(r"\s+", " ", dt.text[a:b]).strip()[:300], 0.8, "rule:variable", dt.ev(a, b)))
            break

    def stamp_duty(self):
        dt = self.dt
        for m in re.finditer(r"stamp\s+duty\s+(?:amount|paid)\s*(?:\(\s*rs\.?\s*\)|in\s+rs\.?|\(inr\))?\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*(?P<n>\d[\d,]*(?:\.\d+)?)", dt.lower):
            a, b = dt.sentence(m.start(), 200)
            self.add(Candidate("stamp_duty_amount", m.group("n").replace(",", ""), 0.9, "rule:e-stamp", dt.ev(m.start(), m.end())))
        for m in re.finditer(r"stamp\s+duty(?:\s+(?:and|&)\s+registration(?:\s+(?:charges|fees|expenses))?)?[^.]{0,80}?(?:shall\s+be\s+)?(?:borne|paid)\s+"
                             r"(?:by\s+)?(?:the\s+)?(?P<who>" + LESSEE_WORDS + "|" + LESSOR_WORDS + r"|both|equally)", dt.lower):
            who = m.group("who")
            val = "EQUALLY" if who in ("both", "equally") else ("LESSEE" if re.match(LESSEE_WORDS, who) else "LESSOR")
            a, b = dt.sentence(m.start())
            if re.search(r"equally|50\s*:\s*50|in\s+equal", dt.lower[a:b]):
                val = "EQUALLY"
            self.add(Candidate("stamp_duty_borne_by", val, 0.85, "rule:stamp-borne", dt.ev(a, b)))

    def brokerage(self):
        dt = self.dt
        for m in re.finditer(r"brokerage", dt.lower):
            a, b = dt.sentence(m.start())
            ams = [x for x in self._amount_near(a, b - a) if x[1] <= b]
            if ams:
                self.add(Candidate("brokerage_amount", str(ams[0][0].value), 0.75, "rule:brokerage", dt.ev(a, b)))

    def renewal(self):
        dt = self.dt
        for m in re.finditer(r"renew(?:al|ed|able)?|extension\s+of\s+the\s+(?:term|period|lease|licen[cs]e)|extend\s+the\s+(?:term|period|lease|licen[cs]e)", dt.lower):
            a, b = dt.sentence(m.start())
            s = dt.lower[a:b]
            if re.search(r"shall\s+not\s+be\s+renew|no\s+renewal|not\s+renewable", s):
                self.add(Candidate("renewal_option", False, 0.85, "rule:no-renewal", dt.ev(a, b)))
                continue
            self.add(Candidate("renewal_option", True, 0.8, "rule:renewal", dt.ev(a, b)))
            durs = [d for d in find_durations(dt.text[m.start(): b]) if d[0] > 0]
            if durs:
                self.add(Candidate("renewal_months", durs[0][0], 0.8, "rule:renewal-period", dt.ev(a, b)))
            if re.search(r"mutual(ly)?\s+(consent|agree|acceptable|discuss)|mutually|subject\s+to\s+(?:the\s+)?(?:" + LESSOR_WORDS + r")['’]?s?\s+(consent|approval)|"
                         r"fresh\s+agreement|new\s+agreement|as\s+may\s+be\s+agreed", s):
                self.add(Candidate("renewal_at_option_of", "MUTUAL", 0.82, "rule:renewal-mutual", dt.ev(a, b)))
            elif re.search(r"(?:option|right|discretion)\s+of\s+the\s+" + LESSEE_WORDS + "|" + LESSEE_WORDS + r"\s+shall\s+(?:have|be\s+entitled\s+to)\s+(?:the\s+|an\s+)?(?:right|option)|"
                           r"at\s+the\s+(?:sole\s+)?(?:option|request)\s+of\s+the\s+" + LESSEE_WORDS, s):
                self.add(Candidate("renewal_at_option_of", "LESSEE", 0.85, "rule:renewal-lessee", dt.ev(a, b)))
            pcts = [p for p in find_percents(dt.text[a:b]) if 0 < p[0] <= 50]
            if pcts and re.search(r"increas|escalat|enhanc|higher", s):
                self.add(Candidate("renewal_escalation_pct", str(pcts[0][0]), 0.8, "rule:renewal-escalation", dt.ev(a, b)))

    def termination(self):
        dt = self.dt
        for m in re.finditer(r"terminat\w*", dt.lower):
            a, b = dt.sentence(m.start())
            s = dt.lower[a:b]
            if not re.search(r"notice", s):
                continue
            durs = [d for d in find_durations(dt.text[a:b]) if d[0] != 0]
            months = None
            if durs:
                # prefer the duration closest to the word notice
                npos = s.find("notice")
                durs.sort(key=lambda d: abs(d[1] - npos))
                v = durs[0][0]
                months = v if v > 0 else max(1, round(-v / 30))
            breach = re.search(r"breach|default|non[\s\-]payment|fail(s|ure)?\s+to\s+pay|violation|insolven|illegal", s)
            either = re.search(r"either\s+party|both\s+(the\s+)?parties|any\s+party", s)
            lessee_subj = re.search(r"(the\s+)?" + LESSEE_WORDS + r"\s+(shall\s+be\s+entitled|may|shall\s+have\s+the\s+right|can)", s)
            lessor_subj = re.search(r"(the\s+)?" + LESSOR_WORDS + r"\s+(shall\s+be\s+entitled|may|shall\s+have\s+the\s+right|can)", s)
            if (lessee_subj or either) and months:
                self.add(Candidate("lessee_termination_notice_months", months, 0.82, "rule:lessee-termination", dt.ev(a, b)))
            if (lessor_subj or either) and not breach:
                self.add(Candidate("lessor_can_terminate_without_cause", True, 0.75, "rule:lessor-termination", dt.ev(a, b)))
            elif lessor_subj and breach:
                self.add(Candidate("lessor_can_terminate_without_cause", False, 0.7, "rule:lessor-termination-breach", dt.ev(a, b)))
            if re.search(r"penalty|compensation|liquidated\s+damages|termination\s+fee|forfeit", s):
                ams = find_amounts(dt.text[a:b])
                if ams:
                    self.add(Candidate("termination_penalty", str(ams[0].value), 0.7, "rule:termination-penalty", dt.ev(a, b)))
                else:
                    mm = re.search(r"equivalent\s+to\s+(?P<n>\d+|[a-z]+)\s*(?:\(\d+\)\s*)?months?", s)
                    if mm:
                        n = int(mm.group("n")) if mm.group("n").isdigit() else int(words_to_number(mm.group("n")) or 0)
                        if n:
                            self.add(Candidate("termination_penalty", f"=months:{n}", 0.6, "rule:termination-penalty-months", dt.ev(a, b)))

    def purchase_option(self):
        dt = self.dt
        for m in re.finditer(r"option\s+to\s+(?:purchase|buy|acquire)|purchase\s+option|buy[\s\-]?back\s+option|right\s+to\s+purchase", dt.lower):
            a, b = dt.sentence(m.start())
            ams = find_amounts(dt.text[a:b])
            val = str(ams[0].value) if ams else None
            if val:
                self.add(Candidate("purchase_option_price", val, 0.82, "rule:purchase-option", dt.ev(a, b)))

    def rvg(self):
        dt = self.dt
        for m in re.finditer(r"residual\s+value", dt.lower):
            a, b = dt.sentence(m.start())
            if "guarant" in dt.lower[a:b]:
                ams = find_amounts(dt.text[a:b])
                if ams:
                    self.add(Candidate("residual_value_guarantee", str(ams[0].value), 0.8, "rule:rvg", dt.ev(a, b)))

    def restoration(self):
        dt = self.dt
        m = re.search(r"(restore|reinstate|reinstatement|restoration)\b[^.]{0,160}(original|same|good)\s+(condition|state|order)|"
                      r"(hand\s+over|handover|deliver)\s+(back\s+)?(vacant\s+)?(peaceful\s+)?possession[^.]{0,160}(original|same|good)\s+(condition|state)|"
                      r"remove\s+(all\s+)?(the\s+)?(fit[\s\-]?outs|fixtures|improvements|installations)", dt.lower)
        if m:
            a, b = dt.sentence(m.start())
            self.add(Candidate("restoration_obligation", True, 0.8, "rule:restoration", dt.ev(a, b),
                               note="Assess whether a restoration provision (Ind AS 37) is required; 'reasonable wear and tear' clauses reduce it."))

    def sublease(self):
        dt = self.dt
        for m in re.finditer(r"sub[\s\-]?let|sub[\s\-]?lease|sub[\s\-]?licen[cs]e|part\s+with\s+(the\s+)?possession", dt.lower):
            a, b = dt.sentence(m.start())
            s = dt.lower[a:b]
            if re.search(r"shall\s+not|not\s+be\s+entitled|not\s+permitted|prohibited|without\s+(the\s+)?(prior\s+)?(written\s+)?consent|no\s+right", s):
                self.add(Candidate("sublease_permitted", False, 0.8, "rule:no-sublet", dt.ev(a, b)))
            elif re.search(r"may\s+sub|entitled\s+to\s+sub|free\s+to\s+sub|right\s+to\s+sub", s):
                self.add(Candidate("sublease_permitted", True, 0.8, "rule:sublet", dt.ev(a, b)))
            break

    def substitution(self):
        dt = self.dt
        m = re.search(r"(?:" + LESSOR_WORDS + r")\s+(?:may|shall\s+be\s+entitled\s+to|has\s+the\s+right\s+to|reserves\s+the\s+right\s+to|shall\s+have\s+the\s+right\s+to)\s+"
                      r"(?:at\s+any\s+time\s+)?(?:substitute|replace|relocate|shift|change)", dt.lower)
        if m:
            a, b = dt.sentence(m.start())
            self.add(Candidate("substitution_right", True, 0.8, "rule:substitution", dt.ev(a, b),
                               note="Substitution right is substantive only if practical ability AND economic benefit exist (B14)."))

    def gst(self):
        dt = self.dt
        m = re.search(r"(exclusive\s+of|plus|over\s+and\s+above|in\s+addition\s+to|excluding)\s+(the\s+)?(applicable\s+)?(gst|goods\s+and\s+services\s+tax)|"
                      r"(gst|goods\s+and\s+services\s+tax)\s+(as\s+applicable\s+)?(shall\s+be\s+)?(extra|payable\s+extra|borne\s+by)", dt.lower)
        if m:
            a, b = dt.sentence(m.start())
            self.add(Candidate("gst_treatment", "Exclusive of GST (GST charged extra)", 0.85, "rule:gst", dt.ev(a, b)))
            return
        m = re.search(r"inclusive\s+of\s+(all\s+)?(taxes|gst)", dt.lower)
        if m:
            a, b = dt.sentence(m.start())
            self.add(Candidate("gst_treatment", "Inclusive of GST", 0.8, "rule:gst", dt.ev(a, b)))

    def currency(self):
        L = self.dt.lower
        inr = len(re.findall(r"\brs\.?\s*\d|\binr\b|₹|\brupees\b", L))
        usd = len(re.findall(r"\busd\b|us\$|\bus\s+dollars?\b", L))
        eur = len(re.findall(r"\beur\b|€", L))
        cur = max((("INR", inr), ("USD", usd), ("EUR", eur)), key=lambda x: x[1])
        if cur[1]:
            self.add(Candidate("currency", cur[0], 0.9 if cur[1] > 2 else 0.7, "rule:currency-count", None,
                               note=f"{cur[1]} currency references found."))

    def asset(self):
        dt = self.dt
        m = re.search(r"(?:schedule|description)\s+(?:of|to)?\s*(?:the\s+)?(?:said\s+)?(?:premises|property|licen[cs]ed\s+premises|leased\s+premises|equipment|vehicle)", dt.lower)
        cand_idx = None
        if m:
            cand_idx = m.end()
        else:
            m = re.search(r"(?:premises|property|office\s+space|unit|shop|warehouse|godown|flat|floor)\s+(?:bearing|situated|located|admeasuring|being|known\s+as)", dt.lower)
            if m:
                cand_idx = m.start()
        if cand_idx is not None:
            a, b = dt.sentence(cand_idx + 1, 500)
            if b - cand_idx < 25:
                b = dt.sentence(b + 2, 500)[1]
            desc = re.sub(r"\s+", " ", dt.text[cand_idx: b]).strip(" :.-)(\n")
            # the premises clause often runs on into the term / rent ('... 40,000 sq.ft. for a period of 9 years commencing ...')
            cut = re.search(r"[\s,]*(?:\bfor\s+a\s+(?:total\s+)?(?:period|term)\b|\bfor\s+(?:the\s+)?(?:licen[cs]e|lease)\s+(?:period|term)\b|"
                            r"\bcommencing\b|\bwith\s+effect\s+from\b|\bon\s+the\s+terms\b|\bat\s+a\s+(?:monthly\s+)?(?:rent|licen[cs]e\s+fee)\b)",
                            desc, re.I)
            if cut and cut.start() >= 15:
                desc = desc[:cut.start()].strip(" ,;:-")
            if len(desc) > 10:
                self.add(Candidate("asset_description", desc[:400], 0.7, "rule:premises", dt.ev(a, b)))
        m = re.search(r"(situated|located|lying)\s+at\s+(?P<addr>[^.;]{10,220})", dt.text, re.I)
        if m:
            self.add(Candidate("asset_address", re.sub(r"\s+", " ", m.group("addr")).strip(), 0.72, "rule:address",
                               dt.ev(m.start(), m.end())))
        L = dt.lower
        scores = {
            "Buildings": len(re.findall(r"premises|office|warehouse|godown|shop|flat|floor|building|unit\s+no|carpet\s+area|showroom", L)),
            "Land": len(re.findall(r"\bland\b|plot\s+no|survey\s+no|acre|hectare", L)),
            "Vehicles": len(re.findall(r"vehicle|\bcar\b|registration\s+no|chassis|engine\s+no", L)),
            "Plant and machinery": len(re.findall(r"machine|machinery|equipment|plant\b|generator|crane", L)),
            "IT equipment": len(re.findall(r"laptop|computer|server|printer|it\s+equipment|desktop", L)),
        }
        best = max(scores.items(), key=lambda x: x[1])
        if best[1] > 0:
            self.add(Candidate("asset_category", best[0], min(0.9, 0.5 + best[1] * 0.04), "rule:category-keywords", None,
                               note=f"Keyword score {best[1]}"))

    # ------------------------------------------------------------------ derived values
    def derive(self):
        best = {k: _best(v) for k, v in self.c.items() if not k.startswith("_")}
        from ..engine.calendar_utils import add_months, months_between_frac, prev_day, next_day
        cd = best.get("commencement_date")
        ed = best.get("expiry_date")
        tm = best.get("tenure_months")
        if cd and tm and not ed:
            d = prev_day(add_months(date.fromisoformat(cd.value), int(tm.value)))
            self.add(Candidate("expiry_date", d.isoformat(), min(cd.confidence, tm.confidence) - 0.1, "derived",
                               note="Derived: commencement date + contractual term − 1 day."))
        if cd and ed and not tm:
            months = months_between_frac(date.fromisoformat(cd.value), next_day(date.fromisoformat(ed.value)))
            if months == int(months):
                self.add(Candidate("tenure_months", int(months), min(cd.confidence, ed.confidence) - 0.1, "derived",
                                   note="Derived from commencement and expiry dates."))
        if not cd:
            rc = best.get("rent_commencement_date") or best.get("agreement_date")
            if rc:
                self.add(Candidate("commencement_date", rc.value, 0.35, "derived",
                                   note="No explicit commencement date found — proposed from "
                                        f"{'rent commencement' if best.get('rent_commencement_date') else 'agreement'} date. "
                                        "Commencement is when the asset is made available for use (App. A) — confirm."))
        rent = best.get("rent_amount")
        area, psf = best.get("area_sqft"), best.get("rate_per_sqft")
        if not rent and area and psf:
            v = Decimal(area.value) * Decimal(psf.value)
            self.add(Candidate("rent_amount", str(v.quantize(Decimal("0.01"))), 0.6, "derived",
                               note=f"Derived: area {area.value} sq ft × rate {psf.value} per sq ft."))
            rent = self.c["rent_amount"][-1]
        for key in ("deposit_amount", "termination_penalty"):
            for cnd in self.c.get(key, []):
                if isinstance(cnd.value, str) and cnd.value.startswith("=months:") and rent:
                    n = int(cnd.value.split(":")[1])
                    cnd.value = str((Decimal(rent.value) * n).quantize(Decimal("0.01")))
                    cnd.note += f" Derived: {n} × rent {rent.value}."
                    cnd.method = "derived"
        for cnd in self.c.get("cam_amount", []):
            if isinstance(cnd.value, str) and cnd.value.startswith("=psf:"):
                if area:
                    cnd.value = str((Decimal(cnd.value.split(":")[1]) * Decimal(area.value)).quantize(Decimal("0.01")))
                    cnd.method = "derived"
                else:
                    cnd.value = None
        for k in list(self.c):
            self.c[k] = [x for x in self.c[k] if x.value is not None]
        if not best.get("rent_frequency") and rent:
            self.add(Candidate("rent_frequency", "MONTHLY", 0.4, "derived", note="Frequency not stated near the rent clause — assumed monthly; confirm."))
        if not best.get("currency"):
            self.add(Candidate("currency", "INR", 0.5, "derived", note="Default currency."))


def extract_rules(pages: list[tuple[int, str]]) -> dict[str, list[Candidate]]:
    return RuleExtractor(pages).run()
