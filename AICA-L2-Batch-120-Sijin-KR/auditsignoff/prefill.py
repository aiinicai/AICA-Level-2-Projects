"""Pre-fill the engagement fact sheet from trade licence, MOA/AOA, certificate of incorporation, etc.
Class B (assisted): every value comes with its source file, the matching text and a confidence; the reviewer confirms or edits
before the fact sheet is used. Nothing here is trusted silently, and OCR-derived values are always marked Low."""
from __future__ import annotations
import re
from pathlib import Path

from .loaders import load_document
from .models import load_params

LEGAL_MAP = [  # (regex on legal-form text, code)
    (r"free\s*zone\s*establishment|\bFZE\b", "FZE"),
    (r"free\s*zone\s*company|\bFZCO\b|\bFZC\b|\bFZ[- ]LLC\b", "FZC"),
    (r"limited\s+liability\s+partnership|\bLLP\b", "LLP"),
    (r"limited\s+liability\s+company|\bL\.?L\.?C\.?\b", "LLC"),
    (r"sole\s+proprietor|individual\s+establishment|\bsole\b", "SOLE"),
    (r"civil\s+(company|work)", "CIVIL"),
]
AUTH_EMIRATE = {"DMCC": "Dubai", "DED": "Dubai", "DET": "Dubai", "DSO": "Dubai", "JAFZA": "Dubai", "DIFC": "Dubai",
                "DAFZA": "Dubai", "DDA": "Dubai", "DIEZ": "Dubai", "DWC": "Dubai", "IFZA": "Dubai", "RAKEZ": "Ras Al Khaimah",
                "ADGM": "Abu Dhabi", "KEZAD": "Abu Dhabi", "SHAMS": "Sharjah"}
AUTH_NAMES = {"DMCC": r"dubai multi commodities", "DSO": r"dubai silicon oasis", "JAFZA": r"jebel ali free zone",
              "DIFC": r"dubai international financial", "DAFZA": r"dubai airport free zone", "DDA": r"dubai development authority",
              "IFZA": r"international free zone authority", "RAKEZ": r"ras al khaimah economic zone", "ADGM": r"abu dhabi global market",
              "KEZAD": r"khalifa economic zones?|kezad", "SHAMS": r"sharjah media city|\bshams\b",
              "DED": r"department of economic development|economy and tourism|\bDET\b|\bDED\b", "DIEZ": r"dubai integrated economic zones?",
              "DWC": r"dubai world central|\bDWC\b"}
MONTHS = "january february march april may june july august september october november december".split()
NAME_END = r"(?:L\.?L\.?C\.?|FZ[- ]?LLC|FZCO|FZC|FZE|DMCC|LLP|PJSC|Limited|LTD\.?|L\.?L\.?C\.?\s*-?\s*(?:SPC|OPC)|\(?(?:Branch)\)?)"
PERSON = r"(?:(?:Mr|Mrs|Ms|Miss|Dr|Sheikh|Eng)\.?\s+)?[A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){1,4}"


def _rows(doc):
    """Every 'label -> value' candidate: table rows and 'Label: value' lines, with a snippet for audit."""
    out = []
    for t in doc.tables:
        for r in t.rows:
            cells = [c.strip() for c in r if c and c.strip()]
            for i in range(len(cells) - 1):
                out.append((cells[i], cells[i + 1], " | ".join(cells)))
    lines = [ln.strip() for ln in doc.all_text.splitlines() if ln.strip()]
    for i, ln in enumerate(lines):
        m = re.match(r"^([A-Za-z][A-Za-z0-9 ./()&'-]{1,50}?)\s*[:\-–]\s*(.+)$", ln)
        if m:
            out.append((m.group(1), m.group(2), ln))
        elif i + 1 < len(lines) and len(ln) < 45 and not ln.endswith("."):
            out.append((ln, lines[i + 1], ln + " / " + lines[i + 1]))     # label on one line, value on the next
    return out, lines


