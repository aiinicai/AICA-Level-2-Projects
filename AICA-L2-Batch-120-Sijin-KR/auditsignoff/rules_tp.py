"""Module C - Transfer pricing report review: report (any format) vs benchmarking workbook vs fact sheet / FS / CT working."""
from __future__ import annotations
import re
import statistics
from pathlib import Path

from .loaders import find_row, load_document, table_has
from .models import Finding, Result
from .rules_fs import NotRun, fuzzy_hits, _is_tnr

NUM = re.compile(r"\(?-?\d[\d,]*\.?\d*\)?\s*%?")


def _num(s):
    m = re.search(r"-?\d[\d,]*\.?\d*", str(s).replace("(", "-").replace(")", ""))
    return float(m.group(0).replace(",", "")) if m else None


def _ex(cid, title, sev, detail, loc, exp="", found=""):
    return Finding(cid, title, sev, detail, loc, str(exp), str(found))


# ================================================================== workbook
def quartiles(vals, method="INC"):
    v = sorted(vals)
    n = len(v)

    def q(p):
        if method == "EXC":
            pos = p * (n + 1)
            if pos < 1 or pos > n:
                return None
        else:
            pos = p * (n - 1) + 1
        lo = int(pos)
        frac = pos - lo
        if lo >= n:
            return v[-1]
        return v[lo - 1] + frac * (v[lo] - v[lo - 1])
    return {"min": v[0], "q1": q(0.25), "median": statistics.median(v), "q3": q(0.75), "max": v[-1]}


class TPWorkbook:
    def __init__(self, path, params):
        import openpyxl
        from .legacy import ensure_modern
        self.p = params["tp"]
        wb = openpyxl.load_workbook(str(ensure_modern(path)), data_only=True)
        self.comps, self.sheet, self.pli_header, self.labels = [], None, None, {}
        self.mr_persons = []                         # (label, AED amount, location) per person - absolute-remuneration benchmarks
        self.all_numbers = set()
        self.fraction = False
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            self.all_numbers.update(float(v) for r in rows for v in r if isinstance(v, (int, float)) and not isinstance(v, bool))
            self._scan_labels(ws.title, rows)
            if self.comps:
                continue
            for hi, row in enumerate(rows[:40]):
                low = [str(c).strip().lower() if c is not None else "" for c in row]
                name_i = next((i for i, h in enumerate(low) if re.search(r"company|comparable|entity|name", h)), None)
                pli_i = next((i for i, h in enumerate(low) if h and any(k == h or (len(k) > 3 and k in h) for k in self.p["pli_columns"]) and i != name_i), None)
                if name_i is None or pli_i is None:
                    continue
                data = []
                for r in rows[hi + 1:]:
                    if len(r) > max(name_i, pli_i) and r[name_i] and isinstance(r[pli_i], (int, float)) and not isinstance(r[pli_i], bool):
                        data.append((str(r[name_i]).strip(), float(r[pli_i])))
                    elif data and not r[name_i]:
                        break
                if len(data) >= 3:
                    self.comps, self.sheet, self.pli_header = data, ws.title, row[pli_i]
                    break
        if self.comps and max(abs(v) for _, v in self.comps) <= 1.5:      # stored as fractions (0.0543 = 5.43%)
            self.fraction = True
            self.comps = [(n, v * 100) for n, v in self.comps]

    def _scan_labels(self, sheet, rows):
        want = {"tested_pli": r"tested party.*(pli|margin|mark.?up|ratio)|^pli of the tested|tested party pli",
                "op": r"^(tested party )?operating profit|^ebit$|^net operating profit",
                "oc": r"^(tested party )?(total )?operating (cost|expense)s?|^total costs?",
                "revenue": r"^(tested party )?(net )?(revenue|sales|turnover)",
                "adjustment": r"adjustment",
                "mr_total": r"^total (managerial )?(remuneration|compensation)"}
        mr_person = re.compile(r"(managerial|key management|director'?s?)\s*(remuneration|compensation|fees|salary)|remuneration paid|\bpaid\b.*remuneration", re.I)
        for ri, row in enumerate(rows):
            lab = next((c for c in row if isinstance(c, str) and c.strip()), None)
            if lab and mr_person.search(lab) and not re.search(r"total|range|within|quartile|median|benchmark|lowest|highest", lab, re.I):
                for nxt in row[1:4]:
                    if isinstance(nxt, (int, float)) and not isinstance(nxt, bool) and nxt >= 1000:
                        self.mr_persons.append((lab.strip(), float(nxt), f"{sheet}!{ri + 1}")); break
            for ci, cell in enumerate(row):
                if isinstance(cell, str):
                    for k, rx in want.items():
                        if k not in self.labels and re.search(rx, cell.strip(), re.I):
                            for nxt in row[ci + 1:ci + 4]:
                                if isinstance(nxt, (int, float)) and not isinstance(nxt, bool):
                                    self.labels[k] = (float(nxt), f"{sheet}!{ri + 1}")
                                    break

    @property
    def values(self):
        return [v for _, v in self.comps]

    def stats(self, method=None):
        if len(self.comps) < 4:
            return None
        return quartiles(self.values, method or self.p["quartile_method"])


# ================================================================== docx extras
def docx_extras(path):
    import docx
    from docx.oxml.ns import qn
    d = docx.Document(str(path))
    secs = []
    for i, s in enumerate(d.sections):
        def part_info(part):
            el = part._element
            xml = el.xml
            has_field = bool(re.search(r'instrText[^>]*>\s*PAGE|w:fldSimple[^>]*w:instr="\s*PAGE', xml, re.I))
            texts = " ".join(p.text for p in part.paragraphs if p.text.strip())
            aligns = [p.alignment for p in part.paragraphs if p.text.strip() or "PAGE" in p._p.xml]
            return {"field": has_field, "text": texts.strip(), "right": any(a is not None and int(a) == 2 for a in aligns) or "w:tab" in xml}
        b = s._sectPr.find(qn("w:pgBorders"))
        sz = None
        if b is not None:
            edges = [e.get(qn("w:sz")) for e in b if e.get(qn("w:sz"))]
            sz = sorted(set(int(x) for x in edges))
        secs.append({"i": i + 1, "header": part_info(s.header), "footer": part_info(s.footer), "border": sz})
    return secs


# ================================================================== context
class TPCtx:
    def __init__(self, doc, wb, eng, params, fs_doc=None, ct_adj=None, facts=None, path=None):
        self.doc, self.wb, self.eng, self.P, self.p = doc, wb, eng, params, params["tp"]
        self.fs, self.ct_adj, self.facts, self.path = fs_doc, ct_adj, facts or {}, path
        self.cy = int(eng["fy"])
        self.name = eng["client"]["name"]
        self._extras = None

    def extras(self):
        if self.doc.kind != "docx":
            raise NotRun("Needs the Word (DOCX) version of the report")
        if self._extras is None:
            self._extras = docx_extras(self.path)
        return self._extras

    def cover_text(self):
        if self.doc.kind == "docx":
            lines = []
            for p in self.doc.paragraphs:
                if p.where != "body" or not p.text.strip():
                    continue
                # the cover ends where the contents page or the first heading begins (a Word file has no page markers here)
                if lines and (re.fullmatch(r"\s*(table of )?contents?\s*", p.text, re.I) or (p.style or "").lower().startswith("heading")):
                    break
                lines.append(p.text.strip())
            return "\n".join(lines[:45])
        return "\n".join(self.doc.pages[0].splitlines()[:45]) if self.doc.pages else ""

    def full_text(self):
        return re.sub(r"[ \t]+", " ", self.doc.all_text)


# ------------------------------------------------------------------ cover / entity
def _need_cover(c):
    if c.doc.kind != "docx" and len(re.sub(r"\s+", "", c.cover_text())) < 15:
        raise NotRun("Cover page is a picture (no readable text) - supply the Word file or review the cover visually")


