"""Module A - statutory audit FS pack. Each rule returns a list of Finding; the runner turns that into PASS/EXC."""
from __future__ import annotations
import difflib
import re
from collections import Counter, defaultdict
from datetime import date

from .loaders import find_row, table_has, load_tb
from .models import Finding, Result

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
DATE_RE = re.compile(r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b", re.I)


class NotRun(Exception):
    """Raised by a rule that cannot run because its input is missing."""


class Ctx:
    def __init__(self, eng, doc, params, tb_path=None):
        self.eng, self.doc, self.p, self.tb_path = eng, doc, params, tb_path
        self.cy, self.py = int(eng["fy"]), int(eng.get("py", int(eng["fy"]) - 1))
        self.client = eng["client"]

    # --- helpers
    def paragraphs(self, where=("body",)):
        return [p for p in self.doc.paragraphs if p.where in where]

    def audit_region(self):
        """Text of the independent auditor's report: from the LAST heading-like 'Independent auditor...' line
        (the first ones are usually index entries) to the next statement heading, max 9000 characters."""
        t = self.doc.text
        ms = list(re.finditer(r"^\s*independent auditor[^\n]{0,60}$", t, re.I | re.M))
        if not ms:
            return ""
        start = ms[-1].start()
        reg = t[start: start + 9000]
        end = re.search(r"^\s*statement of financial position\s*$", reg[10:], re.I | re.M)
        return reg[: end.start() + 10] if end else reg

    def notes_text(self):
        """Text from the last 'Notes to the financial statements' heading; falls back to the whole body text."""
        t = self.doc.text
        ms = list(re.finditer(r"^\s*notes to the (financial statements|accounts)[^\n]{0,30}$", t, re.I | re.M))
        t = t[ms[-1].start():] if ms else t
        return re.sub(r"\s+", " ", t)      # PDF line-wraps must not break phrase matching

    def year_end(self):
        d, m = self.eng["client"].get("year_end", "31 December").split()
        return date(self.cy, MONTHS[m.lower()], int(d))


def _ymd(m):
    return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))


_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uFE58\uFE63\uFF0D"), "-")
_QUOTES = dict.fromkeys(map(ord, "\u2018\u2019\u201B\u2032"), "'")


def canon(s):
    """Canonical form for NAME comparison: unicode dashes -> '-', spacing around dashes/ampersands normalised, NBSP, curly quotes. Case is NOT changed here."""
    s = str(s).replace("\u00a0", " ").translate(_DASHES).translate(_QUOTES)
    s = re.sub(r"\s*-\s*", " - ", s)
    s = re.sub(r"\s*&\s*", " & ", s)
    return re.sub(r"\s+", " ", s).strip()


def same_name(a, b):
    """True when two names differ only by case, dash type, spacing or trailing punctuation (not a spelling error)."""
    f = lambda x: re.sub(r"[\W_]+", " ", canon(x).lower()).strip()      # ignore all punctuation, dash type, spacing and case
    return f(a) == f(b)


def fuzzy_hits(text, target, thr=0.84):
    """Greedy non-overlapping fuzzy matches of `target` inside `text` -> [(cand, ratio)].
    Differences of case, dash type (- / en dash / em dash), spacing or surrounding punctuation are NOT errors: such a match is returned as the exact target."""
    text, tgt = canon(text), canon(target)
    toks = text.split()
    n = len(tgt.split())
    cands = []
    for w in {max(1, n - 1), n, n + 1}:
        for i in range(0, len(toks) - w + 1):
            cand = " ".join(toks[i:i + w]).strip(".,;:()'\"")
            r = difflib.SequenceMatcher(None, cand.lower(), tgt.lower()).ratio()
            if r >= thr:
                cands.append((r, -w, i, w, cand))
    cands.sort(reverse=True)
    used, hits = set(), []
    for r, _, i, w, cand in cands:
        span = set(range(i, i + w))
        if span & used:
            continue
        used |= span
        hits.append((target if same_name(cand, tgt) else cand, 1.0 if same_name(cand, tgt) else r, i))
    return sorted(hits, key=lambda h: h[2])