def _find(rows, label_rx):
    rx = re.compile(label_rx, re.I)
    return [(v, snip) for lab, v, snip in rows if rx.search(lab)]


def _clean(v):
    return re.sub(r"\s+", " ", v).strip(" .:-|")


def _people(text):
    """Names from a cell/line such as 'Mr. Ali Khan (UAE), Ms Sara Noor' or 'Ali Khan - 60%; Sara Noor - 40%'."""
    text = re.sub(r"\([^)]*\)|\d+(\.\d+)?\s*%|\bholding\b.*|\bshares?\b.*|\bnational(ity)?\b.*", "", text, flags=re.I)
    parts = re.split(r"[;,\n]|\band\b|&|\d+[.)]\s", text)
    names = []
    for p in parts:
        p = _clean(re.sub(r"^(Mr|Mrs|Ms|Miss|Dr|Sheikh|Eng)\.?\s+", "", _clean(p), flags=re.I))
        if re.fullmatch(r"[A-Za-z][A-Za-z'.-]+(?:\s+[A-Za-z][A-Za-z'.-]+){1,5}", p) and not re.search(r"company|limited|llc|authority|licen[cs]e|manager|owner", p, re.I):
            names.append(p)
    return names


def extract_from_document(path):
    """-> list of dict(field, value, source, confidence, snippet) for ONE file."""
    doc = load_document(path)
    ocr = doc.kind in ("image", "scan")
    rows, lines = _rows(doc)
    text = re.sub(r"[ \t]+", " ", doc.all_text)
    fname = Path(path).name
    res = []

    def add(field, value, snip, conf="Medium"):
        if value in (None, "", []):
            return
        if ocr:
            conf = "Low"
        res.append({"field": field, "value": value, "source": fname, "confidence": conf, "snippet": snip[:160]})

    # company name
    got = _find(rows, r"^(company|trade|licen[cs]e|business|establishment|legal)\s*(name)?$|name of (the )?company|company name|trade name")
    for v, snip in got:
        v = _clean(v)
        if re.search(NAME_END, v, re.I) and len(v) < 90:
            add("client.name", v, snip, "High")
            break
    else:
        m = re.search(r"^\s*([A-Z0-9][A-Za-z0-9 &.,'-]{2,70}?\s" + NAME_END + r")\s*$", text, re.M)
        if m:
            add("client.name", _clean(m.group(1)), m.group(0), "Low")

    # legal form
    for v, snip in _find(rows, r"legal\s*(type|form|status)|company type|entity type|type of (company|licen[cs]e)|form of"):
        for rx, code in LEGAL_MAP:
            if re.search(rx, v, re.I):
                add("client.legal_status", code, snip, "High"); break
        if any(r["field"] == "client.legal_status" for r in res):
            break
    if not any(r["field"] == "client.legal_status" for r in res):
        nm = next((r["value"] for r in res if r["field"] == "client.name"), "")
        for rx, code in LEGAL_MAP:
            if re.search(rx, nm + " " + text[:1500], re.I):
                add("client.legal_status", code, "inferred from company name / document header", "Low"); break

    # authority / emirate
    hit = None
    for code, rx in AUTH_NAMES.items():
        if re.search(rx, text, re.I):
            hit = code; break
    if not hit:
        for code in load_params().get("authority_tokens", []):
            if re.search(rf"\b{code}\b", text):
                hit = code; break
    if hit:
        add("client.authority", hit, f"authority text found in {fname}", "Medium")
        add("client.emirate", AUTH_EMIRATE.get(hit, ""), f"derived from {hit}", "Low")
    for v, snip in _find(rows, r"^emirate$"):
        add("client.emirate", _clean(v), snip, "Medium"); break

    # shareholders / owners / partners
    names, snips = [], []
    for v, snip in _find(rows, r"share\s*holders?|partners?|owners?|members?|first party|subscribers?"):
        nn = _people(v)
        if nn:
            names += nn; snips.append(snip)
    for m in re.finditer(r"(?:^|\n)\s*(?:\d+[.)]\s*)?((?:Mr|Mrs|Ms|Miss|Dr)\.?\s+[A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){1,4})\s*[,(–-]?[^\n]{0,80}(?:shares?|%)", text):
        names += _people(m.group(1)); snips.append(m.group(0).strip())
    names = list(dict.fromkeys(names))
    if names:
        add("client.shareholders", "; ".join(names), snips[0] if snips else "", "Medium")

    # legal signatories: manager / director / authorised signatory
    sig = []
    for v, snip in _find(rows, r"manager|director|authori[sz]ed\s*(signator|person)|signator|general manager"):
        sig += _people(v)
    sig = list(dict.fromkeys(sig))
    if sig:
        add("client.signatories_legal", "; ".join(sig), "manager/director/signatory fields", "Medium")

    # year end
    m = re.search(r"(?:financial|fiscal)\s+year[^.\n]{0,80}?(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(MONTHS) + r")", text, re.I)
    if m:
        add("client.year_end", f"{int(m.group(1))} {m.group(2).title()}", m.group(0), "Medium")

    # incorporation / issue year -> allowed_years
    for v, snip in _find(rows, r"(date of )?(incorporation|registration|establishment)|(original|initial|first)\s*issue|issue date|licen[cs]e issue"):
        y = re.search(r"(19|20)\d{2}", v)
        if y:
            add("allowed_years", y.group(0), snip, "Medium"); break

    # info-only (not scored): licence number / expiry
    for v, snip in _find(rows, r"licen[cs]e\s*(no|number)|registration\s*(no|number)|commercial licen[cs]e"):
        if re.search(r"\d{3,}", v):
            add("info.licence_no", _clean(v), snip, "Medium"); break
    for v, snip in _find(rows, r"expiry|expiration|valid (till|until|to)"):
        add("info.licence_expiry", _clean(v), snip, "Medium"); break
    return res