def tp01_name(c: TPCtx):
    _need_cover(c)
    cov, target, out = c.cover_text(), c.name, []
    hits = fuzzy_hits(cov, target)
    if not hits:
        return [_ex("TP-01", "Company name from the trade licence not found on the cover page", "High", f"'{target}' not on the cover", "Cover", target, "-")]
    for cand, _, _ in hits:
        if cand != target:
            out.append(_ex("TP-01", "Company name on the cover differs from the trade licence", "High" if cand.lower() != target.lower() else "Low",
                           f"'{cand}' vs '{target}'", "Cover", target, cand))
    seen = {h[0] for h in hits}
    for cand, r, _ in fuzzy_hits(c.full_text(), target):
        if cand != target and cand.lower() != target.lower() and cand not in seen:
            seen.add(cand)
            out.append(_ex("TP-01", "Company name spelled differently elsewhere in the report", "Medium", f"'{cand}' vs '{target}'", "Report body", target, cand))
    return out[:6]


def tp02_title(c: TPCtx):
    _need_cover(c)
    cov = c.cover_text().lower()
    if not any(t.lower() in cov for t in c.p["titles"]):
        return [_ex("TP-02", "Cover title is not one of the approved report titles", "Medium", "Expected one of: " + "; ".join(c.p["titles"]), "Cover", "; ".join(c.p["titles"][:2]), "-")]
    return []


def tp03_year(c: TPCtx):
    _need_cover(c)
    cov = c.cover_text()
    years = {int(y) for y in re.findall(r"\b(20\d{2})\b", cov)}
    if not years:
        return [_ex("TP-03", "No financial year found on the cover page", "High", "Cover shows no year", "Cover", str(c.cy), "-")]
    if c.cy not in years:
        return [_ex("TP-03", "Financial year on the cover does not agree to the engagement", "High", f"Cover years {sorted(years)}; engagement FY {c.cy}", "Cover", str(c.cy), str(sorted(years)))]
    stray = years - {c.cy, c.cy - 1} - set(int(x) for x in c.eng.get("allowed_years") or [])
    return [_ex("TP-03", "Unexpected year on the cover page", "Medium", f"{sorted(stray)}", "Cover", str(c.cy), str(sorted(stray)))] if stray else []


def tp55_entity(c: TPCtx):
    t, out = c.full_text(), []
    cl = c.eng["client"]
    auth = str(cl.get("authority", "")).strip()
    if auth and not re.search(rf"\b{re.escape(auth)}\b", t, re.I):
        out.append(_ex("TP-55", "Licensing authority per the fact sheet is not mentioned in the report", "Medium", auth, "Report", auth, "-"))
    miss = [s for s in cl.get("shareholders", []) if not fuzzy_hits(t, s, 0.9)]
    if miss:
        out.append(_ex("TP-55", "Shareholder(s) per MOA not found in the report's ownership description", "High", "; ".join(miss), "Report", "; ".join(miss), "-"))
    return out


# ------------------------------------------------------------------ formatting (DOCX)
def _tp_font_size(c: TPCtx, which):
    P = c.p["heading_sizes"]
    out = {}
    for p in c.doc.paragraphs:
        for r in p.runs:
            if which == "font":
                if r.font and not _is_tnr(r.font):
                    out.setdefault(r.font, [0, p.loc]); out[r.font][0] += len(r.text)
            else:
                if r.size is None:
                    continue
                st = (p.style or "").lower()
                want = P["main"] if st.startswith(("heading 1", "title", "toc heading")) else P["sub"] if st.startswith("heading") else \
                    P["table"] if p.where == "table" else P["header_footer"] if p.where in ("header", "footer") else P["body"]
                if abs(r.size - want) > 0.25:
                    k = (r.size, want, p.where if p.where != "body" else st or "body")
                    out.setdefault(k, [0, p.loc]); out[k][0] += len(r.text)
    return out


def tp06_font(c: TPCtx):
    if c.doc.kind != "docx":
        raise NotRun("Needs the Word (DOCX) version of the report")
    return [_ex("TP-06", f"Font '{f}' used instead of Times New Roman", "Low", f"{n} characters", loc, "Times New Roman", f)
            for f, (n, loc) in sorted(_tp_font_size(c, "font").items(), key=lambda x: -x[1][0])[:5]]


def tp07_sizes(c: TPCtx):
    if c.doc.kind != "docx":
        raise NotRun("Needs the Word (DOCX) version of the report")
    return [_ex("TP-07", f"{k[2]} text is {k[0]:g} pt, standard is {k[1]:g} pt", "Low", f"{n} characters", loc, f"{k[1]:g} pt", f"{k[0]:g} pt")
            for k, (n, loc) in sorted(_tp_font_size(c, "size").items(), key=lambda x: -x[1][0])[:6]]


def tp11_header(c: TPCtx):
    out = []
    for s in c.extras():
        h = s["header"]["text"].lower()
        if not any(t.lower() in h for t in c.p["titles"]):
            out.append(_ex("TP-11", "Header does not show the prescribed title", "Low", f"Section {s['i']} header: '{s['header']['text'][:60]}'", f"Section {s['i']} header", "; ".join(c.p["titles"][:2]), s["header"]["text"][:40] or "(blank)"))
    return out


def tp12_pageno(c: TPCtx):
    out = []
    for s in c.extras():
        hd = s["header"]
        if not hd["field"]:
            typed = re.search(r"(?:page\s*)?\b\d{1,3}\b\s*$", hd["text"])
            out.append(_ex("TP-12", "Page number in the header is not a dynamic PAGE field" if typed else "No page number field in the header", "Low",
                           f"Section {s['i']}: " + ("typed number" if typed else "none found"), f"Section {s['i']} header", "PAGE field, right", "typed" if typed else "none"))
        elif not hd["right"]:
            out.append(_ex("TP-12", "Page number is not positioned at the right of the header", "Low", f"Section {s['i']}", f"Section {s['i']} header", "right", "left/centre"))
    return out


def tp14_footer(c: TPCtx):
    out = []
    for s in c.extras():
        f = s["footer"]
        if c.name.lower() not in f["text"].lower():
            out.append(_ex("TP-14", "Footer does not show the company name as per the trade licence", "Medium", f"Section {s['i']} footer: '{f['text'][:60]}'", f"Section {s['i']} footer", c.name, f["text"][:40] or "(blank)"))
    return out


def tp15_consistency(c: TPCtx):
    ex = c.extras()
    out = []
    for key in ("header", "footer"):
        texts = {re.sub(r"\d+", "#", s[key]["text"]) for s in ex}
        if len(texts) > 1:
            out.append(_ex("TP-15", f"{key.title()} text differs between sections", "Low", " | ".join(sorted(texts))[:200], f"{key}s", "identical", f"{len(texts)} variants"))
    return out


def tp16_border(c: TPCtx):
    want = c.p["page_border_eighths_pt"]
    out = []
    for s in c.extras():
        if not s["border"]:
            out.append(_ex("TP-16", "No page border in this section", "Low", f"Section {s['i']}", f"Section {s['i']}", "1.5 pt border", "none"))
        elif s["border"] != [want]:
            out.append(_ex("TP-16", "Page border thickness differs from 1.5 pt", "Low", f"Section {s['i']}: {[x / 8 for x in s['border']]} pt", f"Section {s['i']}", "1.5 pt", str([x / 8 for x in s["border"]])))
    return out


# ------------------------------------------------------------------ annexures / index
def tp21_annexures(c: TPCtx):
    t = c.doc.text
    heads = [(m.group(1), m.start()) for m in re.finditer(r"^\s*Annexure\s+([A-Z]|\d{1,2})\s*(?:[:\-–]\s*[^\n]{0,80})?$", t, re.M | re.I)]
    refs = {m.group(1).upper() for m in re.finditer(r"\bAnnexure\s+([A-Z]|\d{1,2})\b", c.full_text(), re.I)}
    out = []
    ids = list(dict.fromkeys(h[0].upper() for h in heads))
    if refs and not ids:
        return [_ex("TP-20", "Report refers to annexures but no annexure heading/page was found", "Medium", f"Referenced: {sorted(refs)}", "Report", "Annexure headings", "none")]
    missing = sorted(refs - set(ids))
    if missing:
        out.append(_ex("TP-20", "Annexure referred to in the report is not included", "Medium", f"'Annexure {missing[0]}' is cited but there is no annexure page for: {missing}", "Report", ", ".join(missing), "absent"))
    if ids:
        seq = [i for i in ids]
        exp = [chr(65 + k) for k in range(len(seq))] if all(s.isalpha() for s in seq) else [str(k + 1) for k in range(len(seq))]
        if seq != exp:
            out.append(_ex("TP-21", "Annexures are not numbered sequentially", "Medium", f"Found order {seq}; expected {exp}", "Annexure headings", str(exp), str(seq)))
        unused = sorted(set(ids) - refs)
        if unused:
            out.append(_ex("TP-23", "Annexure included but never referred to in the report", "Low", f"{unused}", "Annexures", "referenced", "unreferenced"))
    return out