# ------------------------------------------------------------------ SA-01
def sa01_names(c: Ctx):
    target = c.client["name"]
    out = []
    scan = [(p.loc, p.text) for p in c.doc.paragraphs if p.where in ("body", "header", "footer")]
    scan += [(t.loc, " ".join(" ".join(r) for r in t.rows)) for t in c.doc.tables]
    scan += [(f"Page {i + 1}", pg) for i, pg in enumerate(c.doc.pages)]
    found_any = False
    for loc, text in scan:
        for cand, r, _ in fuzzy_hits(text, target):
            found_any = True
            if cand == target:
                continue
            if cand.lower() == target.lower():
                out.append(Finding("SA-01", "Company name stylised differently from trade licence", "Low",
                                   f"'{cand}' vs trade licence '{target}'", loc, target, cand))
            else:
                out.append(Finding("SA-01", "Company name spelling differs from trade licence", "High",
                                   f"'{cand}' vs trade licence '{target}'", loc, target, cand))
    if not found_any:
        out.append(Finding("SA-01", "Company name from trade licence not found in the pack", "High",
                           f"'{target}' not located anywhere in the document", "Whole pack", target, "-"))
    return out


# ------------------------------------------------------------------ SA-02
def sa02_legal_status(c: Ctx):
    status = c.client.get("legal_status", "OTHER").upper()
    terms = c.p["legal_status_terms"]
    expected = terms.get(status)
    if not expected:
        raise NotRun(f"Legal status '{status}' not in Annexure II map")
    wrong = [t for t in set(terms.values()) if t != expected]
    out, counts, first = Counter(), Counter(), {}
    for p in c.doc.paragraphs:
        if p.where != "body":
            continue
        for w in wrong:
            for m in re.finditer(rf"\bthe {w}\b", p.text, re.I):
                counts[w] += 1
                first.setdefault(w, p.loc)
    res = []
    for w, n in counts.items():
        res.append(Finding("SA-02", f"Legal-status wording: '{w}' used where '{expected}' is expected", "Medium",
                           f"{n} occurrence(s) of 'the {w.lower()}'. Legal status {status} should read '{expected}' (Annexure II). "
                           f"IFRS boilerplate may legitimately use 'entity' - confirm.", first[w], expected, w))
    return res


# ------------------------------------------------------------------ SA-04
def sa04_signatory_spelling(c: Ctx):
    legal = c.client.get("signatories_legal") or []
    if not legal:
        raise NotRun("signatories_legal not provided in engagement file")
    out = []
    text_units = [(p.loc, p.text) for p in c.doc.paragraphs] + [(f"Page {i + 1}", t) for i, t in enumerate(c.doc.pages)]
    for name in legal:
        exact, variants = 0, []
        for loc, t in text_units:
            for cand, r, _ in fuzzy_hits(t, name, 0.82):
                if cand.lower() == name.lower():
                    exact += 1
                else:
                    variants.append((cand, loc))
        if variants:
            for cand, loc in variants[:3]:
                out.append(Finding("SA-04", "Signatory name spelling differs from legal documents", "High",
                                   f"'{cand}' vs legal name '{name}'", loc, name, cand))
        elif exact == 0:
            out.append(Finding("SA-04", "Signatory from legal documents not found in the pack", "Medium",
                               f"'{name}' not located", "Whole pack", name, "-"))
    return out


