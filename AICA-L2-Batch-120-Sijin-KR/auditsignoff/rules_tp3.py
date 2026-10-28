"""Module C part 3 - the checklist rows that used to be manual, now evidence-driven.

mode:  (none)  deterministic: PASS / EXC
       hybrid  EXC when a real exception is found, REVIEW when only evidence is produced (judgement still needed), PASS when nothing to show
       assist  REVIEW with evidence only
"""
from __future__ import annotations
import difflib
import re
from pathlib import Path

import yaml

from .rules_fs import NotRun, canon, same_name, _is_tnr
from .rules_tp import _ex, _norm, _num, report_stats, quartiles

ROOT = Path(__file__).resolve().parent.parent
TITLE_RX = r"Transfer Pricing (?:Benchmark(?:ing)? Analysis|Financial Update)"
_AMT = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+|\d{5,})(?:\.\d+)?")
STOP_NAME = re.compile(r"^(company|name|minimum|maximum|median|quartile|lower|upper|average|mean|total|s\.?\s*no|sl|particulars|tested|number|statistic|interquartile|range|description|year|source|note)\b", re.I)
CURRENT_YEAR_TOKEN = re.compile(r"20\d\d")


def mode(m):
    def deco(fn):
        fn.mode = m
        return fn
    return deco


def _amts(t):
    return [float(m.group(1).replace(",", "")) for m in _AMT.finditer(t)]


def _sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", re.sub(r"[ \t]+", " ", t)) if s.strip()]


def _near(t, rx, width=200):
    return [t[max(0, m.start() - width): m.end() + width] for m in re.finditer(rx, t, re.I)]


def _need_fs(c):
    if not c.fs:
        raise NotRun("Audited FS not supplied (or could not be read - scanned PDF without OCR)")
    return re.sub(r"[ \t]+", " ", c.fs.all_text)


def _ratio(a, b):
    return difflib.SequenceMatcher(None, canon(a).lower(), canon(b).lower()).ratio()


def _docx_only(c):
    if c.doc.kind != "docx":
        raise NotRun("Needs the Word (DOCX) version of the report")


# ====================================================================== TOC helpers
def _toc(c):
    """-> (entries [(title, page|None)], title_para or None). Word: TOC styles or lines ending in a page number after 'Contents'."""
    entries, tpara = [], None
    if c.doc.kind == "docx":
        paras = [p for p in c.doc.paragraphs if p.where == "body"]
        for i, p in enumerate(paras):
            if re.fullmatch(r"\s*(table of )?contents?\s*", p.text, re.I):
                tpara = p
                break
        for p in paras:
            if (p.style or "").lower().startswith("toc") or (tpara and tpara.idx < p.idx <= tpara.idx + 90 and re.search(r"(\t|\.{3,}|\s{3,})\s*\d{1,3}\s*$", p.text)):
                m = re.match(r"^\s*(.*?)[\t. …_]*\s(\d{1,3})\s*$", p.text.strip()) or re.match(r"^\s*(.*\S)\s*$", p.text)
                if m and not re.fullmatch(r"\s*(table of )?contents?\s*", p.text, re.I):
                    entries.append((re.sub(r"\s+", " ", m.group(1)).strip(" ."), int(m.group(2)) if m.lastindex and m.lastindex >= 2 else None, p))
        return entries, tpara
    pages = c.doc.pages
    ti = next((i for i, p in enumerate(pages[:6]) if re.search(r"^\s*(table of )?contents?\s*$", p, re.I | re.M)), None)
    if ti is None:
        return [], None
    for mm in re.finditer(r"^\s*(.{4,90}?)[.\s_·…]{2,}\s*(\d{1,3})(?:\s*[-–]\s*\d{1,3})?\s*$", pages[ti], re.M):
        entries.append((re.sub(r"[.\s_·…]+$", "", mm.group(1)).strip(), int(mm.group(2)), None))
    return entries, ti


def _headings(c, levels=(1, 2)):
    out = []
    for p in c.doc.paragraphs:
        if p.where != "body":
            continue
        m = re.match(r"heading\s*(\d)", (p.style or "").lower())
        if m and int(m.group(1)) in levels and p.text.strip() and not re.fullmatch(r"\s*(table of )?contents?\s*", p.text, re.I):
            out.append(re.sub(r"\s+", " ", p.text).strip())
    return out


def _strip_num(s):
    return re.sub(r"^\s*(?:\d+(?:\.\d+)*[.)]?|[A-Z][.)])\s+", "", s).strip()


def _body_lines(c):
    if c.doc.kind == "docx":
        return [re.sub(r"\s+", " ", p.text).strip() for p in c.doc.paragraphs if p.where == "body" and p.text.strip()
                and not (re.search(r"(\t|\.{3,})\s*\d{1,3}\s*$", p.text) or (p.style or "").lower().startswith("toc"))]
    pages = c.doc.pages
    ti = next((i for i, p in enumerate(pages[:6]) if re.search(r"^\s*(table of )?contents?\s*$", p, re.I | re.M)), 0)
    return [re.sub(r"\s+", " ", l).strip() for p in pages[ti + 1:] for l in p.splitlines() if l.strip()]


# ====================================================================== 1.2 TOC
@mode(None)
def toc_complete(c):
    """Every Heading 1/2 appears in the TOC (the other direction is tested by the index check)."""
    _docx_only(c)
    entries, tp = _toc(c)
    if not entries:
        raise NotRun("No table of contents found in the Word file")
    titles = [canon(_strip_num(e[0])).lower() for e in entries]
    out = []
    for h in _headings(c):
        k = canon(_strip_num(h)).lower()
        if k and not any(k == t or _ratio(k, t) >= 0.92 for t in titles):
            out.append(_ex("TP-05", "Heading is missing from the table of contents", "Medium", f"'{h}' is a Heading 1/2 but has no TOC entry - update the field", "Table of contents", h, "absent"))
    return out[:12]


@mode(None)
def toc_text(c):
    entries, _ = _toc(c)
    if not entries:
        raise NotRun("No table of contents found")
    heads = _headings(c, (1, 2, 3)) if c.doc.kind == "docx" else _body_lines(c)
    out = []
    for title, pg, _p in entries:
        if title in heads or any(re.sub(r"\s+", " ", title) == h for h in heads):
            continue
        best = max(heads, key=lambda h: _ratio(_strip_num(h), _strip_num(title)), default=None)
        if not best or _ratio(_strip_num(best), _strip_num(title)) < 0.85:
            continue                                  # no counterpart at all: reported by the index check
        if _strip_num(best) == _strip_num(title):
            why = "numbering differs"
        elif _strip_num(best).lower() == _strip_num(title).lower():
            why = "upper/lower case differs"
        else:
            why = "spelling differs"
        out.append(_ex("TP-06", f"TOC text does not match the heading exactly ({why})", "Low", f"TOC: '{title}' / heading: '{best}'", "Table of contents", best, title))
    return out[:12]


@mode(None)
def toc_annexures(c):
    entries, _ = _toc(c)
    an = [(t, p) for t, p, _x in entries if re.match(r"\s*(annex|appendix)", t, re.I)]
    if not an:
        raise NotRun("No annexure entries in the table of contents")
    lines = _body_lines(c)
    out = []
    pmap = {}
    inv = {}
    if c.doc.kind != "docx":
        from .rules_tp import _printed_page_map
        pmap = _printed_page_map(c)
    for t, pg in an:
        best = max(lines, key=lambda l: _ratio(l, t), default="")
        if _ratio(best, t) < 0.88:
            out.append(_ex("TP-08", "Annexure listed in the TOC has no matching annexure heading", "Medium", f"'{t}' (TOC p.{pg})", "Table of contents", t, "not found"))
            continue
        if _strip_num(best) != _strip_num(t) and best != t:
            out.append(_ex("TP-08", "Annexure title in the TOC differs from the annexure page title", "Low", f"TOC '{t}' / page '{best}'", "Annexure", best, t))
        if pmap and pg:
            found = [pmap.get(i + 1) for i, p in enumerate(c.doc.pages) if i > 2 and re.search(r"^\s*" + re.escape(best) + r"\s*$", p, re.I | re.M) and pmap.get(i + 1)]
            if found and pg not in found:
                out.append(_ex("TP-08", "Annexure start page in the TOC is wrong", "Medium", f"'{t}': TOC p.{pg}, starts p.{found[0]}", "Table of contents", f"p.{found[0]}", f"p.{pg}"))
    return out