def _printed_page_map(c):
    """physical page -> printed page number, read from the 'Title  N' header line or a lone number in the first/last lines."""
    m = {}
    for i, p in enumerate(c.doc.pages):
        lines = [l.strip() for l in p.splitlines() if l.strip()]
        for l in lines[:2] + lines[-2:]:
            mm = re.search(r"(?:Analysis|Report|Update)\s+(\d{1,3})$", l) or re.fullmatch(r"(\d{1,3})", l)
            if mm:
                m[i + 1] = int(mm.group(1))
                break
    return m


def tp17_index(c: TPCtx):
    pages = c.doc.pages if c.doc.kind != "docx" else None
    if pages:
        ti = next((i for i, p in enumerate(pages[:6]) if re.search(r"^\s*(table of )?contents?\s*$", p, re.I | re.M)), None)
        if ti is None:
            raise NotRun("No index/contents page found")
        block, body_pages = pages[ti], pages[ti + 1:]
        body = "\n".join(body_pages)
    else:
        t = c.doc.text
        m = re.search(r"^\s*(table of )?contents?\s*$|^\s*index\s*$", t, re.I | re.M)
        if not m:
            raise NotRun("No index/contents page found")
        block = t[m.end(): m.end() + 6000]
        last = [mm.end() for mm in re.finditer(r"^\s*.{4,90}?[.\s_·…]{2,}\s*\d{1,3}(?:\s*[-–]\s*\d{1,3})?\s*$", block, re.M)]
        body = t[m.end() + (last[-1] if last else 6000):] or t        # the body starts after the last index line (a Word index is short)
    entries = [(re.sub(r"[.\s_·…]+$", "", mm.group(1)).strip(), int(mm.group(2)), mm.group(3)) for mm in
               re.finditer(r"^\s*(.{4,90}?)[.\s_·…]{2,}\s*(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?\s*$", block, re.M)]
    if not entries:
        raise NotRun("Index entries with page numbers not recognised")
    out = []
    pmap = _printed_page_map(c) if pages else {}
    inv = {}
    for phys, pr in pmap.items():
        inv.setdefault(pr, phys)
    for title, pg, pg2 in entries:
        if not fuzzy_hits(body, title, 0.88) and title.lower() not in body.lower():
            out.append(_ex("TP-17", "Index entry has no matching heading in the report", "Medium", f"'{title}' (p.{pg})", "Index", title, "not found"))
            continue
        if pages and pmap:
            found = [pmap.get(i + 1) for i, p in enumerate(pages) if i + 1 > 2 and re.search(r"^\s*" + re.escape(title) + r"(\s*\(continued\))?\s*$", p, re.I | re.M) and pmap.get(i + 1)]
            if found and pg not in found:
                out.append(_ex("TP-17", "Index page number does not match the page where the heading first appears", "Medium", f"'{title}': index p.{pg}, heading on p.{found[0]}", "Index", f"p.{found[0]}", f"p.{pg}"))
    if pages and not pmap:
        out.append(_ex("TP-17", "Printed page numbers could not be read, index page numbers not verified", "Low", "no page-number header/footer text", "Report"))
    return out[:12]


# ------------------------------------------------------------------ benchmarking numbers
STAT_RX = {"min": r"^(minimum|min\.?|lowest)\b", "q1": r"(lower quartile|1st quartile|first quartile|\bq1\b|25th percentile)",
           "median": r"\bmedian\b", "q3": r"(upper quartile|3rd quartile|third quartile|\bq3\b|75th percentile)", "max": r"^(maximum|max\.?|highest)\b"}


def report_stats(c: TPCtx):
    """Every (stat, value, location) the report states - tables first, then 'median of 5.4%' style sentences."""
    found = []
    for t in c.doc.tables:
        for ri, r in enumerate(t.rows):
            lab = next((x for x in r if re.search(r"[A-Za-z]", x)), "")
            vals = [_num(x) for x in r if re.search(r"\d", x) and not re.search(r"[A-Za-z]", x)]
            vals = [v for v in vals if v is not None]
            for k, rx in STAT_RX.items():
                if lab and re.search(rx, lab.strip(), re.I) and vals:
                    found.append((k, vals[0], f"{t.loc}, row {ri + 1}"))
    txt = re.sub(r"\s+", " ", c.full_text())
    for m in re.finditer(r"(?:AED\s*)?(?P<v>\d{1,3}(?:,\d{3})+)\s*\((?P<p>25|75)(?:th)? percentile\)", txt, re.I):
        found.append(("q1" if m.group("p") == "25" else "q3", float(m.group("v").replace(",", "")), "narrative: '" + txt[max(0, m.start() - 15): m.end()][:60] + "'"))
    for m in re.finditer(r"median of (?:AED\s*)?(?P<v>\d{1,3}(?:,\d{3})+)", txt, re.I):
        found.append(("median", float(m.group("v").replace(",", "")), "narrative: '" + txt[max(0, m.start() - 5): m.end()][:60] + "'"))
    for k, rx in STAT_RX.items():
        for m in re.finditer(r"(?:" + rx.strip("^").replace("^", "") + r")(?:(?!quartile|median|percentile|minimum|maximum|lowest|highest|actual|tested|PLI)[^.%\d-]){0,40}?(?<![(\d])(?P<v>-?\d{1,3}(?:\.\d{1,2})?)\s*%(?!\s*\))", txt, re.I):
            found.append((k, float(m.group("v")), "narrative: '" + txt[max(0, m.start() - 20): m.end() + 5][:70] + "'"))
    return found


def _relabel(fs, cid):
    for f in fs:
        f.check_id = cid
    return fs


def tp46_stats(c: TPCtx):
    if not c.wb or not c.wb.comps:
        if len(_comp_rows(c)) >= 4:             # no workbook: recompute from the report's own comparables table
            return _relabel(tp64_table_recompute(c), "TP-46")
        raise NotRun("Upload the benchmarking workbook (Excel) - no comparables table found in the report to recompute from")
    st = c.wb.stats()
    if not st:
        raise NotRun("Fewer than 4 comparables in the workbook")
    tol, other = c.p["stat_tolerance_pp"], c.wb.stats("EXC" if c.p["quartile_method"] == "INC" else "INC")
    out, rep = [], report_stats(c)
    if not rep:
        raise NotRun("No range statistics (min/Q1/median/Q3/max) recognised in the report")
    seen = set()
    for k, v, loc in rep:
        if (k, round(v, 2)) in seen:
            continue
        seen.add((k, round(v, 2)))
        if abs(v - st[k]) > tol:
            alt = other and other.get(k) is not None and abs(v - other[k]) <= tol
            if alt:
                out.append(_ex("TP-46", f"{k.upper() if k in ('q1','q3') else k.title()} follows the other quartile method (grey area)", "Medium",
                               f"Report {v:.2f}% = QUARTILE.{'EXC' if c.p['quartile_method']=='INC' else 'INC'}; workbook method is {c.p['quartile_method']} ({st[k]:.2f}%). The firm must fix one method.", loc, f"{st[k]:.2f}%", f"{v:.2f}%"))
            else:
                fm = (lambda x: f"{x:,.0f}") if max(abs(v), abs(st[k])) > 1000 else (lambda x: f"{x:.2f}%")      # AED amounts (CUP / remuneration) or percentages (PLI)
                out.append(_ex("TP-46", f"{k.upper() if k in ('q1','q3') else k.title()} in the report does not agree to the workbook", "High",
                               f"Report {fm(v)} vs workbook {fm(st[k])} (n={len(c.wb.comps)}, {c.wb.sheet})", loc, fm(st[k]), fm(v)))
    return out[:12]


