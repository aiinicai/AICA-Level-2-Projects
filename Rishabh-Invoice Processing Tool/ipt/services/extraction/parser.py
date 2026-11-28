"""Rule-based invoice field parser.

Input: visual lines (from the PDF text layer or OCR). Output: a dict of fields
plus a confidence (0-1) per field. A field that cannot be read is simply absent;
nothing is guessed. Derived values (e.g. state code taken from a GSTIN) get a
lower confidence so the review screen shows them in amber.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from ipt.core.gstin import normalize, repair_ocr_gstin, validate_gstin
from ipt.core.money import to_decimal
from ipt.core.states import STATES
from ipt.core.textnorm import parse_date
from ipt.services.extraction.layout import Line, Word, split_segments

GSTIN_RE = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z][A-Z0-9][0-9A-Z])\b")
PAN_RE = re.compile(r"\b([A-Z]{5}\d{4}[A-Z])\b")
# an amount: optional currency marker, digits with Indian/intl grouping, optional decimals.
# Numbers directly followed by % are rates, not amounts.
# A number must not be cut out of a longer one ('2' from '2.5%') and must not be a rate ('2.50 %').
AMOUNT_RE = re.compile(r"(?<![\w.])(?:₹|Rs\.?|INR)?\s*(-?\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|-?\d+(?:\.\d{1,2})?)"
                       r"(?!\d|[.,]\d|\s*%)")
_YEAR = r"(?:(?:19|20)\d{2}|\d{2})"
DATE_RE = re.compile(rf"(?<![\d/])(\d{{1,2}}[-/.]\d{{1,2}}[-/.]{_YEAR}(?![\d/])|\d{{4}}-\d{{2}}-\d{{2}}|"
                     rf"\d{{1,2}}[-. ]?[A-Za-z]{{3,9}}[-. ,]+{_YEAR})")

HIGH, MEDIUM, GUESS, LOW = 0.95, 0.75, 0.65, 0.55


@dataclass
class ParsedInvoice:
    fields: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)
    items: list[dict] = field(default_factory=list)
    item_confidence: float = 0.0

    def put(self, name: str, value, conf: float) -> None:
        if value is None or value == "":
            return
        if name not in self.fields:  # first (highest-priority) rule wins
            self.fields[name] = value
            self.confidence[name] = round(conf, 2)


def _clean_currency_glyphs(text: str) -> str:
    # Some PDFs map the rupee sign to a stray letter ('I' or '`'); strip it before amounts.
    return re.sub(r"(?<![A-Za-z])[I`](?=\s*-?\d)", "", text)


def _amounts(text: str) -> list[Decimal]:
    out = []
    for m in AMOUNT_RE.finditer(_clean_currency_glyphs(text)):
        d = to_decimal(m.group(1))
        if d is not None:
            out.append(d)
    return out


def _below(lines: list[Line], i: int) -> Line | None:
    """The nearest following segment that sits under segment i (overlapping horizontally)."""
    cur = lines[i]
    for nxt in lines[i + 1:i + 8]:
        if nxt.page != cur.page or nxt.y <= cur.y + 1:
            continue
        if nxt.x0 < cur.x1 + 10 and nxt.x1 > cur.x0 - 10:
            return nxt
    return None


def _right_of(lines: list[Line], i: int, max_gap: float = 160) -> Line | None:
    """The segment on the same visual line just right of segment i (label .... value)."""
    cur = lines[i]
    best = None
    for k, sg in enumerate(lines):
        if k == i or sg.page != cur.page or abs(sg.y - cur.y) > 3.5 or sg.x0 < cur.x1:
            continue
        if sg.x0 - cur.x1 <= max_gap and (best is None or sg.x0 < best.x0):
            best = sg
    return best


def _label_span(seg: Line, m: re.Match) -> tuple[float, float]:
    """x-range of the words that make up a label match inside a segment
    ('Invoice No.  e-Way Bill No.  Dated' -> just 'Dated')."""
    pos, xs = 0, []
    for w in seg.words:
        start, end = pos, pos + len(w.text)
        if end > m.start() and start < m.end():
            xs.append((w.x0, w.x1))
        pos = end + 1
    return (min(a for a, _ in xs), max(b for _, b in xs)) if xs else (seg.x0, seg.x1)


def _below_span(lines: list[Line], i: int, x0: float, x1: float) -> Line | None:
    cur = lines[i]
    best = None
    for nxt in lines[i + 1:i + 12]:
        if nxt.page != cur.page or nxt.y <= cur.y + 1:
            continue
        if best is not None and nxt.y > best.y + 3.5:
            break
        if nxt.x0 < x1 + 10 and nxt.x1 > x0 - 10:
            if best is None or abs(nxt.x0 - x0) < abs(best.x0 - x0):
                best = nxt
    return best


def _candidates(lines: list[Line], i: int, label_re: re.Pattern) -> list[str]:
    """Possible value texts for a label, in order: after the label in the same segment,
    the segment to its right, the segment directly below the label word(s) (Tally-style boxes)."""
    out = []
    m = label_re.search(lines[i].text)
    rest = lines[i].text[m.end():].strip(" :-#.") if m else ""
    if rest:
        out.append(rest)
    right = _right_of(lines, i)
    if right is not None and not re.search(r"[A-Za-z ]{3,}:\s*$", right.text):
        out.append(right.text.strip())
    if m:
        under = _below_span(lines, i, *_label_span(lines[i], m))
        if under is not None:
            out.append(under.text.strip())
    nxt = _below(lines, i)
    if nxt is not None and nxt.text.strip() not in out:
        out.append(nxt.text.strip())
    return out


def _after_label(lines: list[Line], i: int, label_re: re.Pattern) -> str:
    c = _candidates(lines, i, label_re)
    return c[0] if c else ""


def _find_label(lines, pattern: str, value_re: re.Pattern | None = None, start: int = 0):
    """Yield (line index, value text) for lines matching a label pattern. With value_re,
    the first candidate (same segment / right / below) that matches it is used."""
    lab = re.compile(pattern, re.I)
    for i in range(start, len(lines)):
        if lab.search(lines[i].text):
            cands = _candidates(lines, i, lab)
            if value_re is None:
                if cands:
                    yield i, cands[0]
                continue
            for c in cands:
                m = value_re.search(c)
                if m:
                    yield i, m.group(1)
                    break


def _amount_for(lines, pattern: str, base_conf: float):
    """Amount on the label's line (last amount after the label), else the next line."""
    lab = re.compile(pattern, re.I)
    for i, ln in enumerate(lines):
        m = lab.search(ln.text)
        if not m:
            continue
        nums = _amounts(ln.text[m.end():])
        right = _right_of(lines, i)
        if not nums and right is not None and not re.search(r"[A-Za-z]{4,}", right.text):
            nums = _amounts(right.text)
        nxt = _below(lines, i)
        if not nums and nxt is not None and not re.search(r"[A-Za-z]{4,}", nxt.text):
            nums = _amounts(nxt.text)
        if nums:
            return nums[-1], base_conf
    return None, 0