@mode(None)
def toc_format(c):
    P = c.p["heading_sizes"]
    out = []
    if c.doc.kind == "docx":
        entries, tp = _toc(c)
        if not entries:
            raise NotRun("No table of contents found")
        bad = {}
        if tp is not None:
            for r in tp.runs:
                if r.size is not None and abs(r.size - P["main"]) > 0.25:
                    out.append(_ex("TP-09", f"TOC heading is {r.size:g} pt, standard is {P['main']:g} pt", "Low", tp.text.strip(), "Table of contents", f"{P['main']:g} pt", f"{r.size:g} pt"))
                    break
        for _t, _pg, p in entries:
            if p is None:
                continue
            for r in p.runs:
                if r.font and not _is_tnr(r.font):
                    bad.setdefault(("font", r.font), p.loc)
                if r.size is not None and abs(r.size - P["body"]) > 0.25 and abs(r.size - P["sub"]) > 0.25:
                    bad.setdefault(("size", r.size), p.loc)
        for (k, v), loc in list(bad.items())[:5]:
            out.append(_ex("TP-09", f"TOC entries use {'font ' + str(v) if k == 'font' else str(v) + ' pt'}", "Low",
                           "Times New Roman, subheadings 12 pt, text 11 pt expected (grey area: the checklist does not say which TOC level takes 12 pt, so 11 or 12 pt are both accepted)", loc,
                           "Times New Roman" if k == "font" else "11 / 12 pt", str(v)))
        return out
    import pdfplumber
    entries, ti = _toc(c)
    if ti is None:
        raise NotRun("No table of contents page found")
    with pdfplumber.open(str(c.path)) as pdf:
        pg = pdf.pages[ti]
        fonts = {ch["fontname"].split("+")[-1] for ch in pg.chars}
        sizes = {round(ch["size"] * 2) / 2 for ch in pg.chars}
    for f in sorted(fonts):
        if not re.search(r"times|tnr|timesnewroman", f, re.I):
            out.append(_ex("TP-09", f"TOC page uses font '{f}'", "Low", "Times New Roman expected", f"p.{ti + 1}", "Times New Roman", f))
    for s in sorted(sizes):
        if min(abs(s - P["main"]), abs(s - P["sub"]), abs(s - P["body"])) > 0.3:
            out.append(_ex("TP-09", f"TOC page has {s:g} pt text", "Low", "19.5 / 12 / 11 pt expected", f"p.{ti + 1}", "19.5 / 12 / 11", f"{s:g}"))
    return out[:6]


# ====================================================================== 1.3 company details
FORMS = re.compile(r"\b(L\.?L\.?C\.?|FZ-?LLC|FZE|FZCO|DMCC|P\.?J\.?S\.?C\.?|PSC|Sole Proprietorship|Branch|Establishment)\b", re.I)


def _sent_with(t, rx):
    return [s for s in _sentences(t) if re.search(rx, s, re.I)]