# ------------------------------------------------------------------ SA-05
def sa05_signatory_sufficiency(c: Ctx):
    sh = c.client.get("shareholders") or []
    signed = c.eng.get("fs_signatories")
    if not sh or signed is None:
        raise NotRun("shareholders / fs_signatories not provided")
    def is_sh(n):
        return any(difflib.SequenceMatcher(None, n.lower(), s.lower()).ratio() >= 0.9 for s in sh)
    all_sh_signed = all(any(difflib.SequenceMatcher(None, s.lower(), n.lower()).ratio() >= 0.9 for n in signed) for s in sh)
    non_sh = [n for n in signed if not is_sh(n)]
    need_br = (not all_sh_signed) or bool(non_sh)
    if need_br and not c.eng.get("br_on_file", False):
        return [Finding("SA-05", "Signatories do not cover all shareholders and no Board Resolution is on file", "High",
                        f"{len(sh)} shareholder(s), {len(signed)} signatory(ies)"
                        + (f"; non-shareholder signatory: {', '.join(non_sh)}" if non_sh else ""),
                        "FS signature page", "All shareholders sign, or BR authorising signatory", f"{len(signed)} of {len(sh)} signed")]
    return []


# ------------------------------------------------------------------ SA-06
def sa06_years(c: Ctx):
    allowed = {c.cy, c.py} | set(int(y) for y in c.eng.get("allowed_years", []))
    out = []
    # 1) statement column headers
    for t in c.doc.tables:
        head = [yr for r in t.rows[:2] for cell in r for yr in re.findall(r"\b(20\d{2})\b", cell)]
        if len(head) >= 2:
            ys = [int(y) for y in head[:2]]
            if ys != [c.cy, c.py] and set(ys) <= {c.cy, c.py, c.cy + 1, c.py - 1}:
                out.append(Finding("SA-06", "Comparative column headers not in CY, PY order for the reporting year", "High",
                                   f"Header shows {ys[0]} | {ys[1]}; expected {c.cy} | {c.py}", t.loc, f"{c.cy} | {c.py}", f"{ys[0]} | {ys[1]}"))
    # 2) period-end phrases
    ye = c.year_end()
    rx = re.compile(r"(?:year ended|period ended|as at|as of)\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})", re.I)
    units = [(p.loc, p.text) for p in c.doc.paragraphs] + [(f"Page {i + 1}", t) for i, t in enumerate(c.doc.pages)]
    for loc, t in units:
        for m in rx.finditer(t):
            dm = DATE_RE.search(m.group(1))
            if not dm:
                continue
            d = _ymd(dm)
            if d.year in (c.cy, c.py) and (d.month, d.day) != (ye.month, ye.day):
                out.append(Finding("SA-06", "Period-end date differs from the entity's year-end", "Medium",
                                   f"'{m.group(0)}' - year-end is {ye.day} {ye.strftime('%B')}", loc, f"{ye.day} {ye.strftime('%B')}", m.group(1)))
    # 3) stray years
    stray = defaultdict(list)
    for loc, t in units:
        for y in re.findall(r"\b(20\d{2})\b", t):
            if int(y) not in allowed and c.py - 3 <= int(y) < c.py:   # older than the comparative year; cy+1 is the report-date year
                stray[int(y)].append(loc)
    for y, locs in stray.items():
        out.append(Finding("SA-06", f"Year {y} appears but is neither current nor previous year", "Medium",
                           f"{len(locs)} occurrence(s); expected only {c.cy} and {c.py}", locs[0], f"{c.cy}/{c.py}", str(y)))
    return out


# ------------------------------------------------------------------ SA-07/08/09/10 auditor's report
def sa07_report_date(c: Ctx):
    reg = c.audit_region()
    if not reg:
        raise NotRun("Independent auditor's report section not found")
    ye = c.year_end()
    dates = [_ymd(m) for m in DATE_RE.finditer(reg)]
    if not any(d > ye for d in dates):
        return [Finding("SA-07", "Audit report date missing (no date after year-end in the report)", "High",
                        f"Year-end {ye.isoformat()}; no later date located in the auditor's report", "Auditor's report", "Dated report", "None")]
    return []