# --------------------------------------------------------------------------- header
def parse_header(lines: list[Line], out: ParsedInvoice, base: float, company_gstin: str | None) -> None:
    text = "\n".join(ln.text for ln in lines)
    upper = text.upper()

    # document type
    for pat, kind in ((r"\bCREDIT\s+NOTE\b", "credit_note"), (r"\bDEBIT\s+NOTE\b", "debit_note"),
                      (r"\bBILL\s+OF\s+SUPPLY\b", "bill_of_supply"), (r"\bTAX\s+INVOICE\b", "tax_invoice"),
                      (r"\bINVOICE\b", "tax_invoice")):
        if re.search(pat, upper):
            out.put("doc_type", kind, base if kind != "tax_invoice" or "TAX" in upper else MEDIUM)
            break

    # GSTINs: the company's own GSTIN is the buyer; otherwise the first GSTIN is the supplier
    own = normalize(company_gstin) if company_gstin else None
    buyer_zone = None
    for i, ln in enumerate(lines):
        if re.search(r"bill(ed)?\s*to|buyer|customer|consignee|ship(ped)?\s*to|recipient", ln.text, re.I) \
                and not re.search(r"original|duplicate|triplicate|for\s+recipient", ln.text, re.I):
            buyer_zone = i
            break
    found = []
    repaired: set[str] = set()
    for i, ln in enumerate(lines):
        hits = [m.group(1) for m in GSTIN_RE.finditer(ln.text.upper().replace(" ", ""))]
        if not hits:
            lab = re.search(r"GSTIN|GST\s*NO|GSTIN/UIN|GSTI\s*N", ln.text, re.I)
            if lab:
                fixed = repair_ocr_gstin(ln.text[lab.end():lab.end() + 30])
                if fixed:
                    hits, _ = [fixed], repaired.add(fixed)
        if not hits and base < HIGH:
            # a GSTIN printed without its label: a 15/16-character token shaped like one
            for tok in re.findall(r"[A-Za-z0-9@!|]{15,16}", ln.text):
                if sum(c.isalpha() for c in tok[2:7]) >= 4 and sum(c.isdigit() for c in tok[7:11]) >= 3:
                    fixed = repair_ocr_gstin(tok)
                    if fixed:
                        hits, _ = [fixed], repaired.add(fixed)
                        break
        found += [(i, g) for g in hits]
    def _looks_like_own(g: str) -> bool:
        # an OCR-damaged copy of the company's own GSTIN (same PAN except 1-2 characters) is the buyer,
        # never the supplier - even if a "repair" turned it into another valid-looking GSTIN
        return bool(own) and g != own and sum(a != b for a, b in zip(g[2:12], own[2:12])) <= 2

    for i, g in found:
        if own and (g == own or _looks_like_own(g)):
            out.put("buyer_gstin", own, base if g == own else LOW)
        elif buyer_zone is not None and i > buyer_zone and "supplier_gstin" in out.fields:
            out.put("buyer_gstin", g, base * 0.9)
        else:
            out.put("supplier_gstin", g, base if (buyer_zone is None or i < buyer_zone) else MEDIUM)
    for key in ("supplier_gstin", "buyer_gstin"):
        if out.fields.get(key) in repaired:
            out.confidence[key] = round(out.confidence[key] * 0.9, 2)  # repaired from OCR: please verify
    if "supplier_gstin" in out.fields:
        g = out.fields["supplier_gstin"]
        out.put("supplier_state_code", g[:2], base * 0.9)
        out.put("supplier_pan", g[2:12], base * 0.9)
    if "buyer_gstin" in out.fields:
        out.put("buyer_state_code", out.fields["buyer_gstin"][:2], base * 0.9)
    for _, val in _find_label(lines, r"\bPAN\b\s*(no\.?)?\s*:?", PAN_RE):
        out.put("supplier_pan", val, base)
        break

    # supplier name: a line with a business suffix before the buyer block, else the first clean line
    limit = buyer_zone if buyer_zone is not None else min(len(lines), 25)
    for ln in lines[:limit]:
        t = ln.text.strip(" |:")
        if re.search(r"\b(PVT|PRIVATE|LIMITED|LTD|LLP|TRADERS|ENTERPRISES|INDUSTRIES|COMPANY|CORPORATION|"
                     r"MINERALS|CHEMICALS|AGENCIES|SOLUTIONS|& CO)\b", t, re.I) and not re.search(
                         r"gstin|bank|a/c|holder|for |declare", t, re.I) and len(t) < 70:
            t = re.sub(r"\s*\(\d{2}\W\d{2}\)?\W*$", "", t)
            t = re.sub(r"^[^A-Za-z]*[a-z]*[^A-Za-z\s]+\)?\s+(?=[A-Z])", "", t)
            out.put("supplier_name", t, GUESS)
            break
    for ln in ([] if "supplier_name" in out.fields else sorted(lines[:10], key=lambda s: (s.y, s.x0))):
        t = ln.text.strip()
        if t and not re.search(r"invoice|gstin|phone|email|page|original|duplicate|copy|recipient|\bdated\b|"
                               r"\bno\.|\bdate\b|e-way|irn|\back\b", t, re.I) \
                and len(t) > 3 and not re.search(r"\d{3,}", t) and re.search(r"[A-Za-z]{4,}", t):
            out.put("supplier_name", t, GUESS if base >= HIGH else LOW)   # first line of a scan: a guess
            break
    # buyer name: the first line after "Billed to"/"Buyer" that is not a label
    if buyer_zone is not None:
        for ln in lines[buyer_zone + 1: buyer_zone + 4]:
            t = ln.text.strip()
            if t and not re.search(r"details|address|gstin|mobile|phone|state|place of supply", t, re.I):
                out.put("buyer_name", t, GUESS)
                break

    # invoice number and date
    inv_no_re = re.compile(r"\b([A-Z0-9][A-Z0-9/\-_.#]{0,40})", re.I)
    lab = INV_NO_LABEL_OCR if base < HIGH else r"\b(invoice|inv|bill|document|doc)\.?\s*(no|number|#)\.?"
    for i, _ in _find_label(lines, lab):
        if re.search(r"(dispatch|despatch|delivery|order|lading)\s*(doc|note)?\s*(no|number)", lines[i].text, re.I) \
                and not re.search(r"invoice|inv\b", lines[i].text, re.I):
            continue
        # first candidate (same segment / right / below) that looks like a number: contains a digit
        val = next((m.group(1) for c in _candidates(lines, i, re.compile(lab, re.I))
                    for m in [inv_no_re.search(c)] if m and _looks_like_invoice_no(m.group(1))), None)
        if val:
            out.put("invoice_no", val.strip(".-"), base)
            break
    date_lab = re.compile(r"\b(invoice|inv|bill)\.?\s*(\w\s+)?date\b|\bdate of (invoice|issue)\b|\bdated\b", re.I)
    for i, ln in enumerate(lines):
        if not date_lab.search(ln.text) or re.search(r"delivery|order|ack|due|lading|lr", ln.text, re.I):
            continue
        d = next((d for c in _candidates(lines, i, date_lab) for m in DATE_RE.finditer(c)
                  for d in [parse_date(m.group(1))] if d), None)
        if d:
            out.put("invoice_date", d, base)
            break
    if "invoice_date" not in out.fields:
        # only one date printed in the header (ignoring e-invoice / LR / order dates): use it, flagged
        top = [ln for ln in lines if ln.page == lines[0].page][:60]
        dates = {d for ln in top if not re.search(r"\back\b|\blr\b|lading|order|due|dt\.|delivery", ln.text, re.I)
                 for m in DATE_RE.finditer(ln.text) for d in [parse_date(m.group(1))] if d}
        if len(dates) == 1:
            out.put("invoice_date", dates.pop(), LOW)
    # Tally prints 'Reference No. & Date: <voucher no> dt. <date>' - normally the invoice number itself.
    ref = next((m for ln in lines[:80] for m in [TALLY_REF_RE.search(ln.text)]
                if m and _looks_like_invoice_no(m.group(1))), None)
    if ref and base < HIGH:
        ref_no, d = ref.group(1).strip(".-"), parse_date(ref.group(2))
        same_day = d is not None and d == out.fields.get("invoice_date")
        cur = out.fields.get("invoice_no")
        if cur is None:
            # used only when the invoice-number label could not be read; checked against the invoice date
            out.put("invoice_no", ref_no, GUESS if same_day else LOW)
        elif cur != ref_no:
            # two OCR readings of the same number disagree: a valid financial-year pair ('26-27') decides,
            # otherwise the user must check
            fy_ok = [v for v in (cur, ref_no) if _has_fy_pair(v)]
            if len(fy_ok) == 1 and same_day:
                out.fields["invoice_no"], out.confidence["invoice_no"] = fy_ok[0], GUESS
            else:
                out.confidence["invoice_no"] = min(out.confidence["invoice_no"], LOW)

    # place of supply (state code or state name)
    for i, val in _find_label(lines, r"place\s+of\s+supply"):
        window = " ".join(ln.text for ln in lines[i:i + 3])
        code = re.search(r"(?:state\s*code|code)\s*[:\-]?\s*(\d{2})\b", window, re.I) or \
            re.search(r"place\s+of\s+supply\s*[:\-]?\s*(\d{2})\b", window, re.I)
        if code and code.group(1) in STATES:
            out.put("place_of_supply", code.group(1), base)
        else:
            for c, st in STATES.items():
                if re.search(r"\b" + re.escape(st.name) + r"\b", window, re.I):
                    out.put("place_of_supply", c, MEDIUM)
                    break
        break

    if "place_of_supply" not in out.fields:
        # not printed: goods are supplied where the buyer is - the state code printed in the buyer block
        # ('State Name: Rajasthan, Code: 08'), else the state of the buyer's GSTIN. Marked as a guess.
        # The state NAME outranks the 2-digit code (OCR confuses 08/06/03); both must agree with the buyer's
        # GSTIN state, otherwise the guess is marked for checking.
        code, named = None, None
        if buyer_zone is not None:
            for ln in lines[buyer_zone: buyer_zone + 12]:
                m = re.search(r"\bcode\s*[:\-]?\s*(\d{2})\b", ln.text, re.I)
                if not m:
                    continue
                code = m.group(1) if m.group(1) in STATES else code
                for c, st in STATES.items():
                    if re.search(r"\b" + re.escape(st.name) + r"\b", ln.text, re.I):
                        named = c
        gst_state = out.fields.get("buyer_gstin", "")[:2]
        pick = named or code or (gst_state if gst_state in STATES else None)
        if pick:
            agree = {x for x in (named, code, gst_state if gst_state in STATES else None) if x}
            out.put("place_of_supply", pick, GUESS if len(agree) == 1 else LOW)

    for _, val in _find_label(lines, r"reverse\s+charge", re.compile(r"\b(yes|no|y|n)\b", re.I)):
        out.put("reverse_charge", val.lower().startswith("y"), base)
        break
    irn = re.search(r"\b([0-9a-f]{64})\b", text, re.I)
    if irn:
        out.put("irn", irn.group(1).lower(), base)
    for _, val in _find_label(lines, r"\back\.?\s*(no|number)", re.compile(r"(\d{10,20})")):
        out.put("ack_no", val, base)
        break
    for _, val in _find_label(lines, r"e[\s\-]?way\s*bill\s*(no|number)?", re.compile(r"(\d{12})")):
        out.put("eway_bill_no", val, base)
        break
    for _, val in _find_label(lines, r"\b(p\.?o\.?|purchase\s+order)\s*(no|number)", inv_no_re):
        out.put("po_no", val, base * 0.9)
        break
    for _, val in _find_label(lines, r"amount\s+(chargeable\s+)?in\s+words"):
        if re.search(r"rupee|only", val, re.I):
            out.put("amount_in_words", val, base)
        break
    cur = re.search(r"\b(USD|EUR|GBP|AED|SGD|JPY)\b", upper)
    out.put("currency", cur.group(1) if cur else "INR", base if cur else MEDIUM)