@mode(None)
def profile_vs_fs(c):
    fs = _need_fs(c)
    rep = _norm(c)
    out = []
    rs, fsn = _sent_with(rep, r"incorporated|registered|established|legal form|limited liability|commenced"), _sent_with(fs, r"incorporated|registered|established|legal (status|form)|limited liability|commenced")
    nf = lambda ss: {re.sub(r"[.\s]", "", m.group(1)).upper() for s in ss for m in FORMS.finditer(s)}
    a, b = nf(rs), nf(fsn)
    if a and b and not (a & b):
        out.append(_ex("TP-10", "Legal form in the report differs from the notes to accounts", "Medium", f"Report {sorted(a)}; FS {sorted(b)}", "Company profile", str(sorted(b)), str(sorted(a))))
    dt = lambda ss: {m.group(0).lower() for s in ss for m in re.finditer(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d\d\b", s, re.I)}
    da, db = dt(rs), dt(fsn)
    if da and db and not (da & db):
        out.append(_ex("TP-10", "Date of incorporation in the report differs from the notes to accounts", "Medium", f"Report {sorted(da)}; FS {sorted(db)}", "Company profile", str(sorted(db)), str(sorted(da))))
    pct = lambda t: {m.group(0).replace(" ", "") for s in _sent_with(t, r"shareholder|owned|shareholding|holds|share capital|ownership") for m in re.finditer(r"\b\d{1,3}(?:\.\d+)?\s?%", s)}
    pa, pb = pct(rep), pct(fs)
    if pa and pb and not pa <= pb:
        out.append(_ex("TP-10", "Shareholding percentage in the report is not in the notes to accounts", "Medium", f"Report {sorted(pa)}; FS {sorted(pb)}", "Company profile", str(sorted(pb)), str(sorted(pa))))
    act = re.search(r"(?:principal activit\w+|nature of (?:the )?business|business activit\w+)[^.\n]{0,40}?(?:is|are|of)?[:\s]+([^.\n]{20,220})", fs, re.I)
    if act:
        w = {x for x in re.findall(r"[a-z]{5,}", act.group(1).lower())}
        if w and len(w & set(re.findall(r"[a-z]{5,}", rep.lower()))) / len(w) < 0.25:
            out.append(_ex("TP-10", "Business activity in the notes to accounts is not described in the report", "Low", f"FS: '{act.group(1)[:110]}'", "Company profile", "same activity", "not found"))
    return out


@mode("hybrid")
def functional(c):
    t = _norm(c)
    miss = [k for k, rx in (("functions", r"\bfunctions?\b"), ("assets", r"\bassets?\b"), ("risks", r"\brisks?\b")) if not re.search(rx, t, re.I)]
    has_fa = re.search(r"functional (analysis|profile)|FAR analysis", t, re.I)
    out = []
    if not has_fa:
        out.append(_ex("TP-15", "No functional analysis section found", "Medium", "Functions, assets and risks of the tested party should be analysed", "Report", "functional analysis", "absent"))
    elif miss:
        out.append(_ex("TP-15", "Functional analysis does not cover " + ", ".join(miss), "Medium", "Functions, assets and risks must all be addressed", "Functional analysis", "functions, assets, risks", f"missing {miss}"))
    why = re.search(r"[^.]*tested party[^.]*(because|since|as it|least complex|less complex|reliable|more reliable)[^.]*\.", t, re.I)
    if not why:
        out.append(_ex("TP-15", "Report does not explain why this entity is the tested party", "Medium", "No sentence links 'tested party' to a reason (least complex, reliable data)", "Report", "stated reason", "absent"))
    if not out:
        out.append(_ex("TP-15", "Functional analysis and tested-party reason found", "Info", "Reason: " + (why.group(0).strip()[:180] if why else ""), "Functional analysis"))
    return out


COMPONENTS = {"Salary": r"\b(basic )?salary|salaries|basic pay", "Bonus": r"\bbonus", "Allowances": r"allowance|housing|accommodation allowance|transport",
              "End-of-service": r"end[- ]of[- ]service|\bEOSB\b|gratuity", "Share-based pay": r"share[- ]based|\bESOP\b|stock option", "Benefits in kind": r"benefits? in kind|\bBIK\b|company car|medical|tickets?|insurance"}


def _components(text):
    got = {}
    for ln in text.splitlines():
        for k, rx in COMPONENTS.items():
            if re.search(rx, ln, re.I):
                a = [x for x in _amts(ln) if not (1990 <= x <= 2100)]
                if a:
                    got[k] = got.get(k, 0) + max(a)
    return got


def _num_cell(x):
    v = _num(x) if re.search(r"\d", str(x)) else None
    return v


def _birf_table(birf):
    """Column layout (the firm's BIRF template): header row with Salary / Bonus / ... columns, one row per recipient.
    -> (components {name: amount}, people [names], totals-row amount or None) or None when no such table."""
    for tb in birf.tables:
        for hi, row in enumerate(tb.rows[:10]):
            cols = {j: k for j, cell in enumerate(row) for k, rx in COMPONENTS.items() if re.search(rx, str(cell), re.I)}
            if len({*cols.values()}) < 2:
                continue
            ni = next((j for j, cell in enumerate(row) if re.search(r"name|recipient", str(cell), re.I)), 0)
            comp, people, total_row = {}, [], None
            for r in tb.rows[hi + 1:]:
                nm = (r[ni] if len(r) > ni else "").strip()
                vals = {j: _num_cell(r[j]) for j in cols if len(r) > j}
                if re.fullmatch(r"total.*", nm, re.I):
                    total_row = sum(v for v in vals.values() if v) or None
                    continue
                if not nm or not re.search(r"[A-Za-z]{3}", nm):
                    continue
                people.append(nm)
                for j, v in vals.items():
                    if v:
                        comp[cols[j]] = comp.get(cols[j], 0) + v
            return comp, people, total_row
    return None


@mode(None)
def rem_split_birf(c):
    if not getattr(c, "birf", None):
        raise NotRun("BIRF not supplied - upload the Benchmarking Information Request Form")
    bt = _birf_table(c.birf)
    comp = bt[0] if bt and bt[0] else _components(c.birf.all_text)
    if not comp:
        raise NotRun("No remuneration components with amounts recognised in the BIRF")
    rep = _norm(c)
    ra = _amts(rep)
    out = []
    for k, v in comp.items():
        if not any(abs(v - a) <= max(1.0, 0.005 * v) for a in ra):
            out.append(_ex("TP-16", f"BIRF {k.lower()} amount is not in the report", "High", f"BIRF {k}: AED {v:,.0f} - no matching figure in the report", "Remuneration table", f"{v:,.0f}", "not found"))
    tot = sum(comp.values())
    tm = [a for ln in c.doc.all_text.splitlines() if re.search(r"total (managerial )?remuneration|total compensation", ln, re.I) for a in _amts(ln)]
    if tm and not any(abs(tot - a) <= max(1.0, 0.005 * tot) for a in tm):
        out.append(_ex("TP-16", "Components per the BIRF do not add up to the total in the report", "High", f"BIRF components add to AED {tot:,.0f}; report totals {sorted(set(tm))[:3]}. Grey area: the BIRF may list several recipients - confirm the report total covers the same persons.", "Remuneration table", f"{tot:,.0f}", str(sorted(set(tm))[:2])))
    return out


# ====================================================================== 1.4 subheadings
@mode(None)
def subheading_format(c):
    _docx_only(c)
    P = c.p["heading_sizes"]
    out, bad, nums = [], {}, {"num": 0, "plain": 0}
    for p in c.doc.paragraphs:
        if p.where != "body" or not re.match(r"heading\s*[23]", (p.style or "").lower()) or not p.text.strip():
            continue
        nums["num" if re.match(r"\d+(\.\d+)+", p.text.strip()) else "plain"] += 1
        for r in p.runs:
            if r.font and not _is_tnr(r.font):
                bad.setdefault(("font", r.font), p.loc)
            if r.size is not None and abs(r.size - P["sub"]) > 0.25:
                bad.setdefault(("size", r.size), p.loc)
    for (k, v), loc in list(bad.items())[:5]:
        out.append(_ex("TP-19", f"Subheading {'font ' + str(v) if k == 'font' else 'size ' + str(v) + ' pt'}", "Low", "Times New Roman 12 expected for subheadings", loc, "Times New Roman" if k == "font" else "12 pt", str(v)))
    if nums["num"] and nums["plain"]:
        out.append(_ex("TP-19", "Subheading numbering is inconsistent", "Low", f"{nums['num']} numbered and {nums['plain']} unnumbered subheadings", "Subheadings", "one numbering style", "mixed"))
    return out


# ====================================================================== 1.6 PLI rationale
@mode("hybrid")
def pli_rationale(c):
    t = _norm(c)
    named = [k for k, rx in (("OP/OR", r"\bOP\s*/\s*OR\b|operating (?:profit )?margin"), ("OP/OC", r"\bOP\s*/\s*OC\b|net cost plus|operating profit (?:to|/|over) operating cost"), ("EC/OC", r"\bEC\s*/\s*OC\b")) if re.search(rx, t, re.I)]
    out = []
    if not named and re.search(r"(profit level indicator|PLI)[^.]{0,80}not (applicable|used|relevant)|no profit[- ]based indicator|comparable uncontrolled price|\bCUP\b", t, re.I) \
            and re.search(r"remuneration|compensation|salary", t, re.I) and not re.search(r"\bTNMM\b[^.]{0,60}(is|was) (the )?(most appropriate|selected|applied|chosen)", t, re.I):
        return []                                    # absolute-remuneration benchmark under the CUP method: no profit indicator is expected
    if not named:
        out.append(_ex("TP-28", "No profit level indicator is named in the report", "Medium", "OP/OR, OP/OC (or EC/OC as supplement) expected for TNMM", "Report", "PLI named", "absent"))
        return out
    if named == ["EC/OC"]:
        out.append(_ex("TP-28", "EC/OC is the only indicator named", "Medium", "EC/OC is a supplementary indicator and must not stand alone as the TNMM PLI", "Report", "OP/OR or OP/OC", "EC/OC"))
    sent = [s for s in _sentences(t) if re.search(r"\bPLI\b|profit level indicator|OP\s*/\s*O[RC]|net cost plus", s, re.I) and re.search(r"because|appropriate|since|selected|chosen|reliable|least affected|best measures|suitable", s, re.I)]
    if not sent:
        out.append(_ex("TP-28", "The rationale for the PLI chosen is not stated", "Medium", f"PLI named: {named}; no sentence explains why it is appropriate", "Report", "stated rationale", "absent"))
    if not out:
        out.append(_ex("TP-28", "PLI and rationale found", "Info", f"PLI(s): {named}. Rationale: {sent[0][:200]}", "Report"))
    return out


# ====================================================================== 1.8 full report
class _Sheet:
    def __init__(self, title, rows):
        self.title, self._rows = title, rows

    def iter_rows(self, values_only=True):
        return iter(self._rows)


class _Book:
    def __init__(self, sheets):
        self.worksheets = sheets


def _wb_rows(path):
    """Reads every sheet into memory and CLOSES the file (Windows keeps a read-only workbook locked, which blocks deleting the temp folder)."""
    import openpyxl
    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    try:
        return _Book([_Sheet(ws.title, [tuple(r) for r in ws.iter_rows(values_only=True)]) for ws in wb.worksheets])
    finally:
        wb.close()


@mode(None)
def rejected_reasons(c):
    if not getattr(c, "wb_path", None) or str(c.wb_path).lower().endswith(".xls"):
        raise NotRun("Benchmarking workbook (.xlsx) not supplied")
    wb = _wb_rows(c.wb_path)
    out, seen = [], False
    for ws in wb.worksheets:
        if not re.search(r"reject|exclu|screen|search|stage|funnel", ws.title, re.I):
            continue
        rows = list(ws.iter_rows(values_only=True))
        hi = next((i for i, r in enumerate(rows[:15]) if any(isinstance(x, str) and re.search(r"reason|rejection|rationale|comment|criteria", x, re.I) for x in r)), None)
        if hi is None:
            continue
        seen = True
        h = rows[hi]
        rc = next(i for i, x in enumerate(h) if isinstance(x, str) and re.search(r"reason|rejection|rationale|comment|criteria", x, re.I))
        nc = next((i for i, x in enumerate(h) if isinstance(x, str) and re.search(r"company|name", x, re.I)), 0)
        blanks, generic, reasons = [], [], {}
        for r in rows[hi + 1:]:
            if len(r) <= max(rc, nc) or not r[nc] or not str(r[nc]).strip():
                continue
            v = str(r[rc]).strip() if r[rc] is not None else ""
            if not v:
                blanks.append(str(r[nc]))
            elif re.fullmatch(r"(n/?a|-+|\.+|nil|none|other)", v, re.I):
                generic.append(str(r[nc]))
            else:
                reasons[re.sub(r"\d+", "#", v.lower())] = reasons.get(re.sub(r"\d+", "#", v.lower()), 0) + 1
        if blanks:
            out.append(_ex("TP-38", "Rejected comparable has no recorded reason", "Medium", f"Sheet '{ws.title}': {len(blanks)} without a reason, e.g. {', '.join(blanks[:4])}", ws.title, "reason for every rejection", f"{len(blanks)} blank"))
        if generic:
            out.append(_ex("TP-38", "Rejection reason is not specific", "Low", f"Sheet '{ws.title}': {len(generic)} marked n/a / other / dash, e.g. {', '.join(generic[:4])}", ws.title, "specific criterion", "n/a"))
        if len(reasons) > 12 and sum(1 for v in reasons.values() if v == 1) / len(reasons) > 0.6:
            out.append(_ex("TP-38", "Rejection criteria are applied inconsistently", "Low", f"{len(reasons)} different reason wordings; most used once - standardise the criteria codes", ws.title, "consistent criteria", f"{len(reasons)} wordings"))
    if not seen:
        raise NotRun("No rejected-comparables sheet with a reason column recognised in the workbook")
    return out


@mode("hybrid")
def data_periods(c):
    t = _norm(c)
    single = re.search(r"single[- ]year|one[- ]year|current[- ]year data|year[- ]of[- ]review", t, re.I)
    multi = re.search(r"multi(?:ple)?[- ]year|(\d)[- ]year (?:weighted )?average|weighted average|three[- ]year|average of", t, re.I)
    out = []
    ncols = None
    if getattr(c, "wb_path", None) and not str(c.wb_path).lower().endswith(".xls"):
        yrs = set()
        for ws in _wb_rows(c.wb_path).worksheets:
            for r in list(ws.iter_rows(values_only=True))[:12]:
                for x in r:
                    if isinstance(x, (str, int)) and re.fullmatch(r"(?:FY\s?)?(20\d\d)", str(x).strip(), re.I):
                        yrs.add(int(re.search(r"20\d\d", str(x)).group(0)))
        ncols = len(yrs)
    if not single and not multi:
        out.append(_ex("TP-39", "The data period (single-year or multi-year average) is not stated", "Medium", "State whether comparables use single-year or multi-year averages", "Report", "stated", "absent"))
    elif single and not multi and ncols and ncols > 1:
        out.append(_ex("TP-39", "Report says single-year data but the workbook carries several years", "Medium", f"Workbook headers show {ncols} financial years", "Report vs workbook", "one convention", f"{ncols} years"))
    elif multi and not single and ncols == 1:
        out.append(_ex("TP-39", "Report says multi-year averages but the workbook has one year", "Medium", "Only one financial year column found", "Report vs workbook", "multi-year", "1 year"))
    if not out:
        out.append(_ex("TP-39", "Data period statements", "Info", f"Report: {'single-year' if single else ''} {'multi-year' if multi else ''}; workbook years: {ncols if ncols is not None else 'n/a'}", "Report"))
    return out


@mode("hybrid")
def method_rejection(c):
    t = _norm(c)
    chosen = "TNMM" if re.search(r"\bTNMM\b|transactional net margin", t, re.I) else "CUP" if re.search(r"\bCUP\b|comparable uncontrolled", t, re.I) else None
    others = {"CUP": r"\bCUP\b|comparable uncontrolled price", "Resale Price": r"resale price", "Cost Plus": r"cost[- ]plus method", "Profit Split": r"profit[- ]split", "TNMM": r"\bTNMM\b|transactional net margin"}
    generic = re.search(r"other (?:OECD )?(?:transfer pricing )?methods?[^.]{0,120}(not (?:appropriate|suitable|applicable|reliable)|rejected|discarded|considered)", t, re.I)
    miss, ev = [], []
    for k, rx in others.items():
        if k == chosen:
            continue
        s = [x for x in _sentences(t) if re.search(rx, x, re.I) and re.search(r"not (?:appropriate|suitable|applicable|reliable|used|selected|adopted)|reject|unreliable|no reliable|unable|lack|insufficient|inappropriate", x, re.I)]
        if s:
            ev.append(f"{k}: {s[0][:140]}")
        else:
            miss.append(k)
    if chosen is None:
        return [_ex("TP-40", "No method (TNMM / CUP) is named, so rejection cannot be tested", "Medium", "Name the primary method", "Report", "TNMM or CUP", "none")]
    if miss and not generic:
        return [_ex("TP-40", "No reason is given for not using: " + ", ".join(miss), "Medium", f"Primary method {chosen}. Each other OECD method needs a stated reason (or one sentence covering all)", "Method selection", "reason per method", f"{len(miss)} missing")]
    return [_ex("TP-40", "Method rejection reasons found", "Info", f"Primary {chosen}. " + " | ".join(ev[:4]) + (" | generic rejection sentence present" if generic else ""), "Method selection")]


POS = r"within|consistent|supports?|corroborat|in line|aligned|falls? in|arm'?s length"
NEG = r"outside|exceeds?|above the|below the|not consistent|inconsistent|higher than|lower than|does not support|not within|not aligned"


def _polarity(s):
    n, p = bool(re.search(NEG, s, re.I)), bool(re.search(POS, s, re.I))
    return "neg" if n else "pos" if p else None


@mode("hybrid")
def secondary_conclusion(c):
    t = _norm(c)
    sec = [s for s in _sentences(t) if re.search(r"corroborat|secondary|salary survey|salary database|market (salary|remuneration)|recruiter", s, re.I) and _polarity(s)]
    if not sec:
        raise NotRun("No secondary / corroborative analysis conclusion found in the report")
    pri = [s for s in _sentences(t) if re.search(r"interquartile|arm'?s length range|benchmarking (analysis|result)|TNMM|PLI", s, re.I) and _polarity(s) and s not in sec]
    ps = {_polarity(s) for s in pri}
    ss = {_polarity(s) for s in sec}
    if ps and ss and ps != ss:
        return [_ex("TP-43", "Secondary conclusion contradicts the primary method conclusion", "High", f"Primary: '{pri[0][:150]}' / Secondary: '{sec[0][:150]}'", "Conclusion", "consistent conclusions", "contradiction")]
    return [_ex("TP-43", "Secondary and primary conclusions", "Info", f"Secondary: '{sec[0][:170]}'" + (f"; primary: '{pri[0][:150]}'" if pri else ""), "Conclusion")]


# ====================================================================== 1.10 charts
def _charts(c):
    if c.doc.kind != "docx":
        return None
    import zipfile
    z = zipfile.ZipFile(str(c.path))
    out = []
    for n in sorted(x for x in z.namelist() if re.match(r"word/charts/chart\d+\.xml$", x)):
        x = z.read(n).decode("utf8", "ignore")
        kind = re.search(r"<c:(bar|line|pie|scatter|area|doughnut)Chart", x)
        ttl = re.search(r"<c:title>(.*?)</c:title>", x, re.S)
        ax = [" ".join(re.findall(r"<a:t>(.*?)</a:t>", m)) for m in re.findall(r"<c:(?:catAx|valAx)>.*?</c:(?:catAx|valAx)>", x, re.S) if "<c:title>" in m for m in [re.search(r"<c:title>(.*?)</c:title>", m, re.S).group(1)]]
        vals = [[float(v) for v in re.findall(r"<c:v>(-?[\d.]+(?:E-?\d+)?)</c:v>", s)] for s in re.findall(r"<c:val>(.*?)</c:val>", x, re.S)]
        cats = re.findall(r"<c:cat>(.*?)</c:cat>", x, re.S)
        cat = re.findall(r"<c:v>(.*?)</c:v>", cats[0]) if cats else []
        mn = re.search(r"<c:valAx>.*?<c:scaling>.*?<c:min val=\"(-?[\d.]+)\"", x, re.S)
        out.append({"name": n.split("/")[-1], "kind": kind.group(1) if kind else "?", "title": " ".join(re.findall(r"<a:t>(.*?)</a:t>", ttl.group(1))) if ttl else "",
                    "axes": ax, "legend": "<c:legend>" in x, "series": vals, "cats": cat, "min": float(mn.group(1)) if mn else None})
    return out


@mode("hybrid")
def chart_scale(c):
    ch = _charts(c)
    if ch is None:
        raise NotRun("Charts can be read from the Word file only")
    if not ch:
        import zipfile
        pics = [n for n in zipfile.ZipFile(str(c.path)).namelist() if n.startswith("word/media/")]
        if pics:
            return [_ex("TP-53", "Charts are pictures - scale and labels cannot be read", "Info", f"{len(pics)} picture(s); paste native Word/Excel charts so axes, units and legend can be tested", "Charts")]
        raise NotRun("No charts in the report")
    out = []
    for g in ch:
        if g["kind"] not in ("pie", "doughnut") and len(g["axes"]) < 2:
            out.append(_ex("TP-53", "Chart axis title missing", "Low", f"{g['name']} '{g['title'][:40]}' has {len(g['axes'])} axis title(s)", g["name"], "both axes titled", str(len(g["axes"]))))
        if not g["title"]:
            out.append(_ex("TP-53", "Chart has no title", "Low", g["name"], g["name"], "title", "none"))
        if len(g["series"]) > 1 and not g["legend"]:
            out.append(_ex("TP-53", "Chart has several series but no legend", "Medium", g["name"], g["name"], "legend", "none"))
        if g["kind"] == "bar" and g["min"] is not None and g["min"] > 0:
            out.append(_ex("TP-53", "Bar chart axis does not start at zero", "Medium", f"{g['name']}: axis minimum {g['min']:g} exaggerates differences", g["name"], "0", f"{g['min']:g}"))
        allv = [v for s in g["series"] for v in s]
        txt = g["title"] + " ".join(g["axes"])
        if allv and not re.search(r"%|AED|percent|margin|USD|\$", txt, re.I):
            out.append(_ex("TP-53", "Chart units are not shown", "Low", f"{g['name']}: no %/AED in the title or axis titles", g["name"], "units", "none"))
        if g["title"] and not CURRENT_YEAR_TOKEN.search(g["title"] + " ".join(g["axes"])) and not re.search(r"FY|year|period", g["title"], re.I):
            out.append(_ex("TP-53", "Chart period is not shown", "Low", f"{g['name']}: add the financial year to the title", g["name"], "period", "none"))
    return out[:10] or [_ex("TP-53", "Chart scale, labels and legend are in order", "Info", f"{len(ch)} native chart(s) tested", "Charts")]


@mode("hybrid")
def chart_data(c):
    ch = _charts(c)
    if ch is None:
        return []
    if not ch:
        return []
    out = []
    if c.wb and c.wb.comps:
        wv = sorted(round(v, 2) for v in c.wb.values)
        for g in ch:
            for s in g["series"]:
                if len(s) >= 4:
                    sv = sorted(round(v * 100 if all(abs(x) < 1.5 for x in s) else v, 2) for v in s)
                    if len(sv) != len(wv):
                        out.append(_ex("TP-52", "Chart has a different number of points from the workbook", "High", f"{g['name']}: {len(sv)} points vs {len(wv)} comparables", g["name"], str(len(wv)), str(len(sv))))
                    else:
                        bad = [(a, b) for a, b in zip(sv, wv) if abs(a - b) > 0.06]
                        if bad:
                            out.append(_ex("TP-52", "Chart values do not agree with the workbook", "High", f"{g['name']}: {len(bad)} point(s) differ, e.g. chart {bad[0][0]} vs workbook {bad[0][1]}", g["name"], str(bad[0][1]), str(bad[0][0])))
    return out


@mode("hybrid")
def chart_message(c):
    ch = _charts(c)
    if not ch:
        raise NotRun("No native charts to compare with the narrative")
    t = _norm(c)
    sents = [s for s in _sentences(t) if re.search(r"\b(chart|figure|graph)\b", s, re.I)]
    out = []
    for g in ch:
        for s in g["series"]:
            if len(s) < 5 or not g["cats"]:
                continue
            tested = next((i for i, k in enumerate(g["cats"]) if re.search(r"tested|actual|company|client", k, re.I)), None)
            if tested is None:
                continue
            rest = [v for i, v in enumerate(s) if i != tested]
            q1, _m, q3 = quartiles(rest, c.p["quartile_method"])[:3] if isinstance(quartiles(rest, c.p["quartile_method"]), (list, tuple)) else (None, None, None)
            if q1 is None:
                continue
            pos = "within" if q1 <= s[tested] <= q3 else "outside"
            for sn in sents:
                if re.search(r"within the (?:interquartile )?range|falls within", sn, re.I) and pos == "outside" or re.search(r"outside the (?:interquartile )?range|falls outside|exceeds the range", sn, re.I) and pos == "within":
                    out.append(_ex("TP-54", "Narrative contradicts the chart", "High", f"{g['name']}: tested party is {pos} the interquartile range of the plotted comparables but the text says: '{sn[:150]}'", g["name"], pos, sn[:60]))
    return out or [_ex("TP-54", "Chart messages", "Info", f"{len(ch)} chart(s); narrative sentences about charts: {len(sents)}. {' | '.join(s[:120] for s in sents[:2])}", "Charts")]


# ====================================================================== 1.11 consistency
@mode(None)
def naming_consistency(c):
    t = _norm(c)
    out = []
    nm = canon(c.name)
    toks = nm.split()
    if len(toks) >= 2:
        n = len(toks)
        forms = {}
        for ln in t.splitlines():
            w = ln.split()
            for i in range(0, len(w) - n + 1):
                cand = " ".join(w[i:i + n]).strip(".,;:()'\"")
                if cand.lower() != nm.lower() and not same_name(cand, nm) and _ratio(cand, nm) >= 0.82 and cand.split()[0].lower().strip(".,") == toks[0].lower():
                    forms[cand] = forms.get(cand, 0) + 1
        if forms:
            out.append(_ex("TP-56", "Tested party is not named identically everywhere", "Low", "Variants: " + "; ".join(f"'{k}' x{v}" for k, v in list(forms.items())[:4]) + f" vs '{c.name}'", "Whole report", c.name, ", ".join(list(forms)[:2])))
    ends = {m.group(1) for m in re.finditer(r"(?:year|period) ended\s+(\d{1,2}\s+\w+\s+20\d\d)", t, re.I)}
    if len(ends) > 1:
        out.append(_ex("TP-56", "Period is not stated identically everywhere", "Medium", f"Period-end dates quoted: {sorted(ends)}", "Whole report", "one period", str(sorted(ends))))
    plis = [k for k, rx in (("OP/OC", r"\bOP\s*/\s*OC\b"), ("OP/OR", r"\bOP\s*/\s*OR\b")) if re.search(rx, t, re.I)]
    if len(plis) > 1:
        out.append(_ex("TP-56", "PLI is named differently in different places", "Medium", f"Both {plis} appear - the tested PLI must be named the same way in every table and paragraph", "Whole report", "one PLI name", " / ".join(plis)))
    return out


# ====================================================================== 1.12 financial update
def _split(c):
    """-> dict(cur_text, prior_text, cur_tables, prior_tables). Prior-year report is attached after the update (inside the same file)."""
    t = c.doc.text
    cuts = [m.start() for m in re.finditer(r"^\s*(?:table of )?contents?\s*$", t, re.I | re.M)]
    titles = [m.start() for m in re.finditer(r"^\s*" + TITLE_RX + r"\s*$", t, re.I | re.M)]
    cut = None
    if len(cuts) >= 2:
        before = [x for x in titles if cuts[0] < x < cuts[1]]
        cut = before[-1] if before else cuts[1]
    elif len([x for x in titles if x > len(t) * 0.25]) >= 1:
        cut = [x for x in titles if x > len(t) * 0.25][0]
    if cut is None:
        raise NotRun("The prior-year report was not found inside the document (attach it after the update)")
    out = {"cur_text": t[:cut], "prior_text": t[cut:], "cur_tables": [], "prior_tables": []}
    if c.doc.kind == "docx":
        import docx
        d = docx.Document(str(c.path))
        pi, tbl, off = 0, 0, 0
        paras = [p for p in c.doc.paragraphs if p.where == "body"]
        cum, acc = [], 0
        for p in paras:
            cum.append(acc); acc += len(p.text) + 1
        split_idx = next((i for i, a in enumerate(cum) if a >= cut), len(paras))
        for ch in d.element.body.iterchildren():
            tag = ch.tag.split("}")[-1]
            if tag == "p":
                pi += 1
            elif tag == "tbl":
                (out["prior_tables"] if pi > split_idx else out["cur_tables"]).append(c.doc.tables[tbl] if tbl < len(c.doc.tables) else None)
                tbl += 1
        out["cur_tables"] = [x for x in out["cur_tables"] if x]; out["prior_tables"] = [x for x in out["prior_tables"] if x]
    return out


def _names_from_tables(tables):
    names = []
    for tb in tables:
        for r in tb.rows:
            if len(r) < 2:
                continue
            a = (r[0] or "").strip()
            if len(a) < 5 or STOP_NAME.match(a) or not re.search(r"[A-Za-z]{4}", a) or re.fullmatch(r"[\d.,% ]+", a):
                continue
            if not any(re.fullmatch(r"-?\(?\d[\d,]*\.?\d*\)?\s*%?", (x or "").strip()) for x in r[1:]):
                continue
            if a not in names:
                names.append(a)
    return names


def _cur_names(c, sp):
    if c.wb and c.wb.comps:
        return [n for n, _v in c.wb.comps]
    return _names_from_tables(sp["cur_tables"])


def _match(a, pool, thr=0.9):
    return next((b for b in pool if same_name(a, b) or _ratio(a, b) >= thr), None)


REASON = r"acquir|delist|independen|change in (?:the )?business|business (?:model )?change|insufficient|missing data|data (?:is )?not available|no longer|bankrupt|liquidat|merge|loss[- ]making|reclassif|ceased|not available|restructur"


def _changes(c):
    _docx_only(c)
    sp = _split(c)
    cur, pri = _cur_names(c, sp), _names_from_tables(sp["prior_tables"])
    if not pri:
        raise NotRun("Prior-year comparables table not recognised")
    if not cur:
        raise NotRun("Current comparables not recognised (supply the workbook)")
    kept = [n for n in cur if _match(n, pri)]
    added = [n for n in cur if not _match(n, pri)]
    dropped = [n for n in pri if not _match(n, cur)]
    return sp, kept, added, dropped


def _reason_near(text, name):
    for m in re.finditer(re.escape(name.split()[0]), text, re.I):
        w = text[max(0, m.start() - 350): m.end() + 450]
        if _ratio(name, w[:len(name) + 20]) > 0.5 or name.lower() in w.lower():
            r = re.search(REASON, w, re.I)
            if r:
                return w[max(0, r.start() - 60): r.end() + 60].replace("\n", " ")
    return None


@mode("hybrid")
def comps_retained(c):
    sp, kept, added, dropped = _changes(c)
    if not added and not dropped:
        return []
    return [_ex("TP-63", "Comparable set changed since last year", "Info", f"Retained {len(kept)}; dropped {len(dropped)} ({', '.join(dropped[:4])}); added {len(added)} ({', '.join(added[:4])}). Reasons are tested at the next two checks.", "Comparables", "same set", f"-{len(dropped)} / +{len(added)}")]


@mode("hybrid")
def dropped_reason(c):
    sp, kept, added, dropped = _changes(c)
    if not dropped:
        return []
    out, ok = [], []
    for n in dropped:
        r = _reason_near(sp["cur_text"], n)
        if r:
            ok.append(f"{n}: {r[:110]}")
        else:
            out.append(_ex("TP-64", "Comparable dropped without a stated reason", "High", f"'{n}' was accepted last year and is not in this year's set; no acquisition / delisting / independence / business-change / missing-data reason found in the update", "Comparables", "documented valid reason", "none"))
    return out or [_ex("TP-64", "Reasons for dropped comparables found", "Info", " | ".join(ok[:4]) + " - confirm each is valid", "Comparables")]


@mode("hybrid")
def added_reason(c):
    sp, kept, added, dropped = _changes(c)
    if not added:
        return []
    out, ok = [], []
    prior_all = sp["prior_text"]
    for n in added:
        was_rej = bool(re.search(re.escape(n.split()[0]) + r"[^\n]{0,80}", prior_all, re.I)) and not _match(n, _names_from_tables(sp["prior_tables"]))
        cur_reason = re.search(r"newly|now (?:meets|satisfies|independent)|added|included (?:this|in the current)|passes? the|previously (?:rejected|excluded)", " ".join(_near(sp["cur_text"], re.escape(n.split()[0]), 300)), re.I)
        if cur_reason:
            ok.append(f"{n}{' (previously rejected)' if was_rej else ''}")
        else:
            out.append(_ex("TP-65", "Comparable added without an explanation" + (" (it was rejected last year)" if was_rej else ""), "High" if was_rej else "Medium",
                           f"'{n}' is new in this year's set" + ("; it appeared on last year's rejected list - state why it now qualifies (no cherry-picking)" if was_rej else "; state why it was added"), "Comparables", "documented reason", "none"))
    return out or [_ex("TP-65", "Added comparables are explained", "Info", ", ".join(ok[:5]) + " - confirm the reasons are valid", "Comparables")]


def _sub(c, text, tables):
    class D: pass
    class X: pass
    x = X(); x.doc = D(); x.doc.tables = tables; x.full_text = lambda: re.sub(r"[ \t]+", " ", text); x.p = c.p; x.wb = None
    return x


@mode("hybrid")
def range_movement(c):
    _docx_only(c)
    sp = _split(c)
    cs, ps = _sub(c, sp["cur_text"], sp["cur_tables"]), _sub(c, sp["prior_text"], sp["prior_tables"])
    cur = {}
    prior = {}
    for dst, ctx in ((cur, cs), (prior, ps)):
        for k, v, _loc in report_stats(ctx):
            dst.setdefault(k, v)
    keys = [k for k in ("q1", "median", "q3") if k in cur and k in prior]
    if not keys:
        raise NotRun("IQR statistics could not be read from both the update and the prior report")
    lim = c.p.get("range_move_pct", 25)
    mv = [(k, prior[k], cur[k], (cur[k] - prior[k]) / abs(prior[k]) * 100 if prior[k] else 0) for k in keys]
    big = [m for m in mv if abs(m[3]) > lim]
    explained = re.search(r"compared (?:with|to) (?:the )?(?:prior|previous|last)|(?:prior|previous|last) (?:year|period)|year[- ]on[- ]year|movement|moved|increase[d]? from|decrease[d]? from", sp["cur_text"], re.I)
    pos = re.search(r"(?:within|outside|above|below)[^.]{0,60}(?:range|interquartile)", sp["cur_text"], re.I)
    out = []
    if big and not explained:
        out.append(_ex("TP-66", "IQR moved materially and the update does not explain it", "High", "; ".join(f"{k}: {a:g} -> {b:g} ({d:+.0f}%)" for k, a, b, d in big), "Conclusion", f"explained movement (> {lim}%)", "no explanation"))
    if not pos:
        out.append(_ex("TP-66", "The tested party's position against the range is not restated", "Medium", "No 'within / outside the range' statement in the update", "Conclusion", "position stated", "absent"))
    return out or [_ex("TP-66", "Range movement", "Info", "; ".join(f"{k}: {a:g} -> {b:g} ({d:+.0f}%)" for k, a, b, d in mv), "Conclusion")]


@mode("hybrid")
def yoy(c):
    sp = _split(c)
    def amts(text, rx):
        v = []
        for ln in text.splitlines():
            if re.search(rx, ln, re.I):
                v += [a for a in _amts(ln) if not (1990 <= a <= 2100)]
        return v
    out, info = [], []
    lim = c.p.get("range_move_pct", 25)
    comp = bool(re.search(r"compared (?:with|to)|(?:prior|previous|last) (?:year|period)|year[- ]on[- ]year|increase|decrease|movement", sp["cur_text"], re.I))
    for lab, rx in (("remuneration", r"remuneration|compensation"), ("disallowance", r"disallow|excess over|adjustment")):
        a, b = amts(sp["cur_text"], rx), amts(sp["prior_text"], rx)
        if not a or not b:
            continue
        ca, pb = max(a), max(b)
        d = (ca - pb) / pb * 100 if pb else 0
        info.append(f"{lab}: {pb:,.0f} -> {ca:,.0f} ({d:+.0f}%)")
        if abs(d) > min(lim, 10) and not comp:
            out.append(_ex("TP-67", f"Year-on-year movement in {lab} is not explained", "Medium", f"{lab} {pb:,.0f} -> {ca:,.0f} ({d:+.0f}%); the update has no comparison with the prior year", "Conclusion", "explained movement", "none"))
    if not info:
        raise NotRun("Remuneration / disallowance amounts could not be read from both reports")
    return out or [_ex("TP-67", "Year-on-year view", "Info", "; ".join(info), "Conclusion")]


def _fy_of(text):
    m = re.findall(r"(?:year|period) ended\s+(?:\d{1,2}\s+\w+\s+)?(20\d\d)|(?:FY|financial year)\s*(20\d\d)", text[:4000], re.I)
    ys = [int(a or b) for a, b in m]
    return max(set(ys), key=ys.count) if ys else None


@mode("hybrid")
def validity(c):
    sp = _split(c)
    py = _fy_of(sp["prior_text"])
    sd = re.search(r"(?:search|extraction|extracted|accessed|retrieved|data)[^.\n]{0,40}(20\d\d)", sp["prior_text"], re.I)
    base = int(sd.group(1)) if sd else py
    if not base:
        raise NotRun("Year of the prior benchmarking could not be read")
    lim = c.p.get("refresh_cycle_years", 3)
    gap = c.cy - base
    if gap >= lim:
        return [_ex("TP-58", "Prior benchmarking is outside the refresh cycle", "Medium", f"Prior benchmark year {base}; this report {c.cy} (gap {gap} yrs, cycle {lim}). Grey area: the firm's cycle and the FTA's position should be confirmed; a full benchmark may be due.", "Prior report", f"gap < {lim} yrs", f"{gap} yrs")]
    return [_ex("TP-58", "Prior benchmarking within the refresh cycle", "Info", f"Prior benchmark year {base}; this report {c.cy} (gap {gap} yr; cycle {lim}).", "Prior report")]


def _persons(t):
    return {re.sub(r"\s+", " ", m.group(1)).strip() for m in re.finditer(r"\b(?:Mr|Ms|Mrs|Dr|Eng|Sheikh|Sh)\.?\s+([A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+){0,3})", t)}


@mode("hybrid")
def change_in_facts(c):
    sp = _split(c)
    a, b = _persons(sp["cur_text"]), _persons(sp["prior_text"])
    left = [n for n in b if not any(same_name(n, m) or _ratio(n, m) > 0.88 for m in a)]
    new = [n for n in a if not any(same_name(n, m) or _ratio(n, m) > 0.88 for m in b)]
    pc = lambda t: {m.group(0).replace(" ", "") for s in _sent_with(t, r"shareholder|owned|shareholding|holds|ownership") for m in re.finditer(r"\b\d{1,3}(?:\.\d+)?\s?%", s)}
    sc = pc(sp["cur_text"]) ^ pc(sp["prior_text"])
    disc = re.search(r"resign|appointed|joined|ceased|restructur|change in (?:role|ownership|shareholding|remuneration)|new (?:pay|remuneration) structure|no change|unchanged|there (?:has|have) been no", sp["cur_text"], re.I)
    if (left or new or sc) and not disc:
        return [_ex("TP-59", "Facts changed since the prior report but the update does not discuss it", "Medium",
                    f"Persons only in the prior report: {sorted(left)[:4]}; only in the update: {sorted(new)[:4]}; shareholding figures that differ: {sorted(sc)[:4]}", "Company profile", "changes reflected / 'no change' stated", "silent")]
    return [_ex("TP-59", "Change in facts", "Info", f"Left: {sorted(left)[:4] or 'none'}; new: {sorted(new)[:4] or 'none'}; shareholding differences: {sorted(sc) or 'none'}; update " + ("discusses changes" if disc else "states nothing"), "Company profile")]


DBS = r"S&P Capital IQ|Capital IQ|Orbis|Bureau van Dijk|TP Catalyst|Bloomberg|Refinitiv|Mergent|Osiris|Compustat"


@mode("hybrid")
def same_criteria(c):
    sp = _split(c)
    def attrs(t):
        return {"database": {m.group(0).lower() for m in re.finditer(DBS, t, re.I)},
                "method": {k for k, rx in (("TNMM", r"\bTNMM\b|transactional net margin"), ("CUP", r"\bCUP\b|comparable uncontrolled")) if re.search(rx, t, re.I)},
                "PLI": {k for k, rx in (("OP/OC", r"\bOP\s*/\s*OC\b"), ("OP/OR", r"\bOP\s*/\s*OR\b"), ("EC/OC", r"\bEC\s*/\s*OC\b")) if re.search(rx, t, re.I)},
                "industry codes": {m.group(0).upper() for m in re.finditer(r"\b(?:SIC|NAICS|NACE|GICS)[^\n]{0,30}?\d{3,}", t, re.I)}}
    a, b = attrs(sp["cur_text"]), attrs(sp["prior_text"])
    diff = {k: (sorted(b[k]), sorted(a[k])) for k in a if a[k] != b[k] and (a[k] or b[k])}
    explained = re.search(r"change in (?:the )?(?:method|database|search)|search (?:criteria )?(?:was|were) (?:changed|revised|updated)|revised the search", sp["cur_text"], re.I)
    if diff and not explained:
        return [_ex("TP-61", "Search criteria / method differ from the prior report without explanation", "Medium", "; ".join(f"{k}: prior {p} -> now {n}" for k, (p, n) in diff.items()), "Methodology", "same criteria", "changed")]
    return [_ex("TP-61", "Criteria compared with the prior report", "Info", "; ".join(f"{k}: {sorted(a[k]) or 'n/a'}" for k in a) + (" (changes are explained)" if diff else " - identical"), "Methodology")]


@mode("hybrid")
def rolled_forward(c):
    sp = _split(c)
    out = []
    ext = re.search(r"(?:extract|retriev|accessed|downloaded|as (?:of|at|on)|search date|data (?:was|were) (?:obtained|taken))[^.\n]{0,60}(?:\d{1,2}\s+\w+\s+20\d\d|\w+\s+20\d\d)", sp["cur_text"], re.I)
    if not ext:
        out.append(_ex("TP-62", "Database extraction date is not stated in the update", "Low", "State the date the comparables' data was extracted", "Methodology", "extraction date", "absent"))
    if getattr(c, "wb_path", None) and not str(c.wb_path).lower().endswith(".xls"):
        yrs = set()
        for ws in _wb_rows(c.wb_path).worksheets:
            for r in list(ws.iter_rows(values_only=True))[:12]:
                for x in r:
                    if isinstance(x, (str, int)) and re.fullmatch(r"(?:FY\s?)?(20\d\d)", str(x).strip(), re.I):
                        yrs.add(int(re.search(r"20\d\d", str(x)).group(0)))
        if yrs and max(yrs) < c.cy:
            out.append(_ex("TP-62", "Latest financial year has not been rolled forward in the workbook", "Medium", f"Years in the workbook: {sorted(yrs)}; the update is for {c.cy}. Grey area: some comparables may not yet have published {c.cy} accounts - state that if so.", "Workbook", str(c.cy), str(max(yrs))))
    elif not out:
        raise NotRun("Benchmarking workbook (.xlsx) not supplied")
    return out


# ====================================================================== 1.13 regulatory
@mode("hybrid")
def components(c):
    t = _norm(c)
    need = {"entity and industry analysis": r"industry (analysis|overview)|economic (environment|overview)|company (profile|overview)|entity (profile|overview)|background of the (company|entity)",
            "description of the controlled transaction": r"controlled transaction|payment(?:s)? to (?:the )?connected person|remuneration paid|nature of (?:the )?transaction",
            "method selection": r"method selection|selection of (?:the )?(?:transfer pricing )?method|most appropriate method|selected method",
            "comparability analysis": r"comparability analysis|search (?:strategy|process)|screening|comparable (?:set|companies)",
            "conclusion": r"\bconclusion\b|arm'?s length (?:range|conclusion)"}
    miss = [k for k, rx in need.items() if not re.search(rx, t, re.I)]
    if miss:
        return [_ex("TP-68", "Expected report component not found: " + ", ".join(miss), "Medium", "OECD / FTA TP Guide components: entity and industry analysis, controlled transaction, method selection, comparability analysis, conclusion", "Report", "all five", f"missing {len(miss)}")]
    return [_ex("TP-68", "All expected components found", "Info", "entity/industry, controlled transaction, method selection, comparability, conclusion are all present (adequacy still for the reviewer)", "Report")]


@mode("hybrid")
def connected_persons(c):
    rep = _persons(c.doc.all_text)
    out = []
    birf = getattr(c, "birf", None)
    if birf:
        bt = _birf_table(birf)
        bn = set(bt[1]) if bt and bt[1] else ({x for x in _persons(birf.all_text)} | {r[0].strip() for tb in birf.tables for r in tb.rows[1:] if r and re.fullmatch(r"[A-Z][A-Za-z.\- ]{4,50}", (r[0] or "").strip())})
        miss = [n for n in bn if not any(_ratio(n, m) > 0.85 or n.lower() in c.doc.all_text.lower() for m in rep) and n.lower() not in c.doc.all_text.lower()]
        extra = [n for n in rep if not any(_ratio(n, m) > 0.85 or n.lower() in birf.all_text.lower() for m in bn)]
        if miss:
            out.append(_ex("TP-69", "Person in the BIRF is not in the report", "High", f"{sorted(miss)[:5]}", "Connected persons", "BIRF persons in the report", str(sorted(miss)[:3])))
        if extra:
            out.append(_ex("TP-69", "Person in the report is not in the BIRF", "High", f"{sorted(extra)[:5]}", "Connected persons", "agrees to BIRF", str(sorted(extra)[:3])))
    fs = _need_fs(c) if c.fs else None
    if fs:
        if not re.search(r"related part(?:y|ies)|key management", fs, re.I):
            out.append(_ex("TP-69", "Audited FS has no related-party / key management note", "Medium", "The connected-person payments cannot be agreed to a note", "FS", "related party note", "absent"))
        elif not re.search(r"related part(?:y|ies)|connected person", _norm(c), re.I):
            out.append(_ex("TP-69", "Report does not identify the connected person / related party", "Medium", "The FS has a related-party note but the report does not refer to the related party", "Report", "identified", "absent"))
    if not birf and not fs:
        raise NotRun("Neither the BIRF nor the audited FS was supplied")
    return out or [_ex("TP-69", "Connected persons agree", "Info", f"Persons named in the report: {sorted(rep)[:5]}", "Connected persons")]


@mode("hybrid")
def law_refs(c):
    cfg = yaml.safe_load((ROOT / "rules" / "law_refs.yaml").read_text(encoding="utf-8"))
    t = _norm(c)
    out, cited = [], []
    for o in cfg["outdated"]:
        for m in re.finditer(o["rx"], t, re.I):
            out.append(_ex("TP-70", "Outdated / doubtful legal reference", "Medium", f"'{m.group(0)[:80]}' - {o['note']}", "Report", "current instrument", m.group(0)[:50]))
    for r in cfg["current"]:
        if re.search(r["rx"], t, re.I):
            cited.append(r["note"])
    inst = {re.sub(r"\s+", " ", m.group(0)) for m in re.finditer(r"(?:Cabinet\s+(?:Decision|Resolution)|Ministerial\s+Decision|Federal\s+Decree[- ]Law|Federal\s+Law)\s+(?:No\.?\s*)?\(?\d+\)?\s+of\s+20\d\d", t, re.I)}
    known = [r["rx"] for r in cfg["current"] + cfg["outdated"]]
    unknown = [i for i in inst if not any(re.search(k, i, re.I) for k in known)]
    if unknown:
        out.append(_ex("TP-70", "Legal reference not in the firm's reference list", "Low", f"{sorted(unknown)[:5]} - {cfg['unknown_instrument_note']}", "Report", "verified citation", ", ".join(sorted(unknown)[:2])))
    allowed = set(cfg["thresholds_aed"]["allowed"])
    for s in _sentences(t):
        if re.search(r"disclosure|threshold|master file|local file|documentation", s, re.I):
            for m in re.finditer(r"AED\s*([\d,.]+)\s*(million|billion|m|bn)?", s, re.I):
                try:
                    v = float(m.group(1).replace(",", "")) * (1e9 if (m.group(2) or "").lower() in ("billion", "bn") else 1e6 if (m.group(2) or "").lower() in ("million", "m") else 1)
                except ValueError:
                    continue
                if v >= 100000 and v not in allowed:
                    out.append(_ex("TP-70", "Threshold quoted does not match current FTA thresholds", "Medium", f"'{s[:160]}' - AED {v:,.0f} is not a current TP threshold (AED 40m / 4m / 500k / 200m / 3.15bn)", "Report", "current threshold", f"AED {v:,.0f}"))
    return out or [_ex("TP-70", "Legal references checked against the firm's list", "Info", f"Recognised: {sorted(set(cited))[:5] or 'none cited'}; list verified {cfg['as_of']}", "Report")]


NEW = {"toc_complete": toc_complete, "toc_text": toc_text, "toc_annexures": toc_annexures, "toc_format": toc_format, "profile_vs_fs": profile_vs_fs, "functional": functional,
       "rem_split_birf": rem_split_birf, "subheading_format": subheading_format, "pli_rationale": pli_rationale, "rejected_reasons": rejected_reasons, "data_periods": data_periods,
       "method_rejection": method_rejection, "secondary_conclusion": secondary_conclusion, "chart_scale": chart_scale, "chart_data": chart_data, "chart_message": chart_message,
       "naming_consistency": naming_consistency, "comps_retained": comps_retained, "dropped_reason": dropped_reason, "added_reason": added_reason, "range_movement": range_movement,
       "yoy": yoy, "validity": validity, "change_in_facts": change_in_facts, "same_criteria": same_criteria, "rolled_forward": rolled_forward, "components": components,
       "connected_persons": connected_persons, "law_refs": law_refs}