def sa08_licence_ref(c: Ctx):
    reg = c.audit_region()
    if not reg:
        raise NotRun("Independent auditor's report section not found")
    out = []
    if not re.search(r"(registration|licen[cs]e)\s*(no\.?|number)?\s*[:\-#]?\s*\d{2,}", reg, re.I):
        out.append(Finding("SA-08", "Partner audit licence / registration number missing", "High",
                           "No 'Registration No.: <digits>' pattern in the auditor's report", "Auditor's report", "Registration number", "None"))
    if not re.search(r"\bref(erence)?\.?\s*(no\.?|number)?\s*[:\-#]\s*[A-Za-z0-9/\-]{3,}", reg, re.I):
        out.append(Finding("SA-08", "Audit report reference number missing", "High",
                           "No 'Ref: <number>' pattern in the auditor's report", "Auditor's report", "Report reference", "None"))
    return out


def sa09_authority(c: Ctx):
    reg = c.audit_region()
    if not reg:
        raise NotRun("Independent auditor's report section not found")
    expected = c.client["authority"].upper()
    m = re.search(r"legal and regulatory requirements", reg, re.I)
    seg = reg[m.start(): m.start() + 2500] if m else reg
    present = {t for t in c.p["authority_tokens"] if re.search(rf"\b{t}\b", seg)}
    out = []
    if expected not in present:
        out.append(Finding("SA-09", "Licensing authority not named in 'other legal and regulatory requirements'", "High",
                           f"Expected {expected}; found {sorted(present) or 'none'}", "Auditor's report", expected, ", ".join(sorted(present)) or "none"))
    for t in sorted(present - {expected}):
        out.append(Finding("SA-09", "Wrong licensing authority named in auditor's report", "High",
                           f"'{t}' appears; client is licensed by {expected}", "Auditor's report", expected, t))
    return out


def sa10_addressee(c: Ctx):
    sh = c.client.get("shareholders") or []
    if not sh:
        raise NotRun("shareholders not provided")
    reg = c.audit_region()
    m = re.search(r"to the (share\s?holders?)\b", reg, re.I) or re.search(r"to the (share\s?holders?)\b", c.doc.all_text, re.I)
    if not m:
        return [Finding("SA-10", "Auditor's report addressee not found", "Low", "No 'To the Shareholder(s)' line", "Auditor's report", "", "")]
    plural = m.group(1).lower().endswith("s")
    if plural != (len(sh) > 1):
        return [Finding("SA-10", "Addressee singular/plural does not match number of shareholders", "Low",
                        f"{len(sh)} shareholder(s) but report reads '{m.group(0)}'", "Auditor's report",
                        "Shareholders" if len(sh) > 1 else "Shareholder", m.group(1))]
    return []


# ------------------------------------------------------------------ SA-13/14/15/16 formatting
def _is_tnr(name):
    n = (name or "").lower().replace(" ", "").replace("-", "")
    return "timesnewroman" in n or n.endswith("timesroman") or "timesnewromanps" in n or "times" in n.split("+")[-1]


def sa13_font(c: Ctx):
    want = c.p["typography"]["font"]
    out = []
    if c.doc.kind == "docx":
        bad = Counter()
        loc = {}
        total = 0
        for p in c.doc.paragraphs:
            for r in p.runs:
                if r.font is None:
                    continue
                total += len(r.text)
                if not _is_tnr(r.font):
                    bad[r.font] += len(r.text)
                    loc.setdefault(r.font, p.loc)
        for f, n in bad.most_common(5):
            out.append(Finding("SA-13", f"Font '{f}' used instead of {want}", "Low" if n / max(total, 1) < 0.1 else "Medium",
                               f"{n} characters ({n / max(total, 1):.1%} of text)", loc[f], want, f))
    else:
        if c.doc.kind != "pdf":
            raise NotRun("Font is not measurable from an Excel/scanned/image input")
        total = sum(c.doc.pdf_fonts.values())
        for f, n in c.doc.pdf_fonts.items():
            if not _is_tnr(f):
                out.append(Finding("SA-13", f"Font '{f}' used instead of {want}", "Low" if n / max(total, 1) < 0.1 else "Medium",
                                   f"{n} characters ({n / max(total, 1):.1%} of text) - measured from PDF", "PDF", want, f))
    return out