def tp49_consistency(c: TPCtx):
    rep = report_stats(c)
    if not rep:
        raise NotRun("No range statistics recognised in the report")
    by = {}
    for k, v, loc in rep:
        by.setdefault(k, []).append((v, loc))
    out = []
    for k, lst in by.items():
        vals = sorted({round(v, 2) for v, _ in lst})
        amt = max(vals) > 1000
        tol = 1.5 if amt else c.p["stat_tolerance_pp"]
        u = (lambda v: f"{v:,.0f}") if amt else (lambda v: f"{v:.2f}%")
        if len(vals) > 1 and max(vals) - min(vals) > tol:
            out.append(_ex("TP-49", f"{k.upper() if k in ('q1','q3') else k.title()} is stated differently within the report", "High",
                           "; ".join(f"{u(v)} at {loc}" for v, loc in lst[:4]), "Executive summary / analysis / conclusion", u(vals[0]), u(vals[-1])))
    return out


def tp45_count(c: TPCtx):
    if not c.wb or not c.wb.comps:
        rows = _comp_rows(c)
        if len(rows) < 4:
            raise NotRun("Upload the benchmarking workbook (or a report with a comparables table) to count comparables")
        stated = {int(a or b) for a, b in re.findall(r"(?:number of comparables|accepted companies|retained as suitable comparables)\D{0,40}?(\d{1,3})|(\d{1,3}) companies were retained", _norm(c), re.I)}
        if stated and len(rows) not in stated:
            return [_ex("TP-45", "Number of comparables stated differs from the report's own table", "High", f"Stated {sorted(stated)}; table rows {len(rows)} (no workbook supplied)", "Final comparables table", str(len(rows)), str(sorted(stated)))]
        return []
    txt = re.sub(r"\s+", " ", c.full_text())
    ms = []
    for m in re.finditer(r"\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?:final\s+|independent\s+|accepted\s+)?(?:comparable|comparables|companies|comparable companies|entities)\b", txt, re.I):
        # a table label sitting right after a number ("Total manual review rejections 36 | Accepted companies 27") is not a count of accepted comparables
        if re.search(r"(rejections?|rejected|screened|potential comparables|search results|search dump)\W*$", txt[max(0, m.start() - 30):m.start()], re.I) \
                and re.match(r"\s*accepted", txt[m.end(1):m.end(1) + 12], re.I):
            continue
        ms.append(m.group(1))
    words = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}
    nums = {int(x) if x.isdigit() else words[x.lower()] for x in ms}
    n = len(c.wb.comps)
    if not nums:
        raise NotRun("Number of comparables not stated in recognisable wording")
    snip = re.search(r"\b(?:\d{1,3}|" + "|".join(words) + r")\s+(?:comparable|companies|independent)[^.]{0,20}", txt, re.I)
    q = f" ('{snip.group(0).strip()[:70]}')" if snip else ""
    return [_ex("TP-45", "Number of comparables stated in the report differs from the workbook", "Medium",
                f"Report states {sorted(nums)}; workbook has {n} accepted comparables" + q, "Report", str(n), str(sorted(nums)))] if nums != {n} else []


def tp50_names(c: TPCtx):
    if not c.wb or not c.wb.comps:
        raise NotRun("Benchmarking workbook not supplied or not recognised")
    t, out = c.full_text(), []
    miss = [n for n, _ in c.wb.comps if not fuzzy_hits(t, re.sub(r"\s+", " ", n), 0.9)]
    if miss:
        out.append(_ex("TP-50", "Comparable(s) in the workbook are not named in the report", "High", "; ".join(miss[:8]), "Report vs workbook", f"{len(c.wb.comps)} names", f"{len(c.wb.comps) - len(miss)} found"))
    return out


def tp47_position(c: TPCtx):
    if not c.wb or not c.wb.comps:
        t = _norm(c)
        acts = sorted({float(x.replace(",", "")) for x in re.findall(r"(?:Mr|Ms|Mrs)\.?\s+(?:Mr\.?\s+)?[A-Z]+\s*[–-]\s*(\d{1,3}(?:,\d{3}){2,})", t)}, reverse=True)
        st = {}
        for k, v, _ in report_stats(c):
            if v > 1000:
                st.setdefault(k, v)
        if not acts or "q1" not in st or "q3" not in st:
            raise NotRun("Upload the benchmarking workbook (tested-party PLI) - actual figure/range not both found in the report")
        out = [a for a in acts if a < st["q1"] or a > st["q3"]]
        says = re.search(r"(outside|above|below|exceed\w*|not aligned|within) (?:with )?(?:the )?(?:arm'?s length|interquartile|observed)", t, re.I)
        if out and not says:
            return [_ex("TP-47", "Actual is outside the range but the report does not state the position", "High", f"Actuals {out} vs IQR {st['q1']:,.0f} - {st['q3']:,.0f}", "Conclusion")]
        return []
    st = c.wb.stats()
    if not st:
        raise NotRun("Fewer than 4 comparables")
    mrp = c.wb.mr_persons
    if mrp and not c.wb.labels.get("tested_pli"):            # absolute-remuneration (CUP) benchmark: each person against the interquartile range
        txt = re.sub(r"\s+", " ", c.full_text()).lower()
        says_in = bool(re.search(r"(lies|lie|falls?|is|are|remains?)\s+within the (arm'?s length|interquartile)|within the interquartile range|within the arm'?s length range", txt))
        says_out = bool(re.search(r"(outside|below|above|falls outside|exceeds?) the (arm'?s length|interquartile) range", txt))
        out = []
        for lab, amt, src in mrp:
            inside = st["q1"] <= amt <= st["q3"]
            if inside and says_out and not says_in:
                out.append(_ex("TP-47", "Report says remuneration is outside the range but the workbook amount is inside the IQR", "High", f"{lab}: {amt:,.0f} vs IQR {st['q1']:,.0f} - {st['q3']:,.0f}", src, "inside", "outside"))
            elif not inside and says_in and not says_out:
                out.append(_ex("TP-47", "Report says remuneration is within the range but the workbook amount is outside the IQR", "High", f"{lab}: {amt:,.0f} vs IQR {st['q1']:,.0f} - {st['q3']:,.0f}; adjustment to the median {st['median']:,.0f} may be required", src, "outside", "within"))
            elif not inside and not says_in and not says_out:
                out.append(_ex("TP-47", "Remuneration is outside the IQR but the report does not state the position", "Medium", f"{lab}: {amt:,.0f} vs IQR {st['q1']:,.0f} - {st['q3']:,.0f}", src))
        return out
    tested = c.wb.labels.get("tested_pli")
    if not tested:
        m = re.search(r"tested party[^.%]{0,80}?(?:PLI|margin|mark-?up|ratio)[^.%\d-]{0,40}?(-?\d{1,3}(?:\.\d{1,2})?)\s*%", re.sub(r"\s+", " ", c.full_text()), re.I)
        if not m:
            raise NotRun("Tested-party PLI not found in the workbook or report")
        pli, src = float(m.group(1)), "report"
    else:
        pli, src = tested[0] * (100 if c.wb.fraction else 1), tested[1]
    inside = st["q1"] <= pli <= st["q3"]
    txt = re.sub(r"\s+", " ", c.full_text()).lower()
    says_in = bool(re.search(r"within the (arm'?s length|interquartile) range|falls within", txt))
    says_out = bool(re.search(r"(outside|below|above|falls outside) the (arm'?s length|interquartile) range", txt))
    out = []
    if inside and says_out and not says_in:
        out.append(_ex("TP-47", "Report says the tested party is outside the range but its PLI is inside the IQR", "High", f"PLI {pli:.2f}% vs IQR {st['q1']:.2f}% - {st['q3']:.2f}%", src, "inside", "outside"))
    if not inside and says_in and not says_out:
        adj = (st["median"] - pli) / 100 * (c.wb.labels.get("oc", (0,))[0] if "oc" in c.wb.labels else 0)
        out.append(_ex("TP-47", "Report says the tested party is within the range but its PLI is outside the IQR", "High",
                       f"PLI {pli:.2f}% vs IQR {st['q1']:.2f}% - {st['q3']:.2f}%; adjustment to median {st['median']:.2f}% required" + (f" (about AED {adj:,.0f} on operating costs)" if adj else ""), src, "outside", "within"))
    if not inside and not says_out and not says_in:
        out.append(_ex("TP-47", "Tested-party PLI is outside the IQR but the report does not state the position/adjustment", "Medium", f"PLI {pli:.2f}%; IQR {st['q1']:.2f}% - {st['q3']:.2f}%", src))
    return out