# --------------------------------------------------------------------------- totals
TOTAL_RULES = [
    ("taxable_total", r"(total\s+)?taxable\s*(value|amount|sub\s*total|subtotal)|sub\s*-?\s*total"),
    ("cgst", r"\bCGST\b"),
    ("sgst", r"\b(SGST|UTGST)\b"),
    ("igst", r"\bIGST\b"),
    ("cess", r"\bcess\b"),
    ("freight", r"\bfreight\b|\bcartage\b"),
    ("packing", r"\bpacking\b|\bforwarding\b"),
    ("round_off", r"round(ed|ing)?\s*off"),
    ("tds", r"\bTDS\b"),
    ("tcs", r"\bTCS\b"),
    ("invoice_total", r"amount\s+chargeable(?!\s*\(in\s+words)|grand\s+total|invoice\s+(total|value)|total\s+invoice\s+value|net\s+(payable|amount)|"
                      r"amount\s+payable|total\s+amount(?!\s+in\s+words)"),
]


def _tally_totals(lines: list[Line], out: ParsedInvoice, base: float) -> None:
    """Tally-printed invoices: the first 'Total' row carries the invoice total (last amount);
    the HSN summary's 'Total' row starts with the taxable value."""
    hsn_header = None
    for i, ln in enumerate(lines):
        t = ln.text.strip()
        if re.search(r"HSN/?SA[CG]", t, re.I) and re.search(r"taxable", t, re.I):
            hsn_header = i
        elif re.match(r"^total\b", t, re.I):
            nums = _amounts(t)
            if hsn_header is not None and i > hsn_header and len(nums) >= 3:
                out.put("taxable_total", nums[0], base * 0.95)
            elif hsn_header is None and nums and "invoice_total" not in out.fields:
                out.put("invoice_total", nums[-1], base * 0.95)