def sa14_sizes(c: Ctx):
    ty = c.p["typography"]
    allowed, tol = ty["allowed_sizes"], ty["size_tolerance"]
    ok = lambda s: any(abs(s - a) <= tol for a in allowed)
    out = []
    if c.doc.kind == "docx":
        bad, loc = Counter(), {}
        for p in c.doc.paragraphs:
            for r in p.runs:
                if r.size is not None and not ok(r.size):
                    bad[r.size] += len(r.text)
                    loc.setdefault(r.size, p.loc)
        for s, n in bad.most_common(5):
            out.append(Finding("SA-14", f"Font size {s:g} pt is outside firm standard {allowed}", "Low",
                               f"{n} characters", loc[s], str(allowed), f"{s:g}"))
    else:
        if c.doc.kind != "pdf":
            raise NotRun("Font size is not measurable from an Excel/scanned/image input")
        for s, n in c.doc.pdf_sizes.items():
            if not ok(s) and n > 20:
                out.append(Finding("SA-14", f"Font size {s:g} pt is outside firm standard {allowed}", "Low",
                                   f"{n} characters - measured from PDF", "PDF", str(allowed), f"{s:g}"))
    return out


def sa15_margins(c: Ctx):
    m = c.p["margins_in"]
    out = []
    if c.doc.kind == "docx":
        tol = m["tolerance"]
        for s in c.doc.sections:
            probs = []
            if abs(s.left - m["left"]) > tol:
                probs.append(f"left {s.left:.2f} in (std {m['left']})")
            if abs(s.top - m["top"]) > tol:
                probs.append(f"top {s.top:.2f} in (std {m['top']})")
            for nm, v in (("right", s.right), ("bottom", s.bottom)):
                if not any(abs(v - a) <= tol for a in m["right_bottom_allowed"]):
                    probs.append(f"{nm} {v:.2f} in (std {m['right_bottom_allowed']})")
            if probs:
                out.append(Finding("SA-15", "Page margins differ from firm standard", "Low", "; ".join(probs),
                                   f"Section {s.idx}", "L1.3 T1.5 R/B 1|0.75|0.5", "; ".join(probs)))
    else:
        if c.doc.kind != "pdf":
            raise NotRun("Margins is not measurable from an Excel/scanned/image input")
        if not c.doc.pdf_margins:
            raise NotRun("No text found in PDF")
        import statistics
        tol = m["pdf_tolerance"]
        left = statistics.median(x[0] for x in c.doc.pdf_margins)
        if abs(left - m["left"]) > tol:      # top is not tested on PDF: running headers sit inside the top margin
            out.append(Finding("SA-15", "Left margin differs from firm standard (PDF text extent, approximate)", "Low",
                               f"left ~{left:.2f} in (std {m['left']})", "PDF median of pages", str(m["left"]), f"{left:.2f}"))
    return out


def sa16_justified(c: Ctx):
    if c.doc.kind != "docx":
        raise NotRun("Paragraph alignment is not measurable from a PDF")
    mn = c.p["narrative_min_words"]
    bad = [p for p in c.doc.paragraphs if p.where == "body" and len(p.text.split()) >= mn and not p.justified]
    if bad:
        return [Finding("SA-16", "Narrative paragraphs are not justified", "Low",
                        f"{len(bad)} paragraph(s) of {mn}+ words are not justified; first: {bad[0].loc}", bad[0].loc, "Justified", "Left/other")]
    return []


# ------------------------------------------------------------------ statement parsing
def _sofp_table(t):
    return table_has(t, r"^total assets") 


def _cf_table(t):
    return table_has(t, r"operating activities")