def prefill(paths):
    """Merge several documents. When files disagree, the higher-confidence value wins and the conflict is listed."""
    rank = {"High": 3, "Medium": 2, "Low": 1}
    best, conflicts, alts = {}, [], {}
    for p in paths:
        for r in extract_from_document(p):
            k = r["field"]
            alts.setdefault(k, []).append(r)
            if k not in best or rank[r["confidence"]] > rank[best[k]["confidence"]]:
                best[k] = r
    for k, lst in alts.items():
        vals = {re.sub(r"\W+", "", str(x["value"]).lower()) for x in lst}
        if len(vals) > 1:
            conflicts.append({"field": k, "values": [f'{x["value"]} ({x["source"]})' for x in lst]})
    return list(best.values()), conflicts


def rows_to_engagement(rows, fy, overrides=None):
    """Build the fact-sheet dict (same shape as load_input) from reviewed rows."""
    from .inputs import ENG_FIELDS, _convert, _set
    vals = {r["field"]: r["value"] for r in rows}
    vals.update(overrides or {})
    vals["fy"] = fy
    out = {}
    for key, ex, _, kind in ENG_FIELDS:
        if key.startswith("review_log"):
            v = {"done": "No"}.get(key.rsplit(".", 1)[1], "") if key.endswith("done") else ""
        else:
            v = vals.get(key, "")
        if key == "py":
            v = int(fy) - 1
        if key == "br_on_file" and v in ("", None):
            v = "No"
        _set(out, key, _convert(v, kind) if v not in ("", None) or kind in ("list", "intlist", "str", "bool") else None)
    for v in out["review_log"].values():
        v.pop("date", None) if not v.get("date") else None
    return out


def write_fact_sheet_xlsx(eng, path):
    from .inputs import dict_to_xlsx
    dict_to_xlsx(eng, path, "engagement")
