"""Module B part 2 - liquidation DOCUMENT checks: Board Resolution, Statement of Affairs, Liquidator's report, TB, CT/VAT registration evidence.
Documents may be Word, PDF (text or scanned, OCR), Excel or image. Every finding carries the document and page/heading."""
from __future__ import annotations
import re
from datetime import date

from .loaders import find_row, load_document, load_tb
from .models import Finding, Result
from .refs import locate
from .rules_fs import MONTHS, fuzzy_hits, same_name

DOC_ROLES = {"br": "Board Resolution", "soa": "Statement of Affairs", "report": "Liquidator's report", "soa_report": "Statement of Affairs / Liquidator's report", "tb": "Trial balance",
             "ctvat": "CT / VAT registration certificate or FTA letter", "licence": "Trade licence / MOA"}
TRN = re.compile(r"\b(100\d{12})\b")


class Docs:
    def __init__(self, paths: dict):
        self.d, self.errors, self.tb = {}, {}, None
        for role, plist in (paths or {}).items():
            plist = plist if isinstance(plist, (list, tuple)) else [plist]
            for p in plist:
                if not p:
                    continue
                try:
                    if role == "tb":
                        try:
                            self.tb = load_tb(p)
                        except Exception:
                            self.d.setdefault("tb_doc", []).append(load_document(p))
                    elif role == "soa_report":
                        d = load_document(p)               # one upload slot for the Statement of Affairs and/or the Liquidator's report
                        t = d.all_text
                        has_soa = bool(re.search(r"statement of affairs", t, re.I))
                        has_rep = bool(re.search(r"liquidator|liquidation report|final report|audit report", t, re.I))
                        if has_soa:
                            self.d.setdefault("soa", []).append(d)
                        if has_rep or not has_soa:
                            self.d.setdefault("report", []).append(d)
                    else:
                        self.d.setdefault(role, []).append(load_document(p))
                except Exception as e:
                    self.errors[role] = f"{type(e).__name__}: {str(e)[:200]}"
        # a Statement of Affairs that sits inside the report (or the other way round) is still found
        for a, b in (("soa", "report"), ("report", "soa")):
            if not self.d.get(a) and self.d.get(b) and re.search(r"statement of affairs" if a == "soa" else r"liquidator", "\n".join(x.all_text for x in self.d[b]), re.I):
                self.d[a] = list(self.d[b])

    def get(self, role):
        return self.d.get(role) or []

    def text(self, role):
        return "\n".join(re.sub(r"[ \t]+", " ", x.all_text) for x in self.get(role))


def _mk(label, doc, cid, title, sev, detail, exp="", found=""):
    f = Finding(cid, title, sev, detail, label, str(exp), str(found))
    if doc is not None:
        try:
            locate(doc, f)
        except Exception:
            pass
    return f