def parse_totals(lines: list[Line], out: ParsedInvoice, base: float, table_end: int) -> None:
    # Totals are read below the item table so item-level CGST/SGST columns are not mistaken.
    tail = lines[table_end:] if table_end else lines
    _tally_totals(tail, out, base)
    for name, pattern in TOTAL_RULES:
        val, conf = _amount_for(tail, pattern, base)
        if val is not None:
            if name == "round_off":
                out.put(name, val, conf)
            else:
                out.put(name, val, conf)


# --------------------------------------------------------------------------- items
HEADER_KEYS = [
    ("sno", r"^(#|s\.?\s*no\.?|sr\.?\s*no\.?|sl\.?\s*no\.?)$"),
    ("description", r"de?scr\w*|particulars|item|go+ds|gcods|services|product"),   # OCR: 'Descrption of Gcods'
    ("hsn_sac", r"hsn|sac"),
    ("qty", r"^(qty|quantity)"),
    ("unit", r"^(unit|uom|per)$"),
    ("rate", r"^(rate|price|unit\s*price)(?!\s*%)"),
    ("discount", r"disc"),
    ("gst_rate", r"(gst|tax)\s*%|%\s*(gst|tax)|gst\s*rate|tax\s*rate"),
    ("cgst", r"^cgst"),
    ("sgst", r"^(sgst|utgst)"),
    ("igst", r"^igst"),
    ("tax_amount", r"(gst|tax)\s*amt|(gst|tax)\s*amount"),
    ("taxable_value", r"taxable|^amount$|^value$"),
    ("total", r"^total|net\s*amount"),
]
TOTALS_LABEL = re.compile(r"taxable|\bcgst\b|\bsgst\b|\butgst\b|\bigst\b|\bcess\b|round|total|freight|packing|"
                          r"\btcs\b|\btds\b|discount|less|add", re.I)
END_OF_TABLE = re.compile(r"amount\s+in\s+words|sub\s*-?\s*total|taxable\s+sub|grand\s+total|bank\s+details|"
                          r"^total\b|total\s+amount|terms|declaration", re.I)


def _header_columns(words) -> list[tuple[str, float, float]] | None:
    """Group header words (possibly over 2-3 stacked lines) into labelled columns."""
    groups: list[list] = []
    for w in sorted(words, key=lambda w: w.x0):
        if groups and w.x0 <= max(x.x1 for x in groups[-1]) + 4.5:
            groups[-1].append(w)
        else:
            groups.append([w])
    cols = []
    for g in groups:
        g.sort(key=lambda w: (round(w.yc), w.x0))
        label = " ".join(w.text for w in g)
        label_clean = re.sub(r"\((₹|rs\.?|inr|i|`)\)", "", label, flags=re.I).strip()
        for key, pat in HEADER_KEYS:
            if re.search(pat, label_clean, re.I) and key not in [c[0] for c in cols]:
                cols.append((key, min(w.x0 for w in g), max(w.x1 for w in g)))
                break
    keys = {c[0] for c in cols}
    if "description" in keys and len(keys & {"qty", "rate", "taxable_value", "total", "hsn_sac", "gst_rate"}) >= 2:
        return cols
    return None


def _assign(words, cols):
    """Put each word in the column whose span (extended to midpoints) contains it."""
    bounds = []
    for i, (key, x0, x1) in enumerate(cols):
        left = (cols[i - 1][2] + x0) / 2 if i else -1e9
        right = (x1 + cols[i + 1][1]) / 2 if i + 1 < len(cols) else 1e9
        bounds.append((key, left, right))
    cells: dict[str, list[str]] = {}
    for w in words:
        for key, left, right in bounds:
            if left <= w.xc < right:
                cells.setdefault(key, []).append(w.text)
                break
    return {k: " ".join(v) for k, v in cells.items()}


