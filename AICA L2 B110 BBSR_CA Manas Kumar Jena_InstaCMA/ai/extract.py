"""
AI-assisted reading of financial statements.

read_page(): sends one page (text, plus the page image when it is scanned) to
the chosen model and gets back every line with its amount for each year
column, its statement (P&L / BS) and, for P&L expenses, whether it sits in the
Trading account or the Profit & Loss account.

suggest_heads(): asks the model for the CMA head of lines the keyword rules
could not place.
"""
from ai.providers import call_with_backup, parse_json, AIError
from core.models import SourceLine

SYSTEM = ("You read Indian financial statements (Trading and Profit & Loss account, Income & Expenditure account, "
          "Balance Sheet; T-form or Schedule III vertical) for a Chartered Accountant. You return data only, as "
          "JSON, never commentary. Amounts are numbers in rupees without commas; brackets mean negative.")

PROMPT = """Read this page and return a JSON array. One object per line item that carries an amount:
{"statement": "PL" or "BS",
 "label": exact text of the line as printed (no 'To'/'By'),
 "section": for PL expense lines "trading" (above Gross Profit) or "pl" (below Gross Profit); otherwise "",
 "amounts": {"<financial year e.g. 2025-26>": number, ...}}

Rules:
- Give one amount per year column shown (current and previous year columns).
- Skip totals, sub-totals, "Gross Profit c/d / b/d", headings and blank lines, but DO include
  "Net Profit" (as label "Net Profit") so it can be checked.
- In the capital account give "Opening Capital", "Add: Net Profit", "Less: Drawings", "Capital Introduced"
  and the closing capital as "Capital Account" separately when shown.
- For fixed assets give the closing written-down value of each asset (net of depreciation) as one line.
- If the year is shown as 'year ended 31st March 2026' use "2025-26".
%s
PAGE TEXT:
%s"""

HEADS_PROMPT = """Classify each line of an Indian business's financial statement into one CMA head.
Allowed heads (key: meaning):
%s
Return a JSON object {"<line label>": "<head key>"} for these %s lines:
%s"""


def _fy_end(label):
    import re
    m = re.search(r"(20\d{2})\s*[-/]\s*(\d{2,4})", str(label))
    if m:
        a = int(m.group(1))
        return a + 1
    m = re.search(r"(20\d{2})", str(label))
    return int(m.group(1)) if m else None


def read_page(settings, text, image_png=None, src="", hint=""):
    reply = call_with_backup(settings, PROMPT % (hint, (text or "")[:12000]), image_png, SYSTEM)
    data = parse_json(reply)
    out = []
    if isinstance(data, dict):
        data = data.get("lines") or data.get("items") or []
    for d in data:
        try:
            st = "BS" if str(d.get("statement", "PL")).upper().startswith("B") else "PL"
            label = str(d.get("label", "")).strip()
            sec = d.get("section", "") if d.get("section") in ("trading", "pl") else ""
            for yl, amt in (d.get("amounts") or {}).items():
                fy = _fy_end(yl)
                if fy is None or amt in (None, ""):
                    continue
                out.append(SourceLine(year=fy, statement=st, label=label, amount=float(amt), source=src + " (AI)",
                                      section=sec, confidence=0))
        except (TypeError, ValueError, AttributeError):
            continue
    return out


def suggest_heads(settings, lines, allowed):
    """lines: list of SourceLine without a confident head. Sets head + note in place."""
    todo = [ln for ln in lines if (not ln.head or ln.confidence < 70)]
    if not todo:
        return 0
    labels = sorted({"%s|%s" % (ln.statement, ln.label) for ln in todo})
    heads = "\n".join("%s: %s" % (k, v) for k, v in allowed)
    try:
        reply = call_with_backup(settings, HEADS_PROMPT % (heads, len(labels), "\n".join(labels)))
        mp = parse_json(reply)
    except AIError:
        return 0
    keys = {k for k, _ in allowed}
    n = 0
    for ln in todo:
        h = mp.get("%s|%s" % (ln.statement, ln.label)) or mp.get(ln.label)
        if h in keys:
            ln.head, ln.confidence, ln.note = h, 75, "suggested by AI"
            n += 1
    return n