def _soce_table(t):
    return table_has(t, r"share capital") and table_has(t, r"^balance")


def _pair(row):
    label, nums, loc = row
    if len(nums) >= 2:
        return nums[-2], nums[-1], loc
    return nums[-1], None, loc


def _cmp(findings, cid, title, a, b, what_a, what_b, loc, tol=1.0, label=""):
    if a is None or b is None:
        return
    if abs(a - b) > tol:
        findings.append(Finding(cid, title, "High",
                                f"{label}{what_a} {a:,.0f} vs {what_b} {b:,.0f}; difference {a - b:,.0f}", loc, f"{b:,.0f}", f"{a:,.0f}"))


def sa20_balance(c: Ctx):
    ta = find_row(c.doc.tables, r"^total assets", None)
    tel = find_row(c.doc.tables, r"^total (equity and liabilities|liabilities and (share|equity))", None)
    if not ta or not tel:
        raise NotRun("Total assets / total equity and liabilities rows not found in a statement table")
    out = []
    a_cy, a_py, loc = _pair(ta)
    l_cy, l_py, loc2 = _pair(tel)
    # tables list columns as PY, CY or CY, PY: header decides; we assume CY first when header says so.
    cy_first = _cy_first(c, ta)
    if not cy_first:
        a_cy, a_py = a_py, a_cy
        l_cy, l_py = l_py, l_cy
    _cmp(out, "SA-20", "Statement of financial position does not balance (current year)", a_cy, l_cy, "Total assets", "total equity and liabilities", loc)
    _cmp(out, "SA-20", "Statement of financial position does not balance (previous year)", a_py, l_py, "Total assets", "total equity and liabilities", loc)
    return out


def _cy_first(c: Ctx, row):
    """Decide whether the statement lists CY before PY using the header of the table that holds the row."""
    for t in c.doc.tables:
        if any(r and r is not None and row[0] in r for r in t.rows):
            for r in t.rows[:3]:
                ys = [int(y) for cell in r for y in re.findall(r"\b(20\d{2})\b", cell)]
                if len(ys) >= 2:
                    return ys[0] >= ys[1]
    return True


def sa21_cash(c: Ctx):
    sofp_cash = find_row(c.doc.tables, r"^cash and (bank|cash equivalents)", _sofp_like(c))
    cf_close = find_row(c.doc.tables, r"cash and cash equivalents at (the )?end|closing (balance of )?cash", _cf_table)
    if not sofp_cash or not cf_close:
        raise NotRun("Cash and bank (SOFP) or closing cash (cash flow) row not found")
    s_cy, s_py, loc = _pair(sofp_cash)
    f_cy, f_py, loc2 = _pair(cf_close)
    if not _cy_first(c, sofp_cash):
        s_cy, s_py = s_py, s_cy
    if not _cy_first(c, cf_close):
        f_cy, f_py = f_py, f_cy
    out = []
    _cmp(out, "SA-21", "Cash flow closing cash does not agree to SOFP cash and bank (current year)", f_cy, s_cy,
         "Cash flow closing cash", "SOFP cash and bank", f"{loc2} vs {loc}")
    _cmp(out, "SA-21", "Cash flow closing cash does not agree to SOFP cash and bank (previous year)", f_py, s_py,
         "Cash flow closing cash", "SOFP cash and bank", f"{loc2} vs {loc}")
    return out


def _sofp_like(c):
    return lambda t: _sofp_table(t)