def _num(text: str | None, places: str = "0.01") -> Decimal | None:
    """Number in a table cell. Money keeps 2 decimals; quantities/rates pass places='0.001'/'0.0001'."""
    if not text:
        return None
    t = _clean_currency_glyphs(text).replace("%", "").strip()
    m = re.search(r"-?[\d,]*\.?\d+", t)
    if not m:
        return None
    try:
        return Decimal(m.group(0).replace(",", "")).quantize(Decimal(places))
    except ArithmeticError:
        return None


def _split_words(words: list[Word]) -> list[Word]:
    """OCR engines that return whole phrases ('25210090 28.130 MT', 'HSN/SAC Quantity') are split into single
    words; each gets a share of the box width by its number of characters."""
    out = []
    for w in words:
        parts = w.text.split()
        if len(parts) <= 1:
            out.append(w)
            continue
        per = (w.x1 - w.x0) / max(1, len(w.text))
        pos = w.x0
        for p in parts:
            out.append(Word(p, pos, w.y0, pos + per * len(p), w.y1, w.page))
            pos += per * (len(p) + 1)
    return out


def _unit_next_to_qty(words: list[Word]) -> list[Word]:
    """'29.520' 'MT' split apart again: keep a unit word with the quantity before it."""
    out: list[Word] = []
    for w in words:
        if out and re.fullmatch(r"[A-Za-z]{2,5}", w.text) and re.fullmatch(r"\d+\.\d{2,3}", out[-1].text) \
                and w.x0 - out[-1].x1 < 8:
            p = out[-1]
            out[-1] = Word(f"{p.text} {w.text}", p.x0, p.y0, w.x1, w.y1, p.page)
        else:
            out.append(w)
    return out


def parse_items(lines: list[Line], out: ParsedInvoice, base: float) -> int:
    """Returns the index of the first line after the item table (0 if no table)."""
    lines = [Line(_unit_next_to_qty(_split_words(ln.words)), ln.page) for ln in lines]
    for hi, ln in enumerate(lines):
        # the header may be spread over 2-3 stacked lines (e.g. 'Description of Goods' a little lower than
        # 'HSN/SAC Quantity Rate per Amount', or 'GST Amt' over '(₹)')
        span = [k for k in range(max(0, hi - 2), min(len(lines), hi + 3))
                if k == hi or (abs(lines[k].y - ln.y) <= 9 and lines[k].page == ln.page
                               and not _amounts(lines[k].text.replace("(I)", "")))]
        cols = _header_columns(ln.words) and (_header_columns([w for k in span for w in lines[k].words])
                                              or _header_columns(ln.words))
        if cols is None or cols == []:
            joined = _header_columns([w for k in span for w in lines[k].words])
            if joined is None or not any(c[0] == "description" for c in joined) or \
                    not any(re.search(r"hsn|qty|quantity|rate|amount", w.text, re.I) for w in ln.words):
                continue
            cols = joined
        items: list[dict] = []
        end = max(span) + 1
        for j in range(max(span) + 1, len(lines)):
            row = lines[j]
            if END_OF_TABLE.search(row.text):
                end = j
                break
            cells = _assign(row.words, cols)
            no_qty = _num(cells.get("qty")) is None and _num(cells.get("rate")) is None
            if TOTALS_LABEL.search(row.text) and no_qty and (
                    not cells.get("description", "").strip() or
                    re.search(r"\b(c|s|i|ut)gst\b|round|^\s*total\b|less|cess", cells.get("description", ""), re.I)):
                end = j
                break
            end = j + 1
            numeric_keys = [k for k in ("qty", "rate", "taxable_value", "total") if _num(cells.get(k)) is not None]
            if not numeric_keys:
                desc = cells.get("description", "").strip()
                if items and desc and not re.fullmatch(r"\(?[₹I`]?\)?", desc):
                    items[-1]["description"] = ((items[-1].get("description") or "") + " " + desc).strip()
                continue
            desc = cells.get("description", "")
            if "sno" not in dict((c[0], 1) for c in cols):
                desc = re.sub(r"^\d+\s+", "", desc)  # serial number merged into description
            item = {
                "line_no": len(items) + 1,
                "description": desc.strip() or None,
                "hsn_sac": (re.search(r"\d{4,8}", cells.get("hsn_sac", "")) or [None])[0],
                "qty": _num(cells.get("qty"), "0.001"),
                "unit": (cells.get("unit") or None),
                "rate": _num(cells.get("rate"), "0.0001"),
                "discount": _num(cells.get("discount")),
                "taxable_value": _num(cells.get("taxable_value")),
                "gst_rate": _num(cells.get("gst_rate"), "0.001"),
                "cgst": _num(cells.get("cgst")),
                "sgst": _num(cells.get("sgst")),
                "igst": _num(cells.get("igst")),
                "tax_amount": _num(cells.get("tax_amount")),
                "total": _num(cells.get("total")),
                "_row": row.text,                     # used by _tidy_items as evidence, then dropped
            }
            if item["qty"] is not None and item["unit"] is None:
                m = re.search(r"[\d.]+\s*([A-Za-z]{2,5})$", cells.get("qty", ""))
                item["unit"] = m.group(1).upper() if m else None
            items.append(item)
        if items:
            out.items = items
            out.item_confidence = base
            return end
    return 0


# --------------------------------------------------------------------------- label anchors
INV_NO_LABEL = r"\b(invoice|inv|bill)\.?\s*(no|number|#)\.?"
# OCR misreads of the label: 'Imvoice No', 'Invaice No', 'lnvoice N0' ...
INV_NO_LABEL_OCR = (r"\b(invoice|[il1|][a-z]{1,2}[vwy][o0a][il1|!]?c[ec]|inv|bill|document|doc)\.?\s*"
                    r"(no|n0|na|number|#)\b\.?")
TALLY_REF_RE = re.compile(r"\b([A-Z0-9][A-Z0-9/\-_.]{1,30})\s+d[tlLiI1]\s*[.:,]?\s*(\d{1,2}[-./ ][A-Za-z]{3}[-./ ]\d{2,4}|"
                          r"\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", re.I)


def _has_fy_pair(val: str) -> bool:
    m = re.search(r"(?<!\d)(\d{2}|\d{4})-(\d{2})(?!\d)", val)
    return bool(m) and (int(m.group(1)) + 1) % 100 == int(m.group(2))


