"""Heuristic field parser for Indian GST invoices (text from PDF layer, DOCX/XLSX or OCR).

Strategy: label-anchored regexes first (high confidence), then structural fallbacks
(largest amount, first date) at lower confidence. Every field records its confidence so the
pipeline can decide whether to call Gemini.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from ..gst_states import STATE_CODES, state_code
from ..tally.parsers import gstin_valid, scan_gstins
from .schema import Invoice, TaxRow

_NUM = r"-?(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d{1,2})?"
_NUM_RE = re.compile(rf"(?<![\w.,/-])({_NUM})(?![\w/-]|\.\d|,\d)")
_RATE_RE = re.compile(r"(\d{1,2}(?:\.\d{1,2})?)\s*%")
_MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep",
                                           "oct", "nov", "dec"])}
_DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b"),                    # 05/11/2026
    re.compile(r"\b(\d{1,2})[\s\-./]*([A-Za-z]{3,9})[\s\-.,/]*(\d{4})\b"),        # 5-Nov-2026, 05 November 2026
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),                                  # 2026-11-05
    re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2})\b"),                    # 05/11/26
    re.compile(r"\b(\d{1,2})[\s\-./]+([A-Za-z]{3,9})[\s\-./]+(\d{2})\b"),          # 01-OCT-26
]
_INV_LABEL = re.compile(
    r"(?<!against )(?<!original )(?:tax\s+)?(?:invoice|inv|bill|document|doc|(?:credit\s+|debit\s+)?note)\.?\s*"
    r"(?:no|number|num|#)\.?\s*[:\-.]?\s*([A-Z0-9][A-Z0-9/\-_.]{0,24})",
    re.I)
# a value that is only a date (05-11-2026, 05/Nov/26): an invoice number like CN/INV/26-11/0457 is not
_DATE_ONLY = re.compile(r"\d{1,4}[/\-. ](?:\d{1,2}|[A-Za-z]{3,9})[/\-. ]\d{2,4}")
_AGAINST = re.compile(r"(?:against|original|ref\.?|reference)\s+(?:tax\s+)?(?:invoice|inv|bill)\.?\s*(?:no\.?|number)?"
                      r"\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-_.]{2,24})", re.I)
_GST_RATES = ("0", "0.1", "0.25", "1", "1.5", "3", "5", "6", "12", "18", "28", "40")
# item row: ... HSN ... GST% amount  (rate column printed per line, amount last)
_ITEM_RATE = re.compile(r"\b(\d{4,8})\b.*?\s(\d{1,2}(?:\.\d{1,2})?)\s*%?\s+([\d,]+\.\d{2})\s*$")


def is_date_only(s: str) -> bool:
    return bool(_DATE_ONLY.fullmatch((s or "").strip(" .,:")))
_DATE_LABEL = re.compile(r"(?:invoice|inv|bill|document|doc)?\.?\s*(?:date|dated|dt)\.?\s*[:\-]?\s*(.{0,24})", re.I)


def to_dec(s: str) -> Decimal:
    try:
        return Decimal(s.replace(",", ""))
    except (InvalidOperation, AttributeError):
        return Decimal(0)


def amounts_in(line: str) -> list[Decimal]:
    out = []
    for m in _NUM_RE.finditer(line):
        tok = m.group(1)
        digits = tok.replace(",", "").replace("-", "").split(".")[0]
        if len(digits) > 12:
            continue
        out.append(to_dec(tok))
    return out


def last_amount(line: str, prefer_decimal: bool = True) -> Decimal | None:
    """Rightmost money-looking number on a line (skips percentages)."""
    clean = _RATE_RE.sub(" ", line)
    toks = [m.group(1) for m in _NUM_RE.finditer(clean)]
    if prefer_decimal:
        dec = [t for t in toks if "." in t]
        if dec:
            return to_dec(dec[-1])
    return to_dec(toks[-1]) if toks else None


def parse_date(s: str) -> str:
    """Any common Indian date format -> YYYYMMDD ('' if none)."""
    for i, pat in enumerate(_DATE_PATTERNS):
        m = pat.search(s)
        if not m:
            continue
        try:
            if i == 0:
                d, mo, y = int(m[1]), int(m[2]), int(m[3])
            elif i == 1:
                mo = _MONTHS.get(m[2][:3].lower())
                if not mo:
                    continue
                d, y = int(m[1]), int(m[3])
            elif i == 2:
                y, mo, d = int(m[1]), int(m[2]), int(m[3])
            elif i == 3:
                d, mo, y = int(m[1]), int(m[2]), 2000 + int(m[3])
            else:
                mo = _MONTHS.get(m[2][:3].lower())
                if not mo:
                    continue
                d, y = int(m[1]), 2000 + int(m[3])
            return date(y, mo, d).strftime("%Y%m%d")
        except (ValueError, TypeError):
            continue
    return ""


def squeeze(s: str) -> str:
    """Lowercase, no whitespace: makes labels robust to PDFs that split glyphs ('G rand  Total')."""
    return re.sub(r"\s+", "", s.lower())


def _label_line_value(lines: list[str], labels: list[str], exclude: list[str] | None = None) -> Decimal | None:
    """Amount on the last line matching any label (totals usually appear after line items).
    Labels are matched against the squeezed line, so write them without spaces."""
    pat = re.compile("|".join(labels), re.I)
    ex = re.compile("|".join(exclude), re.I) if exclude else None
    found = None
    for ln in lines:
        sq = squeeze(ln)
        if pat.search(sq) and not (ex and ex.search(sq)):
            v = last_amount(ln)
            if v is not None and v != 0:
                found = v
    return found


_NOT_MONEY_CTX = re.compile(r"mob|phone|ph[.:]|tel|fax|a/?c|account|ifsc|gstin|pan|pin|cin|service\s*no|"
                            r"consumer|meter|hsn|sac|code|unit\s*no|\bno\b", re.I)


def money_candidates(lines: list[str]) -> list[Decimal]:
    """Numbers that look like money: 2 decimals or Indian/intl comma grouping, not on identifier lines."""
    out = []
    for ln in lines:
        if _NOT_MONEY_CTX.search(ln) and not re.search(r"\d\.\d{2}\b", ln):
            continue
        for m in _NUM_RE.finditer(_RATE_RE.sub(" ", ln)):
            tok = m.group(1)
            if "." in tok and len(tok.split(".")[1]) == 2 or "," in tok:
                v = to_dec(tok)
                if 0 < abs(v) < Decimal("10000000000"):
                    out.append(abs(v))
    return out


def _find_close(cands: list[Decimal], target: Decimal, tol: Decimal = Decimal("1.00")) -> Decimal | None:
    best = None
    for c in cands:
        if abs(c - target) <= tol and (best is None or abs(c - target) < abs(best - target)):
            best = c
    return best


def value_below(lines: list[str], label_re: str, kind: str = "text", max_down: int = 3) -> str:
    """Tally-style box: label on one line, its value directly beneath it in the same column."""
    pat = re.compile(label_re, re.I)
    for i, ln in enumerate(lines):
        m = pat.search(ln)
        if not m:
            continue
        rest = ln[m.end():]
        if kind == "text" and re.search(r"[:\-]\s*[A-Z0-9]", rest[:6], re.I):
            continue                                   # value is on the same line
        col0, col1 = m.start(), max(m.end(), m.start() + 12)
        for j in range(i + 1, min(len(lines), i + 1 + max_down)):
            below = lines[j]
            for tok in re.finditer(r"\S+(?: \S+)*", below):
                if tok.end() > col0 - 2 and tok.start() < col1 + 4:
                    val = tok.group(0).strip()
                    if kind == "date" and parse_date(val):
                        return val
                    if kind == "text" and re.search(r"\d", val) and len(val) <= 30 and not is_date_only(val):
                        return val.split()[0]
                    if kind == "money" and last_amount(val) is not None:
                        return val
    return ""


def parse(text: str, company_gstin: str = "") -> Invoice:
    inv = Invoice(raw_text=text, source="text")
    conf = inv.field_confidence
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    upper = text.upper()

    # ---- GSTINs: buyer = our company; supplier = first other valid GSTIN
    gstins = scan_gstins(upper.encode())
    company_gstin = (company_gstin or "").upper()
    others = [g for g in gstins if g != company_gstin]
    if others:
        inv.supplier_gstin = others[0]
        conf["supplier_gstin"] = 0.95 if company_gstin in gstins or len(gstins) == 1 else 0.75
    if company_gstin and company_gstin in gstins:
        inv.buyer_gstin, conf["buyer_gstin"] = company_gstin, 0.95
    elif len(others) > 1:
        inv.buyer_gstin, conf["buyer_gstin"] = others[1], 0.6
    if inv.supplier_gstin:
        inv.supplier_pan = inv.supplier_gstin[2:12]

    # ---- supplier name: nearest meaningful line above the supplier GSTIN, else first header line
    skip = re.compile(r"tax\s*invoice|invoice|original|duplicate|triplicate|recipient|gstin|^page|e-?invoice|irn",
                      re.I)
    if inv.supplier_gstin:
        for i, ln in enumerate(lines):
            if inv.supplier_gstin in ln.upper().replace(" ", ""):
                # topmost name-like line in the block above the GSTIN (address lines carry digits)
                cands = []
                for j in range(i - 1, max(-1, i - 7), -1):
                    cand = re.split(r"\s{3,}", lines[j].strip())[0].strip(" :,")
                    if len(cand) <= 3 or skip.search(cand) or re.search(r"@|www\.|phone|ph[:.]|mob|e-?mail",
                                                                         cand, re.I):
                        continue
                    if re.match(r"^\d|.*\b\d{6}\b", cand):
                        continue
                    score = (2 if re.search(r"\b(pvt|private|ltd|limited|llp|agenc|traders|enterprise|industries|"
                                            r"solutions|services|& co|corporation|stores|company)\b", cand, re.I)
                             else 0) + (1 if cand.isupper() else 0) + (i - j) * 0.1
                    cands.append((score, cand))
                if cands:
                    inv.supplier_name, conf["supplier_name"] = max(cands)[1], 0.7
                break
    if not inv.supplier_name:
        for ln in lines[:8]:
            cand = re.split(r"\s{3,}", ln.strip())[0]
            if len(cand) > 3 and not skip.search(cand):
                inv.supplier_name, conf["supplier_name"] = cand.strip(" :,"), 0.4
                break

    # ---- invoice number
    for ln in lines:
        m = _INV_LABEL.search(ln)
        if m and re.search(r"\d", m.group(1)) and not is_date_only(m.group(1)):
            inv.invoice_no, conf["invoice_no"] = m.group(1).strip(".-_/"), 0.9
            break

    if not inv.invoice_no:
        v = value_below(lines, r"(invoice|inv|bill|document)\.?\s*(no|number)\.?", "text")
        if v:
            inv.invoice_no, conf["invoice_no"] = v.strip(".-_/:"), 0.85

    # ---- credit / debit note issued by the supplier
    head = " ".join(lines[:12]).upper()
    if re.search(r"\bCREDIT\s+NOTE\b", head):
        inv.document_type = "credit_note"
    elif re.search(r"\bDEBIT\s+NOTE\b", head):
        inv.document_type = "debit_note"
    elif re.search(r"\bBILL\s+OF\s+SUPPLY\b", head):
        inv.document_type = "bill_of_supply"
    elif re.search(r"\bTAX\s+INVOICE\b", head):
        inv.document_type = "tax_invoice"
    if inv.document_type in ("credit_note", "debit_note"):
        m = _AGAINST.search(text)
        if m and not is_date_only(m.group(1)):
            inv.original_invoice_no = m.group(1).strip(".-_/")

    # ---- invoice date: label first, then value below label, then first date in document
    for ln in lines:
        if re.search(r"(invoice|inv|bill|doc)\w*\.?\s*(date|dt|dated)|\bdated\b|\bdate\b", ln, re.I) and \
                not re.search(r"due|order|challan|delivery|po\b|ack|e-?way|irn", ln, re.I):
            m = _DATE_LABEL.search(ln)
            d = parse_date(m.group(1)) if m else ""
            d = d or parse_date(ln)
            if d:
                inv.invoice_date, conf["invoice_date"] = d, 0.9
                break
    if not inv.invoice_date:
        v = value_below(lines, r"(?:invoice|inv|bill|doc\w*)\.?\s*(?:date|dt)\b|\bdated\b", "date")
        if v:
            inv.invoice_date, conf["invoice_date"] = parse_date(v), 0.85
    if not inv.invoice_date:
        d = parse_date(text)
        if d:
            inv.invoice_date, conf["invoice_date"] = d, 0.5

    # ---- place of supply / reverse charge / IRN
    m = re.search(r"place\s+of\s+supply\s*[:\-]?\s*(\d{2})?[\s\-()]*([A-Za-z &]+)?", text, re.I)
    if m:
        code = m.group(1) or state_code((m.group(2) or "").strip())
        if not code and m.group(2):
            code = next((c for n, c in STATE_CODES.items() if m.group(2).strip().lower().startswith(n)), "")
        if code:
            inv.place_of_supply, conf["place_of_supply"] = code, 0.9
    m = re.search(r"reverse\s+charge[^\n]{0,30}?\b(yes|no|y|n)\b", text, re.I)
    if m:
        inv.reverse_charge = m.group(1).lower().startswith("y")
    m = re.search(r"\bIRN\s*(?:no\.?)?\s*[:\-]?\s*([0-9a-f]{64})\b", text, re.I)
    if m:
        inv.irn = m.group(1).lower()

    # ---- taxes: CGST / SGST|UTGST / IGST / Cess, with rate if printed
    heads = {"igst": r"igst(?!in)|integratedtax", "cgst": r"cgst(?!in)|centraltax",
             "sgst": r"(?<![a-z])[su]t?gst(?!in)|statetax|uttax|state/uttax", "cess": r"cess"}
    rows: dict[Decimal, TaxRow] = {}
    totals = {k: Decimal(0) for k in heads}
    summary_seen = {k: False for k in heads}
    for ln in lines:
        sq = squeeze(ln)
        for head, pat in heads.items():
            if not re.search(pat, sq):
                continue
            if re.search(r"gstin|number|no\.|reg", sq) and not _RATE_RE.search(ln):
                continue
            amt = last_amount(ln)
            if amt is None or amt <= 0:
                continue
            rate_m = _RATE_RE.search(ln)
            rate = to_dec(rate_m.group(1)) if rate_m else None
            is_total = "total" in sq
            if is_total:
                totals[head] = amt                 # explicit total wins
                summary_seen[head] = True
            elif not summary_seen[head]:
                totals[head] += amt
            if rate is not None and head != "cess":
                full = rate * 2 if head in ("cgst", "sgst") else rate
                row = rows.setdefault(full, TaxRow(rate=full))
                setattr(row, head, getattr(row, head) + amt)
    inv.igst_total, inv.cgst_total, inv.sgst_total, inv.cess_total = (totals["igst"], totals["cgst"],
                                                                       totals["sgst"], totals["cess"])
    for k in ("igst_total", "cgst_total", "sgst_total"):
        if getattr(inv, k):
            conf[k] = 0.8

    # ---- totals
    inv.taxable_total = _label_line_value(lines, [r"taxable(value|amount|amt)", r"assessablevalue",
                                                  r"sub-?total", r"totalbeforetax"]) or Decimal(0)
    if inv.taxable_total:
        conf["taxable_total"] = 0.8
    inv.round_off = _label_line_value(lines, [r"round(ed|ing)?-?off", r"rounding"]) or Decimal(0)
    if abs(inv.round_off) > 1:
        inv.round_off = Decimal(0)
    if re.search(r"round(ed|ing)?\s*-?\s*off[^\n]*(\(-\)|less|-\s*\d)", text, re.I) and inv.round_off > 0:
        inv.round_off = -inv.round_off
    inv.tcs = _label_line_value(lines, [r"(?<![a-z])tcs(?![a-z])"]) or Decimal(0)
    grand = _label_line_value(lines, [r"grandtotal", r"totalinvoice(value|amount)", r"invoicetotal",
                                      r"totalamount(payable|due)", r"(net)?amountpayable", r"netpayable",
                                      r"netamount", r"billamount", r"totalamount", r"^total(?![a-z])"],
                              exclude=[r"taxable", r"inwords", r"totaltax", r"taxamount", r"afterdue", r"duedate",
                                       r"^total\d", r"^totalvalue"])
    if grand is None:
        for ln in reversed(lines):
            m = re.search(r"(?:grand\s+)?total(?:\s+amount)?\s*(?:\(?(?:rs\.?|inr|₹)\)?)?\s*[:\-]?\s*([\d,]+\.\d{2})\s*$",
                          ln, re.I)
            if m and not re.search(r"taxable|total\s+tax|sub\s*-?\s*total", ln[:m.start(1)], re.I):
                grand = to_dec(m.group(1))
                break
    cands = money_candidates(lines)
    tax = inv.tax_total

    # 1) taxable from tax / rate, confirmed by an amount printed on the page
    rate_c = next((r for r in rows if rows[r].cgst or rows[r].sgst), None)
    rate_i = next((r for r in rows if rows[r].igst), None)
    est = None
    if rate_c and inv.cgst_total:
        est = inv.cgst_total * 100 / (rate_c / 2)
    elif rate_i and inv.igst_total:
        est = inv.igst_total * 100 / rate_i
    if est:
        tol = max(Decimal("1.00"), est * Decimal("0.0005"))
        hit = _find_close(cands, est, tol)
        if hit and (not inv.taxable_total or abs(inv.taxable_total - hit) > 1):
            inv.taxable_total, conf["taxable_total"] = hit, 0.9
        elif inv.taxable_total and abs(inv.taxable_total - est) <= tol:
            conf["taxable_total"] = 0.9

    # 2) grand total = taxable + tax + TCS (+ round-off), confirmed on the page
    if inv.taxable_total and tax:
        g_est = inv.taxable_total + tax + inv.tcs
        hit = _find_close(cands, g_est, Decimal("1.00"))
        if grand and abs(grand - g_est) <= 1:
            inv.grand_total, conf["grand_total"] = grand, 0.95
        elif grand and grand > 0:
            # a printed total that disagrees with taxable + tax is kept as printed so validation flags it
            inv.grand_total, conf["grand_total"] = grand, 0.6
        elif hit:
            inv.grand_total, conf["grand_total"] = hit, 0.9
        elif grand:
            inv.grand_total, conf["grand_total"] = grand, 0.6
        else:
            inv.grand_total, conf["grand_total"] = g_est.quantize(Decimal("1")), 0.5
        if conf["grand_total"] >= 0.9:
            inv.round_off = inv.grand_total - g_est
    elif grand:
        inv.grand_total, conf["grand_total"] = grand, 0.85
    else:
        below = value_below(lines, r"(net\s*)?amount\s*payable|total\s*amount|grand\s*total|bill\s*amount", "money")
        if below:
            inv.grand_total, conf["grand_total"] = last_amount(below) or Decimal(0), 0.7
        elif cands:
            inv.grand_total, conf["grand_total"] = max(cands), 0.35

    if not inv.taxable_total and inv.grand_total and tax:
        inv.taxable_total = inv.grand_total - tax - inv.round_off - inv.tcs
        conf["taxable_total"] = 0.6

    # tax slabs from a per-line GST% column (mixed-rate invoices print one tax total)
    if len(rows) <= 1 and inv.taxable_total and tax:
        per: dict[Decimal, Decimal] = {}
        for ln in lines:
            m = _ITEM_RATE.search(ln)
            if m and to_dec(m.group(2)).normalize() in {Decimal(x) for x in _GST_RATES}:
                r = to_dec(m.group(2))
                per[r] = per.get(r, Decimal(0)) + to_dec(m.group(3))
        gst = inv.igst_total + inv.cgst_total + inv.sgst_total
        if len(per) > 1 and abs(sum(per.values()) - inv.taxable_total) <= 1:
            exp = {r: t * r / 100 for r, t in per.items()}
            if abs(sum(exp.values()) - gst) <= max(Decimal("1.00"), gst * Decimal("0.005")):
                rows = {}
                rates = sorted(per)
                left = {"igst": inv.igst_total, "cgst": inv.cgst_total, "sgst": inv.sgst_total}
                for k, r in enumerate(rates):
                    row = TaxRow(rate=r, taxable=per[r])
                    for head in ("igst", "cgst", "sgst"):
                        tot = getattr(inv, head + "_total")
                        if not tot:
                            continue
                        part = (exp[r] * tot / gst).quantize(Decimal("0.01")) if k < len(rates) - 1 else left[head]
                        left[head] -= part
                        setattr(row, head, part)
                    rows[r] = row
                for r in rows.values():
                    r.taxable = per[r.rate]
                inv.taxes = sorted(rows.values(), key=lambda r: r.rate)
                if not tax and inv.grand_total:
                    inv.taxable_total = inv.taxable_total or inv.grand_total - inv.round_off
                return inv

    # tax slabs: if no rate printed, infer from tax / taxable
    if not rows and inv.taxable_total and tax:
        pct = ((inv.igst_total + inv.cgst_total + inv.sgst_total) * 100 / inv.taxable_total).quantize(Decimal("0.01"))
        nearest = min([Decimal(r) for r in ("0.1", "0.25", "1.5", "3", "5", "6", "12", "18", "28", "40")],
                      key=lambda r: abs(r - pct))
        if abs(nearest - pct) <= Decimal("0.3"):
            rows[nearest] = TaxRow(rate=nearest, igst=inv.igst_total, cgst=inv.cgst_total, sgst=inv.sgst_total)
    for r in rows.values():
        tax_r = r.igst + r.cgst + r.sgst
        r.taxable = (tax_r * 100 / r.rate).quantize(Decimal("0.01")) if r.rate else Decimal(0)
    if len(rows) == 1 and inv.taxable_total:
        next(iter(rows.values())).taxable = inv.taxable_total
    inv.taxes = sorted(rows.values(), key=lambda r: r.rate)
    if not tax and inv.grand_total:
        inv.taxable_total = inv.taxable_total or inv.grand_total - inv.round_off
    return inv


def hsn_codes(text: str) -> list[str]:
    """HSN/SAC codes printed in the document (4/6/8 digits, near an HSN/SAC label or in item rows)."""
    out: list[str] = []
    lines = text.splitlines()
    hsn_col = False
    for ln in lines:
        if re.search(r"\b(HSN|SAC)\b", ln, re.I):
            hsn_col = True
            for m in re.finditer(r"(?:HSN|SAC)[^\d\n]{0,15}(\d{4}(?:\d{2}){0,2})\b", ln, re.I):
                out.append(m.group(1))
            continue
        if hsn_col and _RATE_RE.search(ln) or hsn_col and len(amounts_in(ln)) >= 2:
            for m in re.finditer(r"(?<![\d.,])(\d{4}|\d{6}|\d{8})(?![\d.,%])", ln):
                code = m.group(1)
                if not code.startswith(("19", "20")) or len(code) != 4:   # skip years
                    out.append(code)
    seen = []
    for c in out:
        if c not in seen:
            seen.append(c)
    return seen