def _dates(txt):
    out = []
    for m in re.finditer(r"(\d{1,2})(?:st|nd|rd|th)?\s+(?:day of\s+)?(January|February|March|April|May|June|July|August|September|October|November|December),?\s+(20\d{2})", txt, re.I):
        try:
            out.append(date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))))
        except ValueError:
            pass
    for m in re.finditer(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](20\d{2})\b", txt):
        try:
            out.append(date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
        except ValueError:
            pass
    return out


def _need(docs, *roles):
    miss = [DOC_ROLES[r] for r in roles if not docs.get(r)]
    if miss:
        raise _NR("Upload: " + ", ".join(miss) + (f" (could not read: {docs.errors}) " if any(r in docs.errors for r in roles) else ""))


class _NR(Exception):
    pass


def _amount(txt, rx):
    m = re.search(rx + r"[^\n\d(-]{0,40}\(?(?P<amt>-?\d[\d,]*\.?\d*)\)?", txt, re.I)
    return float(m.group("amt").replace(",", "")) if m else None


# ------------------------------------------------------------------ LQ-21 Board Resolution
def lq21_br(inp, D, docs):
    _need(docs, "br")
    doc, t = docs.get("br")[0], docs.text("br")
    name, out, L = inp["company"], [], "Board Resolution"
    if not fuzzy_hits(t, name, 0.88):
        out.append(_mk(L, doc, "LQ-21", "Company name per the tracker/licence not found in the Board Resolution", "High", f"'{name}' not found", name, "absent"))
    if not re.search(r"(voluntar\w+\s+(liquidat|winding|dissol)|resolved (to|that)[^.]{0,80}(liquidat|dissol|wind))", t, re.I):
        out.append(_mk(L, doc, "LQ-21", "No resolution wording to liquidate / dissolve found", "High", "Expected 'resolved to voluntarily liquidate' or equivalent", "liquidation resolution", "absent"))
    liq = (inp.get("liquidator") or {}).get("name")
    if liq and not fuzzy_hits(t, liq, 0.88):
        out.append(_mk(L, doc, "LQ-21", "Liquidator named in the tracker is not named in the Board Resolution", "High", f"'{liq}' not found", liq, "absent"))
    if not liq and not re.search(r"appoint\w*[^.]{0,60}liquidator|liquidator[^.]{0,40}appointed", t, re.I):
        out.append(_mk(L, doc, "LQ-21", "Liquidator appointment not found in the Board Resolution", "High", "No wording appointing a liquidator", "appointment", "absent"))
    brd = D.get("board_resolution")
    ds = _dates(t)
    if brd and ds and brd not in ds:
        out.append(_mk(L, doc, "LQ-21", "Board Resolution date in the tracker does not appear in the document", "High", f"Tracker {brd:%d %B %Y}; dates in document {sorted({d.isoformat() for d in ds})[:4]}", brd.isoformat(), ", ".join(sorted({d.isoformat() for d in ds})[:3])))
    if not ds:
        out.append(_mk(L, doc, "LQ-21", "No date found in the Board Resolution", "High", "A dated resolution is required", "date", "absent"))
    sh = inp.get("shareholders") or []
    miss = [s for s in sh if not fuzzy_hits(t, s, 0.88)]
    if miss:
        out.append(_mk(L, doc, "LQ-21", "Shareholder/partner not named or not signing in the Board Resolution", "High", "; ".join(miss), "; ".join(sh), "missing: " + "; ".join(miss)))
    if not re.search(r"sign|signature|signed|authori[sz]ed signator", t, re.I):
        out.append(_mk(L, doc, "LQ-21", "No signature block text found", "Medium", "Check signed by all shareholders/partners (scan quality may hide text)", "signed", "not found"))
    return out


# ------------------------------------------------------------------ LQ-22 Statement of Affairs
def lq22_soa(inp, D, docs):
    _need(docs, "soa")
    doc, t = docs.get("soa")[0], docs.text("soa")
    out, L = [], "Statement of Affairs"
    if not fuzzy_hits(t, inp["company"], 0.88):
        out.append(_mk(L, doc, "LQ-22", "Company name not found in the Statement of Affairs", "High", f"'{inp['company']}'", inp["company"], "absent"))
    ds = _dates(t)
    if not re.search(r"\bas (at|on)\b", t, re.I) or not ds:
        out.append(_mk(L, doc, "LQ-22", "'As at' date missing in the Statement of Affairs", "High", "Date of the statement is required", "as at date", "absent"))
    ta = _amount(t, r"total assets") ; tl = _amount(t, r"total liabilities")
    net = _amount(t, r"(net (assets|surplus|deficiency|\(deficiency\))|surplus\s*/\s*\(deficiency\)|net asset value)")
    if ta is not None and tl is not None:
        calc = ta - tl
        if net is not None and abs(abs(net) - abs(calc)) > 1:
            out.append(_mk(L, doc, "LQ-22", "Net surplus/(deficiency) does not equal total assets less total liabilities", "High", f"{ta:,.0f} - {tl:,.0f} = {calc:,.0f} vs stated {net:,.0f}", f"{calc:,.0f}", f"{net:,.0f}"))
        if tl > ta:
            out.append(_mk(L, doc, "LQ-22", "Statement of Affairs shows a deficiency - company appears insolvent", "High", f"Liabilities {tl:,.0f} exceed assets {ta:,.0f}. Check the authority's rule for solvent voluntary liquidation / creditors' voluntary route before proceeding (grey area - confirm with the Partner).", "assets >= liabilities", f"deficiency {tl - ta:,.0f}"))
    else:
        out.append(_mk(L, doc, "LQ-22", "Total assets / total liabilities not found", "Medium", "Statement should show both totals", "totals", "not found"))
    liq = (inp.get("liquidator") or {}).get("name")
    if liq and not fuzzy_hits(t, liq, 0.88):
        out.append(_mk(L, doc, "LQ-22", "Liquidator not named in the Statement of Affairs", "Medium", f"'{liq}'", liq, "absent"))
    if not re.search(r"vat|duties and taxes|corporate tax|FTA", t, re.I):
        out.append(_mk(L, doc, "LQ-22", "No tax creditor (VAT / corporate tax) shown", "Medium", "Confirm no VAT/CT liability or accrue it; FTA is a creditor until deregistration", "tax liabilities considered", "none listed"))
    brd = D.get("board_resolution")
    if brd and ds and max(ds) < brd:
        out.append(_mk(L, doc, "LQ-22", "Statement of Affairs is dated before the Board Resolution", "Medium", f"{max(ds):%d %B %Y} < {brd:%d %B %Y}", f">= {brd.isoformat()}", max(ds).isoformat()))
    return out


# ------------------------------------------------------------------ LQ-23 Liquidator's report
SECTIONS = {"Assets realised / disposed": r"asset\w*[^.]{0,40}(realis|dispos|sold|transfer)|realisation of assets",
            "Liabilities settled / creditors paid": r"liabilit\w+[^.]{0,30}(settled|paid|discharged)|creditors?[^.]{0,20}(paid|settled)",
            "Distribution to shareholders / balance": r"distribut\w+|balance (paid|returned) to (the )?(shareholder|partner)",
            "Creditor notice / advertisement": r"advertis|newspaper|notice to creditors|creditor claims",
            "No claims / contingent liabilities statement": r"no (further )?(claims|contingent liabilit)|claims? (received|settled)",
            "VAT / CT deregistration status": r"deregist\w+",
            "Bank account closure": r"bank (account )?clos|closure of (the )?bank",
            "Custody of books and records": r"books? (and records|of account)|records (shall be|will be) (kept|maintained)"}


def lq23_report(inp, D, docs):
    _need(docs, "report")
    doc, t = docs.get("report")[0], docs.text("report")
    out, L = [], "Liquidator's report"
    if not fuzzy_hits(t, inp["company"], 0.88):
        out.append(_mk(L, doc, "LQ-23", "Company name not found in the Liquidator's report", "High", f"'{inp['company']}'", inp["company"], "absent"))
    for k, rx in SECTIONS.items():
        if not re.search(rx, t, re.I):
            out.append(_mk(L, doc, "LQ-23", f"Report does not address: {k}", "Medium", f"No wording matching '{k}'", k, "absent"))
    liq = (inp.get("liquidator") or {}).get("name")
    if liq and not fuzzy_hits(t, liq, 0.88):
        out.append(_mk(L, doc, "LQ-23", "Liquidator not named in the report", "Medium", f"'{liq}'", liq, "absent"))
    ds = _dates(t)
    sub = D.get("report_submitted") or D.get("report_issue_planned")
    if sub and ds and sub not in ds:
        out.append(_mk(L, doc, "LQ-23", "Report date in the tracker does not appear in the report", "Medium", f"Tracker {sub:%d %B %Y}; dates in report {sorted({d.isoformat() for d in ds})[:4]}", sub.isoformat(), ", ".join(sorted({d.isoformat() for d in ds})[:3])))
    ads = D.get("newspaper_ads") or []
    ads = ads if isinstance(ads, list) else [ads]
    miss = [a for a in ads if a and a not in ds]
    if ads and miss and re.search(r"advertis|newspaper", t, re.I):
        out.append(_mk(L, doc, "LQ-23", "Advertisement date(s) in the tracker not stated in the report", "Medium", "; ".join(f"{m:%d %B %Y}" for m in miss), "dates agree", "missing"))
    # figures versus the Statement of Affairs
    if docs.get("soa"):
        st = docs.text("soa")
        for lab, rx in (("Total assets", r"total assets"), ("Total liabilities", r"total liabilities")):
            a, b = _amount(st, rx), _amount(t, rx)
            if a is not None and b is not None and abs(a - b) > 1:
                out.append(_mk(L, doc, "LQ-23", f"{lab} in the report differ from the Statement of Affairs", "Medium", f"SOA {a:,.0f} vs report {b:,.0f}; explain movements (realisation gains/losses, costs)", f"{a:,.0f}", f"{b:,.0f}"))
    return out


# ------------------------------------------------------------------ LQ-24 TB
def lq24_tb(inp, D, docs):
    if docs.tb is None and not docs.get("tb_doc"):
        raise _NR("Upload the trial balance (optional) to run this check")
    out, L = [], "Trial balance"
    if docs.tb is not None:
        dr, cr = sum(r["debit"] for r in docs.tb), sum(r["credit"] for r in docs.tb)
        if abs(dr - cr) > 1:
            out.append(_mk(L, None, "LQ-24", "Trial balance does not balance", "High", f"Debits {dr:,.0f} vs credits {cr:,.0f}; difference {dr - cr:,.0f}", f"{dr:,.0f}", f"{cr:,.0f}"))
        cls = lambda k: sum(r["debit"] - r["credit"] for r in docs.tb if r["class"].startswith(k))
        assets, liab = cls("asset"), -cls("liab")
        if docs.get("soa"):
            st = docs.text("soa")
            for lab, v, rx in (("assets", assets, r"total assets"), ("liabilities", liab, r"total liabilities")):
                s = _amount(st, rx)
                if s is not None and v and abs(s - v) > max(1, 0.05 * abs(s)):
                    out.append(_mk(L, None, "LQ-24", f"TB {lab} differ from the Statement of Affairs by more than 5%", "Medium", f"TB {v:,.0f} vs SOA {s:,.0f}; explain (dates differ, adjustments, realisations)", f"{s:,.0f}", f"{v:,.0f}"))
        if docs.get("report"):
            rt = docs.text("report")
            s = _amount(rt, r"total assets")
            if s is not None and assets and abs(s - assets) > max(1, 0.05 * abs(s)):
                out.append(_mk(L, None, "LQ-24", "TB assets differ from the report by more than 5%", "Medium", f"TB {assets:,.0f} vs report {s:,.0f}", f"{s:,.0f}", f"{assets:,.0f}"))
    return out


# ------------------------------------------------------------------ LQ-25 CT / VAT registration
def lq25_registration(inp, D, docs):
    allroles = ["br", "soa", "report", "ctvat", "licence"]
    if not any(docs.get(r) for r in allroles):
        raise _NR("Upload the CT/VAT registration certificate or FTA letter (or the report/SOA) to check registration status")
    out = []
    ct_doc = ct_loc = None
    ct_trn, vat_trn, hits = set(), set(), []
    for r in allroles:
        for d in docs.get(r):
            tx = re.sub(r"[ \t]+", " ", d.all_text)
            for m in TRN.finditer(tx):
                ctx = tx[max(0, m.start() - 80): m.end() + 40].lower()
                kind = "ct" if re.search(r"corporate tax|\bCT\b", ctx, re.I) else "vat" if re.search(r"\bvat\b|value added|tax registration number|\btrn\b", ctx, re.I) else "tax"
                if kind == "ct":
                    ct_trn.add(m.group(1))
                else:
                    vat_trn.add(m.group(1))
                hits.append((r, kind, m.group(1), d))
    all_text = " ".join(docs.text(r) for r in allroles)
    ct_says = bool(re.search(r"corporate tax (registration|trn|number)|registered for corporate tax|CT registration", all_text, re.I))
    ct_registered = bool(ct_trn) or ct_says or bool(docs.get("ctvat") and re.search(r"corporate tax", docs.text("ctvat"), re.I))
    vat_registered = bool(vat_trn) or bool(re.search(r"registered for VAT|VAT registration|vat trn", all_text, re.I))
    rep = docs.get("report")[0] if docs.get("report") else None
    L = "CT/VAT registration"
    if not ct_registered:
        out.append(_mk(L, None, "LQ-25", "No evidence the company is registered for Corporate Tax", "High",
                       "No CT registration number / certificate in the documents. Confirm on EmaraTax. Late registration carries an administrative penalty (CD 75/2023 as amended - verify the current amount) and a deregistration cannot proceed without a registration.", "CT registration evidence", "none"))
    else:
        if not D.get("ct_dereg_initiated") and not (inp.get("nocs") or {}).get("ct_deregistration"):
            out.append(_mk(L, None, "LQ-25", "Registered for Corporate Tax but CT deregistration not initiated/recorded", "High", "Record the CT deregistration application date or the FTA NOC (tracker: dates.ct_dereg_initiated / NOCs).", "CT deregistration initiated", "blank"))
        if rep is not None and not re.search(r"corporate tax", docs.text("report"), re.I):
            out.append(_mk("Liquidator's report", rep, "LQ-25", "Liquidator's report does not mention Corporate Tax status", "Medium", "State CT registration, final return and deregistration status", "CT paragraph", "absent"))
        elif rep is not None and not re.search(r"(final|last) (corporate tax )?return|tax period|corporate tax return", docs.text("report"), re.I):
            out.append(_mk("Liquidator's report", rep, "LQ-25", "Final Corporate Tax return / tax period not addressed in the report", "Medium", "Check the final return is filed and tax paid before the deregistration is accepted", "final CT return", "not mentioned"))
    if vat_registered and not D.get("vat_dereg_initiated") and not (inp.get("nocs") or {}).get("vat_deregistration"):
        out.append(_mk(L, None, "LQ-25", "Registered for VAT but VAT deregistration not initiated/recorded", "High", "Record the VAT deregistration application date or NOC.", "VAT deregistration initiated", "blank"))
    trns = {x[2] for x in hits}
    if len(trns) > 3:
        out.append(_mk(L, None, "LQ-25", "Several different tax registration numbers appear", "Low", f"{sorted(trns)[:4]}", "one VAT and one CT TRN", f"{len(trns)} numbers"))
    return out


# ------------------------------------------------------------------ LQ-26 consistency across documents
def lq26_consistency(inp, D, docs):
    roles = [r for r in ("br", "soa", "report", "ctvat", "licence") if docs.get(r)]
    if len(roles) < 2:
        raise _NR("Upload at least two of: Board Resolution, Statement of Affairs, Liquidator's report, licence")
    out, name = [], inp["company"]
    for r in roles:
        for d in docs.get(r):
            tx = re.sub(r"\s+", " ", d.all_text)
            seen = set()
            for cand, ratio, _ in fuzzy_hits(tx, name, 0.8):
                if not same_name(cand, name) and cand not in seen:      # case / dash / spacing differences are not spelling errors
                    seen.add(cand)
                    out.append(_mk(DOC_ROLES[r], d, "LQ-26", "Company name spelt differently from the licence", "Medium", f"'{cand}' vs '{name}'", name, cand))
    liqs = {}
    for r in roles:
        for m in re.finditer(r"(?:liquidator|appointed)\s*[:\-]?\s*(?:Mr\.?|Ms\.?|Mrs\.?|Dr\.?)?\s*([A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){1,3})", docs.text(r)):
            liqs.setdefault(re.sub(r"\W", "", m.group(1).lower()), (m.group(1), r))
    if len(liqs) > 1:
        out.append(_mk("Documents", None, "LQ-26", "Liquidator's name differs between documents", "High", "; ".join(f"'{v[0]}' in {DOC_ROLES[v[1]]}" for v in list(liqs.values())[:3]), "one name", f"{len(liqs)} variants"))
    return out[:8]


REG = {"LQ-21": lq21_br, "LQ-22": lq22_soa, "LQ-23": lq23_report, "LQ-24": lq24_tb, "LQ-25": lq25_registration, "LQ-26": lq26_consistency}


def run_liq_docs(inp, params, paths):
    docs = Docs(paths)
    from .rules_liq import _d
    D = {k: (_d(v) if not isinstance(v, list) else [_d(x) for x in v]) for k, v in (inp.get("dates") or {}).items()}
    res = []
    for cid, fn in REG.items():
        try:
            f = fn(inp, D, docs)
            res.append(Result(cid, "EXC" if f else "PASS", f))
        except _NR as e:
            res.append(Result(cid, "NOTRUN", [], str(e)))
        except Exception as e:
            res.append(Result(cid, "NOTRUN", [], f"Could not run on this file: {type(e).__name__}: {str(e)[:120]}"))
    return res, docs