def _looks_like_invoice_no(val: str) -> bool:
    """An invoice number has a digit and is not an e-way bill number, an amount or a date."""
    if not re.search(r"\d", val) or re.search(r"way|^\d{12}$", val, re.I):
        return False
    if re.fullmatch(r"\d{1,3}(,\d{2,3})+(\.\d+)?|\d+\.\d{2}", val):
        return False
    return not DATE_RE.fullmatch(val)


def invoice_no_anchors(lines: list[Line]) -> list[tuple[int, float, float]]:
    """(page, x0, bottom) of every 'Invoice No.' label - where a zoomed re-read can look."""
    out = []
    lab = re.compile(INV_NO_LABEL_OCR, re.I)
    for seg in split_segments(lines):
        m = lab.search(seg.text)
        if m and not re.search(r"dispatch|despatch|delivery|order", seg.text, re.I):
            x0, _ = _label_span(seg, m)
            bottom = max(w.y1 for w in seg.words)
            out.append((seg.page, x0, bottom))
    return out


# --------------------------------------------------------------------------- arithmetic check
def _consistent(f: dict) -> bool:
    need = ("taxable_total", "invoice_total")
    if any(f.get(k) is None for k in need):
        return False
    tax = sum((f.get(k) or 0) for k in ("cgst", "sgst", "igst", "cess"))
    if not tax:
        return False
    extra = sum((f.get(k) or 0) for k in ("freight", "packing", "other_charges"))
    return abs(f["taxable_total"] + tax + extra - f["invoice_total"]) <= 1


def _amounts_in_words(lines: list[Line]) -> list[str]:
    """Amounts written in words, as plain numbers (also joined with the neighbouring line, because the
    words often wrap). Only used as candidates for the arithmetic check."""
    from ipt.core.numwords import words_to_amount
    out = []
    idx = [i for i, ln in enumerate(lines) if re.search(r"thousand|hundred|lakh|lac\b|crore", ln.text, re.I)]
    for i in idx:
        for a, b in ((i, i + 1), (i - 1, i + 1), (i, i + 2)):
            chunk = " ".join(ln.text for ln in lines[max(a, 0):b])
            chunk = re.sub(r".*?\(in\s+words\)\s*:?", "", chunk, flags=re.I)
            v = words_to_amount(chunk)
            if v is not None:
                out.append(f"{v:.2f}")
    return out


MAX_ROUND_OFF_OCR = Decimal("1.00")


def _rupee_misread(read: Decimal, checked: Decimal) -> bool:
    """'₹3,119' read as 23,119 or 73,119: the value read is the checked amount with one extra leading
    2 / 7 (the rupee sign)."""
    a, b = f"{read:.2f}", f"{checked:.2f}"
    return len(a) == len(b) + 1 and a[0] in "27" and a[1:] == b
# a 'tax amount' equal to a GST rate (2.50, 9.00 ...) is the rate column read as the amount
GST_RATE_VALUES = {Decimal(x).quantize(Decimal("0.01")) for x in
                   ("0.125", "0.25", "0.75", "1.5", "2.5", "3", "5", "6", "9", "12", "14", "18", "20", "28", "40")}