def sa22_equity(c: Ctx):
    te = find_row(c.doc.tables, r"^total (share\s?holders?[’']?s?[’']? )?equity(?! and)", _sofp_like(c))
    soce = None
    for t in c.doc.tables:
        if _soce_table(t):
            for ri in range(len(t.rows) - 1, -1, -1):
                from .loaders import row_label_and_numbers
                lab, nums = row_label_and_numbers(t.rows[ri])
                if lab.lower().startswith("balance") and nums:
                    soce = (lab, nums, f"{t.loc}, row {ri + 1}")
                    break
        if soce:
            break
    if not te or not soce:
        raise NotRun("Total equity (SOFP) or closing balance (SOCE) not found")
    pr = _pair(te)
    sofp_cy = pr[0] if _cy_first(c, te) else pr[1]
    out = []
    _cmp(out, "SA-22", "SOCE closing equity does not agree to SOFP total equity", soce[1][-1], sofp_cy,
         "SOCE closing total", "SOFP total equity", f"{soce[2]} vs {te[2]}")
    return out


# ------------------------------------------------------------------ SA-24 TB vs FS
def sa24_tb(c: Ctx):
    if not c.tb_path:
        raise NotRun("Trial balance (XLSX/CSV) not supplied")
    tb = load_tb(c.tb_path)
    out = []
    dr, cr = sum(r["debit"] for r in tb), sum(r["credit"] for r in tb)
    if abs(dr - cr) > 1:
        out.append(Finding("SA-24", "Client trial balance does not balance", "High", f"Debits {dr:,.0f} vs credits {cr:,.0f}", "TB", "Dr = Cr", f"{dr - cr:,.0f}"))
    net = lambda cls: sum(r["debit"] - r["credit"] for r in tb if r["class"].startswith(cls))
    assets = net("asset")
    income = -net("income")
    expense = net("expense")
    profit = income - expense
    equity = -net("equity") + profit
    fs_ta = find_row(c.doc.tables, r"^total assets")
    if fs_ta:
        v = _pair(fs_ta)
        v_cy = v[0] if _cy_first(c, fs_ta) else v[1]
        _cmp(out, "SA-24", "Total assets per FS differ from client TB", v_cy, assets, "FS total assets", "TB assets", f"{fs_ta[2]} vs TB")
    fs_pl = find_row(c.doc.tables, r"(profit|loss).*(for the (year|period))|net (profit|loss)")
    if fs_pl:
        v = _pair(fs_pl)
        v_cy = v[0] if _cy_first(c, fs_pl) else v[1]
        _cmp(out, "SA-24", "Profit/(loss) per FS differs from client TB", v_cy, profit, "FS profit", "TB profit", f"{fs_pl[2]} vs TB")
    fs_te = find_row(c.doc.tables, r"^total (share\s?holders?[’']?s?[’']? )?equity(?! and)", _sofp_like(c))
    if fs_te:
        v = _pair(fs_te)
        v_cy = v[0] if _cy_first(c, fs_te) else v[1]
        _cmp(out, "SA-24", "Total equity per FS differs from client TB (equity + current-year profit)", v_cy, equity, "FS equity", "TB equity", f"{fs_te[2]} vs TB")
    if not (fs_ta or fs_pl or fs_te):
        raise NotRun("No statement rows found to compare with the TB")
    return out


# ------------------------------------------------------------------ SA-29/30 disclosures
def sa29_notes(c: Ctx):
    t = c.notes_text()
    out = []
    for name, rx in c.p["mandatory_notes"].items():
        if not re.search(rx, t, re.I):
            out.append(Finding("SA-29", f"Mandatory note missing: {name}", "Medium",
                               f"No text matching /{rx}/ in the pack", "Notes", name, "absent"))
    return out


def sa30_standards(c: Ctx):
    req = c.p["standards_not_yet_effective_mentions"].get(c.cy)
    if not req:
        raise NotRun(f"No standards list configured for FY{c.cy} - technical partner to add")
    t = c.notes_text()
    return [Finding("SA-30", f"Standards disclosure incomplete for FY{c.cy}: '{r}' not mentioned", "Medium",
                    "Annexure I of the review workbook is year-specific and must be refreshed each year-end", "Notes - standards issued not yet effective", r, "absent")
            for r in req if r.lower() not in t.lower()]


