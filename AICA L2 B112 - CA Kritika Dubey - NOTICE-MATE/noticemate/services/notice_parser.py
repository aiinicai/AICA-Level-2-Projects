"""Module 4 — notice particulars and deadline extraction (rule-based, local).

Every field returns {value, status, source_snippet, needs_verification}.
* status = EXTRACTED or NOT PROVIDED. Nothing is guessed.
* The compliance deadline is ALWAYS needs_verification=True until a user
  verifies it against the portal / notice (see notices.verify_deadline).
* "Within N days" deadlines are reported as text; an indicative date is shown
  only if a date of service was found, and is still marked for verification.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

NP = "NOT PROVIDED"

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
_MONTHS.update({k[:3]: v for k, v in list(_MONTHS.items())})
_DATE_NUM = r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})"
_DATE_TXT = r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})[,]?\s+(\d{4})"
DATE_RX = re.compile(rf"(?:{_DATE_NUM}|{_DATE_TXT})")

_SECTION_RX = re.compile(
    r"(?i)(?:u/s\.?|under\s+section|section|sec\.)\s*(\d{2,3}[A-Z]{0,3}(?:\s?\(\s?\d+[A-Za-z]?\s?\))*(?:\s?\(\s?[a-z]{1,4}\s?\))?)")
_AY_RX = re.compile(r"(?i)(?:a\.?\s?y\.?|assessment\s+year)\s*[:\-]?\s*(\d{4}\s?-\s?\d{2,4})")
_TY_RX = re.compile(r"(?i)tax\s+year\s*[:\-]?\s*(\d{4}\s?-\s?\d{2,4})")
_DIN_RX = re.compile(r"(?i)\bDIN\s*(?:&\s*Notice\s*No\.?)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9/().\-]{8,})")
_NOTICE_NO_RX = re.compile(r"(?i)notice\s*(?:no\.?|number)\s*[:\-]?\s*([A-Z0-9][A-Z0-9/().\-]{3,})")
_AMOUNT_RX = re.compile(r"(?i)(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.\d{1,2})?)(\s*(?:lakh|lakhs|crore|crores))?")

_AUTHORITY_RX = re.compile(
    r"(?i)(national\s+faceless\s+assessment\s+cent(?:re|er)|assessment\s+unit[^\n]*|income[- ]tax\s+officer[^\n]*|"
    r"(?:deputy|assistant|joint|additional|principal)?\s*commissioner\s+of\s+income[- ]tax[^\n]*|"
    r"\b(?:ito|acit|dcit|jcit|addl\.?\s*cit|pcit|cit)\b[^\n]*(?:ward|circle|range)[^\n]*|assessing\s+officer[^\n]*)")

SECTION_NATURE_1961 = {
    "139(9)": "Defective return notice",
    "142(1)": "Inquiry before assessment / call for information",
    "143(1)(a)": "Prima facie adjustment intimation proposal",
    "143(2)": "Scrutiny assessment notice",
    "148": "Reassessment notice (income escaping assessment)",
    "148A": "Pre-reassessment inquiry / show cause",
    "148A(b)": "Show cause before issue of s.148 notice",
    "131": "Summons",
    "133(6)": "Call for information",
    "156": "Notice of demand",
    "245": "Proposed adjustment of refund against demand",
    "270A": "Penalty for under-reporting / misreporting",
    "271AAC": "Penalty in respect of income referred to in s.68–69D",
    "274": "Penalty show-cause procedure",
}


def parse_date(s: str) -> date | None:
    m = DATE_RX.search(s)
    if not m:
        return None
    try:
        if m.group(1):
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        mon = _MONTHS.get(m.group(5).lower()) or _MONTHS.get(m.group(5).lower()[:3])
        return date(int(m.group(6)), mon, int(m.group(4))) if mon else None
    except (ValueError, TypeError):
        return None


def _field(value=None, source=None, verify=True, note=None) -> dict:
    return {"value": value if value not in (None, "") else NP,
            "status": "EXTRACTED" if value not in (None, "") else NP,
            "source_snippet": (source or "")[:240],
            "needs_verification": verify,
            "note": note}


def _line_of(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return text[start: end if end != -1 else len(text)].strip()


def _first_date_near(text: str, keywords: list[str], window: int = 120) -> tuple[date | None, str]:
    for kw in keywords:
        for m in re.finditer(kw, text, re.I):
            seg = text[m.end(): m.end() + window]
            d = parse_date(seg)
            if d:
                return d, _line_of(text, m.start())
    return None, ""


def normalise_section(raw: str) -> str:
    return re.sub(r"\s+", "", raw).replace("((", "(")


def parse_amount(s: str) -> float | None:
    m = _AMOUNT_RX.search(s)
    if not m:
        return None
    try:
        v = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = (m.group(2) or "").strip().lower()
    if unit.startswith("lakh"):
        v *= 1e5
    elif unit.startswith("crore"):
        v *= 1e7
    return v


def extract_particulars(text: str) -> dict:
    t = (text or "").replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")  # en/em dash in "2025–26"
    out: dict[str, dict] = {}

    # Section: most frequent normalised match, preferring ones in the first 3000 chars
    secs = [normalise_section(m.group(1)) for m in _SECTION_RX.finditer(t[:6000])]
    sec = max(set(secs), key=lambda s: (secs.count(s), -secs.index(s))) if secs else None
    sec_src = next((_line_of(t, m.start()) for m in _SECTION_RX.finditer(t) if normalise_section(m.group(1)) == sec), "") if sec else ""
    out["section"] = _field(sec, sec_src)

    m = _DIN_RX.search(t)
    out["din"] = _field(m.group(1).rstrip(".,;") if m else None, _line_of(t, m.start()) if m else None)
    m = _NOTICE_NO_RX.search(t)
    out["notice_number"] = _field(m.group(1).rstrip(".,;") if m else None, _line_of(t, m.start()) if m else None)

    m = _AY_RX.search(t)
    ay = re.sub(r"\s", "", m.group(1)) if m else None
    out["assessment_year"] = _field(ay, _line_of(t, m.start()) if m else None)
    m = _TY_RX.search(t)
    out["tax_year"] = _field(re.sub(r"\s", "", m.group(1)) if m else None, _line_of(t, m.start()) if m else None)
    if ay and re.match(r"^\d{4}-\d{2}$", ay):
        y = int(ay[:4])
        out["previous_year"] = _field(f"{y - 1}-{str(y)[2:]}", "Derived from AY (FY = AY minus one year)",
                                      note="Derived, not stated in notice")
    else:
        out["previous_year"] = _field(None)

    m = _AUTHORITY_RX.search(t)
    out["issuing_authority"] = _field(m.group(0).strip()[:160] if m else None, _line_of(t, m.start()) if m else None)

    d, src = _first_date_near(t, [r"\bdated\b", r"\bdate of (?:issue|notice)\b", r"^\s*date\s*[:\-]"], 60)
    out["date_of_issue"] = _field(d.isoformat() if d else None, src)
    ds, src = _first_date_near(t, [r"served on", r"date of service", r"service date"], 60)
    out["date_of_service"] = _field(ds.isoformat() if ds else None, src)

    # Deadline — never guessed
    dl, src = _first_date_near(t, [r"on or before", r"not later than", r"latest by", r"due date", r"compliance date",
                                   r"response (?:due|by)", r"submit .{0,40}? by"], 80)
    within = re.search(r"(?i)within\s+(\d{1,3})\s+days", t)
    note = "MANDATORY: verify compliance deadline against the e-proceedings portal and the notice itself."
    if dl:
        out["compliance_deadline"] = _field(dl.isoformat(), src, True, note)
    elif within:
        n = int(within.group(1))
        indicative = None
        if ds:
            indicative = (ds + timedelta(days=n)).isoformat()
        out["compliance_deadline"] = _field(
            f"Within {n} days" + (f" (indicative {indicative}, from extracted service date)" if indicative else " of service — service date NOT PROVIDED"),
            _line_of(t, within.start()), True, note)
    else:
        out["compliance_deadline"] = _field(None, None, True, note)

    sec_key = sec or ""
    nature = SECTION_NATURE_1961.get(sec_key) or SECTION_NATURE_1961.get(re.sub(r"\([a-z]+\)$", "", sec_key))
    limited = bool(re.search(r"(?i)limited\s+scrutiny", t))
    complete = bool(re.search(r"(?i)complete\s+scrutiny", t))
    if nature and limited:
        nature += " — LIMITED SCRUTINY"
    elif nature and complete:
        nature += " — COMPLETE SCRUTINY"
    out["nature"] = _field(nature, f"Mapped from section {sec_key} (1961 Act numbering) — confirm against applicable Act" if nature else None)
    out["scrutiny_scope"] = _field("LIMITED" if limited else "COMPLETE" if complete else None)
    base_nature = SECTION_NATURE_1961.get(sec_key) or SECTION_NATURE_1961.get(re.sub(r"\([a-z]+\)$", "", sec_key))
    out["notice_type"] = _field(base_nature, f"Mapped from section {sec_key} — confirm" if base_nature else None, True)

    cons = []
    for m in re.finditer(r"(?i)[^\n.]*(?:penalty|ex[- ]parte|best judg(?:e)?ment|section\s*144\b|272A|prosecution|failure to comply|non[- ]compliance)[^\n.]*", t):
        s = m.group(0).strip()
        if s and s not in cons:
            cons.append(s[:240])
    out["non_compliance_consequences"] = _field("; ".join(cons[:5]) if cons else None, None, True)
    out["documents_requested"] = _field("; ".join(i["text"][:120] for i in split_queries(t)[:15]) or None, None, True,
                                        "See issue-wise list")
    return out


_ITEM_RX = re.compile(r"(?m)^\s*(?:\(?(\d{1,2}|[ivxlc]{1,5}|[a-z])[.)]\s+|Q\.?\s?(\d{1,2})[.:)]\s*|Query\s+(\d{1,2})[.:)\s]\s*)(.+)$", re.I)


# A short stand-alone heading line: starts with a capital, no closing punctuation, few words.
_SECTION_HEADING_RX = re.compile(r"^(?:[A-Z][A-Za-z&/\-]*)(?:\s+[A-Za-z&/\-]+){0,5}$")


def split_queries(text: str) -> list[dict]:
    """Split the notice into actual concerns, keeping evidence sub-points with
    their parent query. Lettered records requested under a numbered query are
    not independent assessment issues."""
    lines = (text or "").splitlines()
    numbered: list[dict] = []
    loose: list[dict] = []
    current = None
    latest_numbered = None
    for line in lines:
        m = _ITEM_RX.match(line)
        if m:
            label = m.group(1) or m.group(2) or m.group(3)
            body = m.group(4).strip()
            if len(body) < 15:  # likely a heading/list fragment
                current = None
                continue
            if str(label).isdigit():
                # A numbered list introduced after a request ending in ':' is
                # usually a document checklist belonging to that same query.
                nested_number = bool(latest_numbered and latest_numbered["text"].rstrip().endswith(":"))
                if nested_number:
                    latest_numbered["text"] += f"\n{label}. {body}"
                    current = latest_numbered
                else:
                    # A short line without closing punctuation ("4. Trade creditors of ₹9,80,000") is the
                    # query's own heading: keep it as the title and collect the question wording beneath it.
                    if len(body) <= 110 and not re.search(r"[.:;?]$", body):
                        current = {"label": label, "title": body, "text": ""}
                    else:
                        current = {"label": label, "title": None, "text": body}
                    numbered.append(current)
                    latest_numbered = current
            elif latest_numbered is not None:
                # Lettered paragraphs (a), (b), … commonly enumerate records
                # requested for the immediately preceding numbered concern.
                latest_numbered["text"] += f"\n{label}. {body}"
                current = latest_numbered
            else:
                current = {"label": label, "text": body}
                loose.append(current)
        elif current is not None:
            if not line.strip():
                if current.get("title") and not current["text"]:
                    continue  # blank line between a heading and its wording
                current = None
            elif current["text"] and _SECTION_HEADING_RX.match(line.strip()):
                current = None  # a new unnumbered section ("Submission instructions") ends the query
            elif len(current["text"]) < 5000:
                current["text"] = (current["text"] + " " + line.strip()).strip()
    items = numbered if numbered else loose
    for i in items:
        i.setdefault("title", None)
        if not i["text"].strip() and i["title"]:  # a one-line query: the heading is the query
            i["text"], i["title"] = i["title"], None
    # V3: cut closing matter (consequences, signature) off the last query; it is not part of any question
    tail = re.compile(r"(?i)\s+(?:in case of (?:failure|non[- ]?compliance|default)|failing which|please note that non[- ]?compliance|"
                      r"assessment unit\b|yours faithfully|\(signature\)|this notice is (?:digitally|electronically) (?:signed|generated)|"
                      r"submission instructions|digitally issued)")
    for i in items:
        m = tail.search(i["text"])
        if m and m.start() > 20:
            i["text"] = i["text"][:m.start()].rstrip()
    # keep only items that look like requests/queries
    req = re.compile(r"(?i)(explain|furnish|provide|submit|justify|source|details|produce|reconcil|evidence|why|copy|confirm|substantiat)")
    out = [i for i in items if req.search(i["text"])]
    # V3: when the notice has a numbered list of queries, a lettered "issues identified" summary is not a separate query
    numbered = [i for i in out if str(i["label"]).isdigit()]
    if len(numbered) >= 2:
        out = numbered
    return out