def _check_totals_by_arithmetic(lines: list[Line], out: ParsedInvoice, base: float,
                                company_gstin: str | None) -> None:
    """When the label rules did not give a consistent set of totals, pick the unique combination
    of printed numbers where taxable × GST rate = tax and taxable + tax ≈ total (see reconcile.py)."""
    from ipt.services.extraction.reconcile import solve
    if _consistent(out.fields):
        return
    sup = (out.fields.get("supplier_gstin") or "")[:2]
    own = (company_gstin or "")[:2]
    pos = out.fields.get("place_of_supply")
    intra = (sup == (pos or own)) if sup and (pos or own) else None
    heads_txt = "\n".join(ln.text for ln in lines)
    printed = {h for h in ("CGST", "SGST", "UTGST", "IGST") if re.search(rf"\b{h}\b", heads_txt, re.I)}
    if intra is False and printed & {"CGST", "SGST", "UTGST"} and "IGST" not in printed:
        intra = None          # GSTIN says inter-state but only CGST/SGST are printed: decide from the text
    if intra is None:
        heads = {h for h in ("CGST", "SGST", "UTGST", "IGST") if re.search(rf"\b{h}\b", text_all := "\n".join(
            ln.text for ln in lines), re.I)}
        if heads & {"CGST", "SGST", "UTGST"} and "IGST" not in heads:
            intra = True
        elif heads == {"IGST"}:
            intra = False
    words = _amounts_in_words(lines)
    texts = [ln.text for ln in lines] + words
    from ipt.services.extraction.reconcile import candidates as _cands
    words_amounts = _cands(words)          # 'Rupees ... Only' agreeing with the arithmetic outranks a misread
    sol = solve(texts, intra)
    split_conf = None
    if sol is None and intra:
        # CGST/SGST amounts unreadable but the total tax is: taxable + total tax ≈ total. The halves
        # are worked out (not read), so they are marked for checking.
        whole = solve(texts, False)
        if whole is not None and whole.igst:
            from decimal import ROUND_HALF_UP
            c = (whole.igst / 2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            from ipt.services.extraction.reconcile import Solution
            sol, split_conf = Solution(whole.taxable, c, whole.igst - c, None, whole.total), LOW
    if sol is None:
        ro = out.fields.get("round_off")
        if base < HIGH and ro is not None and abs(ro) > MAX_ROUND_OFF_OCR:
            out.confidence["round_off"] = min(out.confidence["round_off"], LOW)
        if base < HIGH:
            # scanned invoice whose amounts do not add up and no consistent set was found:
            # every amount read is suspect, so all of them are marked for checking
            for k in ("taxable_total", "cgst", "sgst", "igst", "cess", "invoice_total", "round_off"):
                if k in out.confidence:
                    out.confidence[k] = min(out.confidence[k], LOW)
        return
    conf = HIGH if base >= HIGH else 0.85     # three printed numbers agree with each other
    values = {"taxable_total": sol.taxable, "cgst": sol.cgst, "sgst": sol.sgst, "igst": sol.igst,
              "invoice_total": sol.total}
    ro = out.fields.get("round_off")
    if sol.round_off and (ro is None or abs(ro) > MAX_ROUND_OFF_OCR):
        out.fields.pop("round_off", None)          # a 'round off' above Rs 1 was misread (e.g. '₹0.07' -> 7)
        values["round_off"] = sol.round_off
    roles = {v for v in values.values() if v is not None} | {sum(t for t in (sol.cgst, sol.sgst, sol.igst) if t)}
    for k, v in values.items():
        if v is None:
            continue
        if split_conf is not None and k in ("cgst", "sgst") and k not in out.fields:
            out.fields[k], out.confidence[k] = v, split_conf
            continue
        is_rate = k in ("cgst", "sgst", "igst") and out.fields.get(k) in GST_RATE_VALUES and v > 100
        is_rupee = k in out.fields and _rupee_misread(out.fields[k], v)
        in_words = k == "invoice_total" and v in words_amounts and out.fields.get(k) not in words_amounts
        if k not in out.fields or is_rate or is_rupee or in_words or (out.fields[k] != v and out.fields[k] in roles):
            # missing, or the label rule picked a number that plays another role (e.g. the taxable
            # value or the tax total next to a 'Total' label)
            out.fields[k], out.confidence[k] = v, conf
        elif out.fields[k] != v:
            # a value read next to its label disagrees with the arithmetic: keep what was read
            # (never overwrite silently) but mark it for checking in the review screen
            out.confidence[k] = min(out.confidence.get(k, LOW), LOW)


# --------------------------------------------------------------------------- item checks
NOT_AN_ITEM = re.compile(r"\b(output|input)?\s*(c|s|i|ut)gst\b|round\s*off|\btotal\b|amount\s+chargeable|"
                         r"in\s+words|^\s*less\b|^\s*add\b|^\s*(output|input)\s*$", re.I)


def _one_char_apart(a: str, b: str) -> bool:
    """One character changed, added or dropped ('615' / '815', '15' / '815')."""
    if a == b:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long_ = sorted((a, b), key=len)
    return len(long_) - len(short) == 1 and any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


HEADER_JUNK = re.compile(r"^(?:s\.?\s*no\.?|sl\.?\s*no\.?|sr\.?\s*no\.?|no\.?|sl\.?|sr\.?|s\.?n\.?|#)$", re.I)


def _junk_name(desc: str) -> bool:
    d = (desc or "").strip()
    return not re.search(r"[A-Za-z]{3,}", d) or bool(HEADER_JUNK.match(d))


def _merge_split_rows(items: list[dict]) -> list[dict]:
    """A slightly tilted scan can split one item row over 2-3 lines: 'No.  6,280.00 MT  62,800.00' (the table
    heading's 'No.' + rate + amount), '25221000  10.000 MT' and '1 QUICK LIME LOOSE'. Join a row that has the
    amount but no real name with the neighbouring row(s) that have the name / HSN / quantity but no amount."""
    out, i = [], 0
    while i < len(items):
        it = items[i]
        has_amt = it.get("taxable_value") not in (None, 0)
        if has_amt and _junk_name(it.get("description")):
            # amount row first, the name below it (or above it, already in out)
            j, merged, names = i + 1, dict(it), []
            while j < len(items) and j <= i + 2 and items[j].get("taxable_value") in (None, 0):
                nxt = items[j]
                for k in ("hsn_sac", "qty", "unit", "rate", "gst_rate"):
                    if merged.get(k) in (None, "") and nxt.get(k) not in (None, ""):
                        merged[k] = nxt[k]
                d = (nxt.get("description") or "").strip()
                if not _junk_name(d):
                    names.append(d)
                merged["_row"] = f"{merged.get('_row') or ''} {nxt.get('_row') or ''}"
                j += 1
            if not names and out and out[-1].get("taxable_value") in (None, 0) and not _junk_name(
                    out[-1].get("description")):
                prev = out.pop()                       # the name came first
                names.append(prev["description"])
                for k in ("hsn_sac", "qty", "unit", "rate", "gst_rate"):
                    if merged.get(k) in (None, "") and prev.get(k) not in (None, ""):
                        merged[k] = prev[k]
                merged["_row"] = f"{prev.get('_row') or ''} {merged.get('_row') or ''}"
            if names:
                merged["description"] = " ".join(names)
                out.append(merged)
                i = j
                continue
        out.append(it)
        i += 1
    for n, it in enumerate(out, 1):                    # '1 QUICK LIME LOOSE' / '1Quick Lime': drop the serial no.
        d = (it.get("description") or "").strip()
        m = re.match(r"^(\d{1,3})\s*[.)-]?\s*(?=[A-Za-z]{3})", d)
        if m and int(m.group(1)) == n:
            it["description"] = d[m.end():].strip()
    return out


def _tidy_items(out: ParsedInvoice, base: float, texts: list[str] | None = None) -> None:
    """Drop tax / round-off / batch rows that OCR placed inside the item table and flag items whose
    quantity x rate does not give the amount. Values are never changed except one case: a single
    item whose qty x rate equals the (arithmetic-checked) taxable value gets that value as amount."""
    if not out.items:
        return
    out.items = _merge_split_rows(out.items)
    kept = []
    for it in out.items:
        desc = (it.get("description") or "").strip()
        if desc and NOT_AN_ITEM.search(desc):
            continue
        if re.match(r"^batch\b", desc, re.I):
            continue
        if not re.search(r"[A-Za-z]{3,}", desc) and kept:
            continue          # stray numbers below a real item (rates of tax rows, totals)
        kept.append(it)
    for n, it in enumerate(kept, 1):
        it["line_no"] = n
        if it.get("unit"):
            it["unit"] = re.sub(r"[^A-Za-z]", "", it["unit"]).upper() or None
    out.items = kept
    if not kept:
        out.item_confidence = 0.0
        return
    ok = True
    repaired = False
    taxable = out.fields.get("taxable_total")
    for it in kept:
        q, r, a = it.get("qty"), it.get("rate"), it.get("taxable_value")
        if len(kept) == 1 and taxable is not None and q and r and abs(q * r - taxable) <= 1 and a != taxable:
            it["taxable_value"] = a = taxable          # amount misread / missing; qty x rate confirms it
        if len(kept) == 1 and a is None and taxable is not None:
            it["taxable_value"] = a = taxable          # the only item carries the whole (checked) taxable value
        if q and a and (r is None or abs(q * r - a) > 1):
            # rate not read, or misread ('815' as '615' / '15'): amount / quantity - accepted only if that rate
            # is printed on the page, or differs from the rate read by one character
            r2 = (Decimal(str(a)) / Decimal(str(q))).quantize(Decimal("0.01"))
            if r2 > 0 and abs(r2 * Decimal(str(q)) - Decimal(str(a))) <= Decimal("0.05"):
                shown = {f"{r2:.2f}", f"{r2:,.2f}", f"{r2.normalize():f}"}
                row = it.get("_row") or ""            # only the item's own line counts as evidence
                printed = any(re.search(r"(?<![\d.,])" + re.escape(v) + r"(?![\d])", row) for v in shown)
                if printed or (r is not None and _one_char_apart(f"{r.normalize():f}", f"{r2.normalize():f}")):
                    it["rate"] = r = r2
                    repaired = True
        if q is None and r and a:
            # quantity not read: amount / rate, accepted only if it divides to at most 3 decimals AND that
            # quantity is printed somewhere on the page ('29.330 MT')
            qd = (Decimal(str(a)) / Decimal(str(r)))
            if qd == qd.quantize(Decimal("0.001")) and qd > 0:
                shown = {f"{qd:.3f}", f"{qd:.2f}", f"{qd.normalize():f}"}
                if any(re.search(r"(?<![\d.])" + re.escape(v) + r"(?![\d])", t) for t in texts or [] for v in shown):
                    it["qty"] = q = qd
        if q is None or r is None or a is None or abs(q * r - a) > 1:
            ok = False
    if taxable is not None and sum((it.get("taxable_value") or 0) for it in kept) != taxable:
        ok = False
    for it in kept:
        it.pop("_row", None)
    out.item_confidence = (min(base, GUESS) if repaired else base) if ok else min(out.item_confidence or LOW, LOW)


# --------------------------------------------------------------------------- entry
def parse(lines: list[Line], from_ocr: bool, company_gstin: str | None = None) -> ParsedInvoice:
    base = MEDIUM if from_ocr else HIGH
    out = ParsedInvoice()
    segments = split_segments(lines)
    parse_header(segments, out, base, company_gstin)
    table_end = parse_items(lines, out, base)
    end_y = lines[table_end - 1].y if table_end else None
    tail = [sg for sg in segments if end_y is None or sg.y > end_y + 0.5 or sg.page > lines[table_end - 1].page]
    parse_totals(tail, out, base, 0)
    _check_totals_by_arithmetic(lines, out, base, company_gstin)
    name = out.fields.get("supplier_name") or ""
    if base < HIGH and name and not re.search(r"[A-Za-z]{4,}", name):
        out.confidence["supplier_name"] = LOW      # OCR noise, not a name: user must type it
    _tidy_items(out, base, [ln.text for ln in lines])
    if "supplier_gstin" in out.fields and not validate_gstin(out.fields["supplier_gstin"]).valid:
        out.confidence["supplier_gstin"] = min(out.confidence["supplier_gstin"], LOW)
    return out


# --------------------------------------------------------------------------- known suppliers
def fill_known_gstin(text: str, out: ParsedInvoice, known: dict[str, str], company_gstin: str | None) -> None:
    """When OCR could not read the supplier GSTIN, take it from a GSTIN already known for this company (Tally
    ledgers, the supplier master, or other bills in the same file) - but only with evidence printed on this
    page: the supplier's PAN read exactly, or a damaged copy of the GSTIN that is clearly closest to one known
    GSTIN. A matching supplier name raises confidence. Never chosen when two known GSTINs fit."""
    from difflib import SequenceMatcher

    if "supplier_gstin" in out.fields or not known:
        return
    own = normalize(company_gstin) if company_gstin else None
    cands = {g: ([n] if isinstance(n, str) else list(n)) for g, n in known.items()
             if g != own and validate_gstin(g).valid}
    if not cands:
        return
    up = text.upper()
    pans = set(PAN_RE.findall(up)) | set(PAN_RE.findall(up.replace(" ", "")))
    tokens = [t for t in re.findall(r"[A-Z0-9@!|]{12,17}", up.replace(" ", "")) if sum(c.isdigit() for c in t) >= 2]
    name = (out.fields.get("supplier_name") or "").upper()

    def _core(t: str) -> str:
        t = re.sub(r"\b(M/?S|PRIVATE|PVT|LIMITED|LTD|LLP|CO|COMPANY|THE)\b\.?", " ", t.upper())
        return re.sub(r"[^A-Z0-9]+", " ", t).strip()

    def name_ok(names) -> bool:
        # 'AGLOW CHEMICALS PRIVATE LIMITED' on the bill = 'Aglow Chemicals' in Tally
        return bool(_core(name)) and any(n and SequenceMatcher(None, _core(name), _core(n)).ratio() >= 0.85
                                         for n in names)

    by_pan = [g for g in cands if g[2:12] in pans]
    if len(by_pan) == 1:
        g = by_pan[0]
        out.put("supplier_gstin", g, MEDIUM if name_ok(cands[g]) else GUESS)
        out.confidence["supplier_gstin_source"] = "PAN on the bill matches a known supplier"
        return
    if by_pan:
        return                                   # two known GSTINs share that PAN (two states): user decides
    scores = sorted(((max((SequenceMatcher(None, t, g).ratio() for t in tokens), default=0), g) for g in cands),
                    reverse=True)
    if scores and scores[0][0] >= 0.7 and (len(scores) == 1 or scores[0][0] - scores[1][0] >= 0.15):
        g = scores[0][1]
        out.put("supplier_gstin", g, GUESS if name_ok(cands[g]) else LOW)
        out.confidence["supplier_gstin_source"] = "damaged GSTIN on the bill is closest to a known supplier"
        return
    by_name = [g for g, n in cands.items() if name_ok(n)]
    if len(by_name) == 1 and not by_pan:
        # only the supplier name matches: the GSTIN is suggested but must be checked against the bill
        out.put("supplier_gstin", by_name[0], LOW)
        out.confidence["supplier_gstin_source"] = "supplier name matches a known supplier (GSTIN not readable)"