# ------------------------------------------------------------------ SA-46/47 gates, SA-49 going concern
def sa46_levels(c: Ctx):
    log = c.eng.get("review_log")
    if log is None:
        raise NotRun("review_log not provided")
    out = []
    for lvl in c.p["review_levels"]:
        e = log.get(lvl) or {}
        if not e.get("done"):
            out.append(Finding("SA-46", f"Review level not completed before Partner stage: {lvl}", "High",
                               "Partner review should be locked until all lower levels are cleared", "Review log", "done", "pending"))
    return out


def sa47_ready_before_print(c: Ctx):
    log = c.eng.get("review_log")
    if log is None:
        raise NotRun("review_log not provided")
    rb = log.get("ready_before_print") or {}
    if not rb.get("done"):
        return [Finding("SA-47", "'FS ready before print' checklist not completed", "Medium", "Must follow completion of all review levels", "Review log", "done", "pending")]
    dates = [str(log[l].get("date")) for l in c.p["review_levels"] if (log.get(l) or {}).get("date")]
    if dates and rb.get("date") and str(rb["date"]) < max(dates):
        return [Finding("SA-47", "'FS ready before print' was completed before the last review level", "Medium",
                        f"Print check {rb['date']} precedes last review {max(dates)}", "Review log", "after all reviews", str(rb["date"]))]
    return []


def sa49_going_concern(c: Ctx):
    te = find_row(c.doc.tables, r"^total (share\s?holders?[’']?s?[’']? )?equity(?! and)", _sofp_like(c))
    if not te:
        raise NotRun("Total equity row not found")
    pr = _pair(te)
    eq = pr[0] if _cy_first(c, te) else pr[1]
    if eq is not None and eq < 0 and not re.search(r"going concern", c.doc.all_text, re.I):
        return [Finding("SA-49", "Negative equity but no going-concern note/paragraph", "High",
                        f"Total equity {eq:,.0f}; 'going concern' not mentioned anywhere", te[2], "Going-concern disclosure", "absent")]
    return []


REGISTRY = {
    "SA-01": sa01_names, "SA-02": sa02_legal_status, "SA-04": sa04_signatory_spelling, "SA-05": sa05_signatory_sufficiency,
    "SA-06": sa06_years, "SA-07": sa07_report_date, "SA-08": sa08_licence_ref, "SA-09": sa09_authority, "SA-10": sa10_addressee,
    "SA-13": sa13_font, "SA-14": sa14_sizes, "SA-15": sa15_margins, "SA-16": sa16_justified,
    "SA-20": sa20_balance, "SA-21": sa21_cash, "SA-22": sa22_equity, "SA-24": sa24_tb,
    "SA-29": sa29_notes, "SA-30": sa30_standards, "SA-46": sa46_levels, "SA-47": sa47_ready_before_print, "SA-49": sa49_going_concern,
}


def run_fs(eng, doc, params, tb_path=None):
    from .rules_fs2 import A2_REGISTRY, ASSIST2_REGISTRY
    from .refs import add_refs
    ctx = Ctx(eng, doc, params, tb_path)
    results = []
    for cid, fn in {**REGISTRY, **A2_REGISTRY, **ASSIST2_REGISTRY}.items():
        try:
            fnds = fn(ctx)
            if getattr(fn, "assist", False):
                results.append(Result(cid, "REVIEW", fnds, "Assisted: evidence extracted, reviewer to confirm"))
            else:
                results.append(Result(cid, "EXC" if fnds else "PASS", fnds))
        except NotRun as e:
            results.append(Result(cid, "NA" if str(e).startswith("Applies to") else "NOTRUN", [], str(e)))
        except Exception as e:                       # one rule must never stop the review
            results.append(Result(cid, "NOTRUN", [], f"Rule could not run on this file: {type(e).__name__}: {str(e)[:120]}"))
    results.sort(key=lambda r: int(r.check_id.split("-")[1]))
    add_refs(doc, results)
    return results