def tp37_pli(c: TPCtx):
    if c.wb is None and len(_comp_rows(c)) >= 4:
        raise NotRun("Applies to margin-based PLIs; this report benchmarks absolute remuneration (CUP) - see TP-64/TP-68")
    L = c.wb.labels if c.wb else {}
    if not (c.wb and "op" in L and "oc" in L and "tested_pli" in L):
        raise NotRun("Workbook lacks tested-party operating profit, operating costs and PLI labels")
    op, oc, pli = L["op"][0], L["oc"][0], L["tested_pli"][0] * (100 if c.wb.fraction else 1)
    if oc == 0:
        return [_ex("TP-37", "Operating cost is zero: PLI cannot be computed", "High", "Zero denominator", L["oc"][1])]
    mine = op / oc * 100
    if abs(mine - pli) > 0.05:
        return [_ex("TP-37", "Tested-party PLI does not agree to operating profit / operating cost", "High", f"{op:,.0f} / {oc:,.0f} = {mine:.2f}% vs stated {pli:.2f}%", L["tested_pli"][1], f"{mine:.2f}%", f"{pli:.2f}%")]
    return []


def tp38_quality(c: TPCtx):
    if not c.wb or not c.wb.comps:
        rows = _comp_rows(c)
        if len(rows) < 4:
            raise NotRun("Upload the benchmarking workbook - no comparables table found in the report")
        out = []
        keys = [(r[0], r[4]) for r in rows]
        dup = {k for k in keys if keys.count(k) > 1}
        if dup:
            out.append(_ex("TP-38", "Duplicate entry in the comparables table", "High", "; ".join(f"{a}: {b:,.0f}" for a, b in sorted(dup)), "Final comparables table"))
        bad = [r for r in rows if r[4] <= 0 or r[3] <= 0]
        if bad:
            out.append(_ex("TP-38", "Zero or negative value in the comparables table", "High", "; ".join(r[0] for r in bad[:4]), "Final comparables table"))
        return out
    out, names = [], [n for n, _ in c.wb.comps]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        out.append(_ex("TP-38", "Duplicate comparable in the set", "High", "; ".join(sorted(dup)), c.wb.sheet))
    if len(names) < 5:
        out.append(_ex("TP-38", "Very few comparables: the interquartile range may not be reliable", "Medium", f"{len(names)} comparables", c.wb.sheet))
    neg = [n for n, v in c.wb.comps if v < 0]
    if neg:
        out.append(_ex("TP-38", "Loss-making comparable(s) retained: confirm the screening criteria allow this", "Medium", "; ".join(neg[:6]), c.wb.sheet))
    return out


def tp30_fs(c: TPCtx):
    if not c.fs:
        raise NotRun(getattr(c, "fs_note", "") or "Audited FS not supplied")
    L = c.wb.labels if c.wb else {}
    if "op" not in L:
        raise NotRun("Workbook has no tested-party operating profit label (not applicable to an absolute-remuneration benchmark - use the remuneration trace, TP-14)" if (c.wb and c.wb.mr_persons) else "Workbook has no tested-party operating profit label")
    op = L["op"][0]
    cands = []
    for rx in (r"operating profit|profit from operations|results from operating", r"profit (before tax|for the year|/\(loss\)|or loss)", r"^net profit|^net (loss|income)", r"gross profit"):
        r = find_row(c.fs.tables, rx)
        if r:
            cands += r[1]
    if not cands:
        raise NotRun("No profit line recognised in the FS")
    if not any(abs(abs(x) - abs(op)) <= 1 for x in cands):
        return [_ex("TP-30", "Operating profit in the TP workbook does not trace to any profit line in the audited FS", "High",
                    f"Workbook {op:,.0f}; FS profit lines {', '.join(f'{x:,.0f}' for x in cands[:6])}. If adjusted/aggregated, a reconciliation is required.", L["op"][1], f"{op:,.0f}", "no match")]
    return []


def tp57_ct(c: TPCtx):
    if c.ct_adj is None:
        raise NotRun("CT working sheet not supplied")
    txt = re.sub(r"\s+", " ", c.full_text())
    ms = re.findall(r"adjustment[^.%\d]{0,60}?(?:AED|USD)?\s*([\d,]{3,})", txt, re.I)
    rep = [float(m.replace(",", "")) for m in ms if m.replace(",", "").isdigit()]
    if not rep:
        raise NotRun("No adjustment amount stated in the report")
    if all(abs(r - c.ct_adj) > 1 for r in rep):
        return [_ex("TP-57", "TP adjustment in the report does not agree to the CT computation", "High", f"Report {rep[:3]} vs CT working {c.ct_adj:,.0f}", "Report / 07_TP_SCHEDULE", f"{c.ct_adj:,.0f}", str(rep[:3]))]
    return []


def tp58_thresholds(c: TPCtx):
    f, T = c.facts, c.P["ct"]
    if not f:
        raise NotRun("Related-party values / revenue not supplied")
    txt = c.full_text().lower()
    out = []
    agg, cat, conn = f.get("rp_aggregate"), f.get("rp_max_category"), f.get("connected_payments")
    if (agg and agg > T["tp_disclosure"]["aggregate"]) or (cat and cat > T["tp_disclosure"]["category"]):
        if "disclosure form" not in txt:
            out.append(_ex("TP-58", "Transfer Pricing Disclosure Form is triggered but not addressed in the report", "High",
                           f"Aggregate {agg or 0:,.0f} (limit {T['tp_disclosure']['aggregate']:,}) / largest category {cat or 0:,.0f} (limit {T['tp_disclosure']['category']:,})", "Report", "Disclosure Form referred", "absent"))
    rev, grp = f.get("revenue"), f.get("group_revenue")
    if (rev and rev >= T["tp_files"]["own_revenue"]) or (grp and grp >= T["tp_files"]["group_revenue"]):
        if not re.search(r"master file|local file", txt):
            out.append(_ex("TP-58", "Master File / Local File threshold met but not addressed", "High", f"Revenue {rev or 0:,.0f}; group {grp or 0:,.0f} (MD 97/2023)", "Report", "Master/Local File", "absent"))
    if conn and conn > T["tp_disclosure"]["connected_persons"] and "connected person" not in txt:
        out.append(_ex("TP-58", "Connected-person transactions above AED 500,000 but Art. 36 is not addressed", "Medium", f"{conn:,.0f}", "Report"))
    return out



# ================================================================== lessons from the ABC COMPANY sample report (KMP remuneration, PDF)
def _norm(c):
    return re.sub(r"\s+", " ", c.full_text())


def tp60_placeholders(c: TPCtx):
    t, out = _norm(c), []
    rx = [(r"\bX{3,}\b", "placeholder 'XXXX'"), (r"\b(TBC|TBD|TBA)\b", "TBC/TBD marker"), (r"\[\s*(?:insert[^\]]{0,25}|\.{2,}|tbc|tbd|name|date|amount|client|company)?\s*\]", "empty / square-bracket placeholder"),
          (r"\?{3,}", "'???' marker"), (r"lorem ipsum", "dummy text"),
          (r"\b(issued|dated|expiring|expires)\s+(on|in)?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\b(?!\s*,?\s*\d)", "date without a year")]
    for r, lab in rx:
        for m in list(re.finditer(r, t, re.I))[:2]:
            out.append(_ex("TP-60", f"Unfinished text in the report: {lab}", "High", t[max(0, m.start() - 40): m.end() + 25], "Report", "completed text", m.group(0)))
    return out


def tp61_doubled(c: TPCtx):
    t, out = _norm(c), []
    for m in re.finditer(r"\b((?:Mr|Ms|Mrs|Dr)\.?)\s+\1\s+([A-Z]\w+)", t):
        out.append(_ex("TP-61", "Doubled title before a name", "Low", m.group(0), "Report", f"{m.group(1)} {m.group(2)}", m.group(0)))
    seen = set()
    for m in re.finditer(r"\b([A-Za-z]{3,})\s+\1\b", t):
        w = m.group(1).lower()
        if w not in seen and w not in {"that", "had"}:
            seen.add(w)
            out.append(_ex("TP-61", "Repeated word", "Low", t[max(0, m.start() - 25): m.end() + 20], "Report", w, f"{w} {w}"))
    return out[:6]


def tp62_draft(c: TPCtx):
    n = 0
    if c.doc.kind == "docx":
        import zipfile
        try:
            z = zipfile.ZipFile(str(c.path))
            n = sum(len(re.findall(r">\s*DRAFT\s*<|string=\"DRAFT\"|\bDRAFT\b", z.read(x).decode("utf8", "ignore"))) for x in z.namelist() if x.startswith("word/header"))
        except Exception:
            n = 0
    else:
        n = sum(1 for p in c.doc.pages if re.search(r"\bD\s?R\s?A\s?F\s?T\b", p))
        if not n:                       # watermark drawn as a vector/picture: look for the yellow banner in the top-left corner
            try:
                import pdfplumber
                with pdfplumber.open(str(c.path)) as pdf:
                    for pg in pdf.pages:
                        im = pg.to_image(resolution=30).original.convert("RGB")
                        w, h = im.size
                        px = [im.getpixel((x, y)) for x in range(0, w // 4) for y in range(0, h // 5)]
                        if sum(1 for r, g, b in px if r > 220 and g > 220 and b < 120) > 25:
                            n += 1
            except Exception:
                n = 0
    if n:
        return [_ex("TP-62", "DRAFT watermark/legend present", "High", "Remove for the issued version; on this layout the watermark also overprints section headings (first characters hidden)", "All pages", "no watermark in the final", f"{n} occurrence(s)")]
    return []


def tp63_year_body(c: TPCtx):
    t = _norm(c)
    yrs = [int(y) for y in re.findall(r"(?:financial year(?: ending)?|FY|year ended|31 December|period)\D{0,12}(20\d{2})", t, re.I)]
    if not yrs:
        raise NotRun("No financial-year statements found in the body")
    from collections import Counter
    dom, n = Counter(yrs).most_common(1)[0]
    if dom != c.cy:
        return [_ex("TP-63", "Financial year analysed in the report differs from the engagement year", "High", f"Body refers mainly to FY {dom} ({n} mentions); fact sheet FY {c.cy}. Confirm the correct tax period and that comparables data are for that period.",
                    "Report body", str(c.cy), str(dom))]
    return []


def _comp_rows(c: TPCtx):
    """(person, company, role, revenue_mm, comp) from comparables tables in a PDF/DOCX report."""
    rows, seen = [], set()
    num = re.compile(r"^\d{1,3}(?:,\d{3})*(?:\.\d+)?$")
    for t in c.doc.tables:
        for r in t.rows:
            cells = [x.strip() for x in r if x and x.strip()]
            if len(cells) < 5:
                continue
            nums = [x for x in cells if num.match(x)]
            txt = [x for x in cells if not num.match(x)]
            if len(nums) < 2 or len(txt) < 3:
                continue
            rev, comp = nums[0], nums[-1]
            if "." not in rev or len(comp.replace(",", "")) < 4:
                continue
            key = (txt[0], comp)
            if key in seen:
                continue
            seen.add(key)
            rows.append((txt[0], txt[1], txt[2], float(rev.replace(",", "")), float(comp.replace(",", ""))))
    return rows


def tp64_table_recompute(c: TPCtx):
    rows = _comp_rows(c)
    if len(rows) < 4:
        raise NotRun("No comparables table with revenue and amount columns recognised in the report")
    vals = [r[4] for r in rows]
    meth = c.p["quartile_method"]
    st, other = quartiles(vals, meth), quartiles(vals, "EXC" if meth == "INC" else "INC")
    out = []
    for k, v, loc in report_stats(c):
        if v <= 1000:
            continue
        if abs(v - st[k]) > 1.5:
            alt = other.get(k) is not None and abs(v - other[k]) <= 1.5
            out.append(_ex("TP-64", f"{k.upper() if k in ('q1','q3') else k.title()} differs from the figure recomputed from the report's own comparables table"
                           + (" (other quartile method - grey area)" if alt else ""), "Medium" if alt else "High",
                           f"Report {v:,.0f} vs recomputed {st[k]:,.0f} (QUARTILE.{meth}, n={len(vals)})", loc, f"{st[k]:,.0f}", f"{v:,.0f}"))
    stated = re.findall(r"(?:number of comparables|accepted companies|retained as suitable comparables|companies were retained)\D{0,40}?(\d{1,3})|(\d{1,3}) companies were retained", _norm(c), re.I)
    nums = {int(a or b) for a, b in stated}
    if nums and len(rows) not in nums:
        out.append(_ex("TP-64", "Number of comparables stated does not agree to the rows in the table", "High", f"Stated {sorted(nums)}; table rows {len(rows)}", "Report", str(sorted(nums)), str(len(rows))))
    return out[:10]


def tp65_funnel(c: TPCtx):
    t = _norm(c)
    g = lambda rx: (lambda m: int(m.group(1)) if m else None)(re.search(rx, t, re.I))
    tot, rej, acc = g(r"Total potential comparables\D{0,5}(\d+)"), g(r"Total manual review rejections\D{0,5}(\d+)"), g(r"Accepted companies\D{0,5}(\d+)")
    if None in (tot, rej, acc):
        raise NotRun("Accept/reject funnel (total, rejected, accepted) not recognised")
    out = []
    if tot - rej != acc:
        out.append(_ex("TP-65", "Screening funnel does not add up", "High", f"{tot} - {rej} = {tot - rej}, report says {acc} accepted", "Section 3.2", str(tot - rej), str(acc)))
    reasons = [int(x) for x in re.findall(r"^\s*\d\.\s+(?:Non-comparable[^\n]*?)\s+(\d+)\s*$", c.doc.all_text, re.M | re.I)]
    if reasons and sum(reasons) != rej:
        out.append(_ex("TP-65", "Rejection reasons do not add up to total rejections", "High", f"{reasons} = {sum(reasons)} vs {rej}", "Section 3.2", str(rej), str(sum(reasons))))
    m = re.search(r"search results consisting of (\d+) comparables", t, re.I)
    if m and int(m.group(1)) != tot:
        out.append(_ex("TP-65", "Number of search results quoted differs from the total screened", "Medium", f"'{m.group(1)} comparables' (search results) vs {tot} screened. Possible typo (36 = number rejected).", "Step one", str(tot), m.group(1)))
    rows = _comp_rows(c)
    if rows and len(rows) != acc:
        out.append(_ex("TP-65", "Accepted comparables differ from the rows in the final table", "High", f"{acc} accepted vs {len(rows)} rows", "Final set", str(acc), str(len(rows))))
    comps = {r[1] for r in rows}
    if rows and len(comps) < acc * 0.8:
        out.append(_ex("TP-65", "Comparables are persons, not independent companies", "Medium", f"{len(rows)} executives from only {len(comps)} companies (several executives from one company are not independent observations); the report speaks of '{acc} companies'.", "Final set", f"{acc} companies", f"{len(comps)} companies"))
    return out


EXCH_REGION = {"MENA": {"SASE", "DFM", "ADX", "QSE", "BHSE", "MSM", "KWSE", "EGX", "TASE", "ASE", "BIST", "TADAWUL"}}


def tp66_geography(c: TPCtx):
    rows = _comp_rows(c)
    if not rows:
        raise NotRun("Comparables table not recognised")
    ex = [m.group(1) for r in rows for m in [re.search(r"\(([A-Z]+):", r[1])] if m]
    t = _norm(c)
    out = []
    claims = re.findall(r"(MENA|Middle East|Turkey)", t, re.I)
    in_mena = [e for e in ex if e in EXCH_REGION["MENA"]]
    if claims and ex and not in_mena:
        out.append(_ex("TP-66", "Report says MENA/Turkey comparables were used but none appear in the final set", "High",
                       f"All {len(ex)} listed companies trade on {sorted(set(ex))}. Report: UAE nil -> Middle East -> Europe; conclusion mentions 'MENA region, Turkey and selected European countries'.", "Sections 3.2 / 4", "region in the final set agrees to the narrative", "Europe only"))
    if re.search(r"Europe\s*\(Primary\)\s*OR\s*Middle East", t, re.I) and re.search(r"no comparable companies in UAE region so search extended to the Middle East", t, re.I):
        out.append(_ex("TP-66", "Step-3 search is 'Europe OR Middle East' but Middle East had already been searched separately", "Low", "Result of the Middle East step is not stated; cumulative filter hides which region the 27 came from", "Step one", "separate region results", "combined"))
    return out


def tp67_role_scale(c: TPCtx):
    rows = _comp_rows(c)
    if not rows:
        raise NotRun("Comparables table not recognised")
    out = []
    weak = [r for r in rows if re.search(r"\b(CFO|Finance Director|Corporate Secretary|Company Secretary|Head of|SVP|Deputy)\b", r[2], re.I) and not re.search(r"\b(CEO|Managing Director|MD|Chairman)\b", r[2], re.I)]
    if weak:
        out.append(_ex("TP-67", "Comparable roles differ from the tested roles (Managing Director)", "Medium",
                       f"{len(weak)} of {len(rows)} comparables are finance/secretary/division roles, e.g. " + "; ".join(f"'{r[0]}' - {r[2]}" for r in weak[:3]), "Final set", "MD / CEO equivalents", f"{len(weak)} non-equivalent roles"))
    prior = [r for r in rows if "prior board" in r[0].lower()]
    if prior:
        out.append(_ex("TP-67", "Former (Prior Board) executives included without a full-year/continuity check", "Low", "; ".join(r[0] for r in prior), "Final set", "full-year, current role", "prior board"))
    revs = [r[3] for r in rows]
    if min(revs) > 0 and max(revs) / min(revs) > 50:
        out.append(_ex("TP-67", "Comparable scale varies by more than 50x with no size screen or adjustment", "Medium",
                       f"Revenue AED {min(revs):,.1f}mm to {max(revs):,.1f}mm ({max(revs) / min(revs):,.0f}x). Listed multinationals vs a small trading LLC; the tested party's own revenue is not stated for comparison.", "Final set", "revenue band / size adjustment", f"{max(revs) / min(revs):,.0f}x spread"))
    nonmatch = re.search(r"Division F: Wholesale Trade", _norm(c)) and any(re.search(r"Agricultur|Electronics|Metals", r[2] + " " + r[1], re.I) for r in rows)
    if nonmatch:
        out.append(_ex("TP-67", "Business-description screen is a keyword ('building OR construction') but accepted set includes unrelated businesses", "Low", "e.g. agricultural equipment, electronics and metals groups", "Final set", "construction-materials traders", "mixed"))
    return out


def tp68_adjustment(c: TPCtx):
    t = _norm(c)
    acts = sorted({float(x.replace(",", "")) for x in re.findall(r"(?:Mr|Ms|Mrs)\.?\s+(?:Mr\.?\s+)?[A-Z]+\s*[–-]\s*(\d{1,3}(?:,\d{3}){2,})", t)}, reverse=True)
    st = {}
    for k, v, _ in report_stats(c):
        if v > 1000:
            st.setdefault(k, v)
    if not acts or "q3" not in st or "median" not in st:
        raise NotRun("Actual remuneration and the range were not both found")
    over = [a for a in acts if a > st["q3"]]
    if not over:
        return []
    out = []
    to_med, to_uq = sum(a - st["median"] for a in over), sum(a - st["q3"] for a in over)
    if not re.search(r"adjustment of AED|disallow\w* (?:of )?AED|AED [\d,]+ (?:is|be) (?:disallowed|added back)", t, re.I):
        out.append(_ex("TP-68", "Conclusion says the excess 'may be' disallowed but the adjustment is not quantified", "High",
                       f"{len(over)} payment(s) above the upper quartile {st['q3']:,.0f}. Excess to the median {to_med:,.0f}; to the upper quartile {to_uq:,.0f}. Grey area: which point (median / nearest range edge) the UAE TP Guide and the FTA expect; the report does not say.",
                       "Section 4", f"stated adjustment ({to_med:,.0f} to median)", "not quantified"))
    out.append(_ex("TP-68", "Conclusion is permissive ('may be considered ... disallowed') - not a determination", "Medium", "Report should state the adjustment, the legal basis (Arts. 34 and 36 CT Law) and that it flows to the CT computation (CT-03 / sheet 07).", "Section 4", "definitive conclusion", "'may be'"))
    out.append(_ex("TP-68", f"Actuals are {acts[0] / st['median']:.0f}x the median: check commercial rationale, contracts and board approvals before benchmarking", "Medium", f"Actuals {', '.join(f'{a:,.0f}' for a in acts)} vs median {st['median']:,.0f}. Also whether the amounts are dividends/profit drawings re-characterised as salary (Art. 28 / Art. 36).", "Section 4", "support file", "not referred"))
    return out


AUTH = {"Dubai Integrated Economic Zones Authority": "DIEZ", "Dubai Silicon Oasis Authority": "DSOA", "IFZA": "IFZA", "DMCC": "DMCC", "JAFZA": "JAFZA", "DAFZA": "DAFZA", "DIFC": "DIFC", "ADGM": "ADGM", "RAKEZ": "RAKEZ", "SHAMS": "SHAMS"}


def tp69_authority_people(c: TPCtx):
    t, out = _norm(c), []
    hits = {v for k, v in AUTH.items() if re.search(re.escape(k), t, re.I)}
    if len(hits) > 1:
        out.append(_ex("TP-69", "More than one licensing authority named in the report", "Medium", f"{sorted(hits)} (e.g. 'Dubai Integrated Economic Zones Authority' with 'DSO-IFZA'). Confirm to the licence: the authority, free-zone and address must be one consistent set.", "Section 1.1", str(c.eng["client"].get("authority", "")), str(sorted(hits))))
    cl = c.eng["client"]
    known = {re.sub(r"[^a-z]", "", n.lower()) for n in list(cl.get("signatories_legal") or []) + list(cl.get("shareholders") or []) + list(cl.get("managers") or [])}
    names = set(re.findall(r"\b(?:Mr|Ms|Mrs|Dr)\.?\s+(?:(?:Mr|Ms|Mrs)\.?\s+)?([A-Z]{2,})\b", c.full_text()))
    if known:
        miss = sorted(n for n in names if re.sub(r"[^a-z]", "", n.lower()) not in known and not any(re.sub(r"[^a-z]", "", n.lower()) in k for k in known))
        if miss:
            out.append(_ex("TP-69", "Person named in the report is not a manager/signatory/shareholder per the licence/MOA data", "Medium", ", ".join(miss), f"Report ('{miss[0]}')", "licence / MOA / fact sheet", ", ".join(miss)))
    sh = re.search(r"([A-Z][A-Za-z0-9 ]+(?:LTD|LLC|FZE|FZCO|INC|PLC|DMCC))[^.]{0,40}sole\s+shareholder", c.full_text())
    if sh and names:
        out.append(_ex("TP-69", "Sole shareholder is a company but the KMPs are individuals: confirm the ultimate beneficial owners and that the KMPs are not the owners (remuneration vs profit extraction)", "Medium", f"Shareholder: {sh.group(1).strip()}; KMPs: {', '.join(sorted(names))}", "Sections 1.1 / 1.2", "UBO per MOA/Register", "not stated"))
    return out


def tp70_embedded_annexures(c: TPCtx):
    t = _norm(c)
    if re.search(r"double[- ]click the icon|embedded (file|object)|\.zip\b", t, re.I):
        return [_ex("TP-70", "Annexures are an embedded file (zip icon) - not visible in the PDF / not part of the report", "High",
                    "The reviewer, the FTA and any PDF reader cannot open the benchmark workings. Print Annexures 1-9 into the report or issue as a separate file set; the report also refers to 'Annexure A' (Appendix A) which is not an annexure.", "Appendix A", "annexures printed in the document", "embedded zip icon")]
    return []


def _only(fn, cid):
    return lambda c: [f for f in fn(c) if f.check_id == cid]


REGISTRY = {"TP-01": tp01_name, "TP-02": tp02_title, "TP-03": tp03_year, "TP-06": tp06_font, "TP-07": tp07_sizes, "TP-11": tp11_header,
            "TP-12": tp12_pageno, "TP-14": tp14_footer, "TP-15": tp15_consistency, "TP-16": tp16_border, "TP-17": tp17_index,
            "TP-20": _only(tp21_annexures, "TP-20"), "TP-21": _only(tp21_annexures, "TP-21"), "TP-23": _only(tp21_annexures, "TP-23"), "TP-30": tp30_fs, "TP-37": tp37_pli, "TP-38": tp38_quality, "TP-45": tp45_count, "TP-46": tp46_stats,
            "TP-47": tp47_position, "TP-49": tp49_consistency, "TP-50": tp50_names, "TP-55": tp55_entity, "TP-57": tp57_ct, "TP-58": tp58_thresholds,
            "TP-60": tp60_placeholders, "TP-61": tp61_doubled, "TP-62": tp62_draft, "TP-63": tp63_year_body, "TP-64": tp64_table_recompute,
            "TP-65": tp65_funnel, "TP-66": tp66_geography, "TP-67": tp67_role_scale, "TP-68": tp68_adjustment, "TP-69": tp69_authority_people, "TP-70": tp70_embedded_annexures}



def _norm_t(x):
    return re.sub(r"[\s\u00a0]+", " ", str(x)).lower()


def locate(ctx, f):
    """Add the page (PDF + printed number) or nearest heading (Word) where the evidence sits, so the reviewer can go straight to it."""
    if re.search(r"\bp\.\s?\d|\bpage\s+\d|pdf p\.|table \d|row \d|under heading", f.location or "", re.I):
        return
    needles = [m for m in re.findall(r"'([^']{4,80})'", f.detail or "")]
    for v in (f.found, f.expected):
        if v and len(str(v)) >= 4 and re.search(r"[A-Za-z0-9]", str(v)):
            needles.append(str(v).strip("[]'\" "))
    needles += [seg.strip() for seg in re.split(r"[;|]", f.detail or "") if 8 <= len(seg.strip()) <= 70][:2]
    needles = [_norm_t(n)[:60] for n in needles if n]
    doc = ctx.doc
    if doc.kind != "docx" and doc.pages:
        pm = None
        for n in needles:
            for i, pg in enumerate(doc.pages):
                if n and n in _norm_t(pg):
                    try:
                        pm = pm or _printed_page_map(ctx)
                    except Exception:
                        pm = {}
                    pr = pm.get(i + 1)
                    f.location = f"{f.location} - PDF p.{i + 1}" + (f" (printed p.{pr})" if pr else "")
                    return
    elif doc.kind == "docx":
        head = ""
        for p in doc.paragraphs:
            t = p.text.strip()
            if t and len(t) < 90 and (t.isupper() or re.match(r"^\d+(\.\d+)*\.?\s+\S", t)):
                head = t
            for n in needles:
                if n and n in _norm_t(t):
                    f.location = f"{f.location} - under heading '{head or 'start'}'"
                    return


def _cover_evidence(c, cid):
    pg1 = "PDF p.1 (cover picture)"
    t = _norm(c)
    ftr = [l.strip() for p in c.doc.pages[2:5] for l in p.splitlines() if l.strip()][-1:] if c.doc.pages else []
    hdr = [l.strip() for p in c.doc.pages[2:3] for l in p.splitlines() if l.strip()][:1]
    yrs = sorted({int(y) for y in re.findall(r"(?:financial year(?: ending| ended)?|FY)\D{0,12}(20\d{2})", t, re.I)})
    ev = {"TP-01": f"Check the cover shows '{c.name}'. Name in footer/body: footer '{ftr[0] if ftr else 'n/a'}'; matches licence name: {c.name.lower() in t.lower()}.",
          "TP-02": f"Check the cover title is one of {c.p['titles'][:2]}. Header title on PDF p.3: '{hdr[0] if hdr else 'n/a'}'.",
          "TP-03": f"Check the cover year is FY {c.cy}. Years used in the body: {yrs}."}[cid]
    return [_ex(cid, "Cover is a picture - confirm visually", "Info", ev, pg1, "", "")]


def run_tp_engine(report_path, workbook_path, eng, params, fs_path=None, ct_adj=None, facts=None):
    """Runs the individual test functions (internal ids). run_tp() maps them onto the firm's checklist rows."""
    from .legacy import ensure_modern
    rp = ensure_modern(report_path)
    doc = load_document(rp)
    wb = TPWorkbook(workbook_path, params) if workbook_path else None
    fs, fs_note = None, ""
    if fs_path:
        try:
            fs = load_document(fs_path)
        except RuntimeError as e:          # scanned FS but no OCR on this PC: carry on, FS-dependent checks show Not run
            fs_note = "Audited FS could not be read: " + str(e)[:220]
    ctx = TPCtx(doc, wb, eng, params, fs, ct_adj, facts, path=rp)
    ctx.fs_note = fs_note
    ctx.wb_path = workbook_path
    from .rules_tp2 import A_REGISTRY, ASSIST_REGISTRY, install_pdf_variants
    reg = install_pdf_variants(dict(REGISTRY))
    results = []
    for cid, fn in {**reg, **A_REGISTRY, **ASSIST_REGISTRY}.items():
        try:
            f = fn(ctx)
            if getattr(fn, "assist", False):
                results.append(Result(cid, "REVIEW", f, "Assisted: evidence extracted, reviewer to confirm"))
            else:
                results.append(Result(cid, "EXC" if f else "PASS", f))
        except NotRun as e:
            msg = str(e)
            if msg.startswith("Applies to"):
                results.append(Result(cid, "NA", [], msg))
            elif msg.startswith("Cover page is a picture"):
                results.append(Result(cid, "REVIEW", _cover_evidence(ctx, cid), "Cover is a picture: evidence from header/footer/body for the reviewer to confirm"))
            else:
                results.append(Result(cid, "NOTRUN", [], msg))
        except Exception as e:                      # a rule must never stop the whole review
            results.append(Result(cid, "NOTRUN", [], f"Rule could not run on this file: {type(e).__name__}: {str(e)[:120]}"))
    for r in results:
        for f in r.findings:
            try:
                locate(ctx, f)
            except Exception:
                pass
    results.sort(key=lambda r: int(r.check_id.split("-")[1]) if r.check_id.split("-")[1].isdigit() else 0)
    return results, ctx


def run_tp(report_path, workbook_path, eng, params, fs_path=None, ct_adj=None, facts=None, birf_path=None):
    """Module C: runs the engine, then reports against the firm's TP checklist (rules/catalogue.yaml, sections 1.1 - 1.14)."""
    from .tp_checklist import apply_checklist
    legacy, ctx = run_tp_engine(report_path, workbook_path, eng, params, fs_path, ct_adj, facts)
    ctx.birf, ctx.birf_note = None, ""
    if birf_path:
        try:
            ctx.birf = load_document(birf_path)
        except RuntimeError as e:
            ctx.birf_note = "BIRF could not be read: " + str(e)[:200]
    results = apply_checklist(legacy, ctx)
    for r in results:
        for f in r.findings:
            try:
                if not f.location or f.location in ("Report", "Whole report"):
                    locate(ctx, f)
            except Exception:
                pass
    results.sort(key=lambda r: int(r.check_id.split("-")[1]))
    return results, ctx
