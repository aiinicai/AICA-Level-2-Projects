"""Module D - Corporate tax working sheet review.
The engine re-performs the computation from the INPUT cells of the firm CT working sheet, then compares it
with what the workbook itself says, with the return figures (any format) and with the TP/FS evidence."""
from __future__ import annotations
import re
import shutil
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path

from .models import Finding, Result
from .rules_fs import NotRun

S03, S04, S05, S06, S07, S08, S09 = ("03_INCOME_SCHEDULE", "04_ADJUSTMENTS", "05_CT_COMPUTATION", "06_INTEREST_CAP",
                                     "07_TP_SCHEDULE", "08_TAX_LOSSES", "09_TAX_LIABILITY")


def _num(v):
    if isinstance(v, bool) or v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return 0.0


def _date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(str(v).strip(), f).date()
        except (ValueError, TypeError):
            pass
    return None


def add_months(d: date, m: int) -> date:
    y, mo = divmod(d.month - 1 + m, 12)
    y += d.year
    mo += 1
    import calendar
    return date(y, mo, min(d.day, calendar.monthrange(y, mo)[1]))


def _recalc(path):
    """Copy of the workbook with values calculated by LibreOffice (only if installed). None if impossible."""
    from .legacy import _soffice
    exe = _soffice()
    if not exe:
        return None
    out = Path(tempfile.mkdtemp(prefix="ct_recalc_"))
    prof = tempfile.mkdtemp(prefix="lo_profile_")
    try:
        subprocess.run([exe, f"-env:UserInstallation={Path(prof).as_uri()}", "--headless", "--convert-to", "xlsx:Calc MS Excel 2007 XML",
                        "--outdir", str(out), str(path)], check=True, capture_output=True, timeout=240)
    except Exception:
        return None
    r = out / Path(path).name
    return r if r.exists() else None


class CT:
    """Reads the working sheet: inputs (constants) for re-performance, cached values for 'what the workbook says'."""

    def __init__(self, path, params, return_pairs=None, tp_report_adj=None, filing_date=None, fs_profit=None):
        import openpyxl
        from .legacy import ensure_modern
        path = ensure_modern(path)
        self.p, self.path = params["ct"], Path(path)
        self.wf = openpyxl.load_workbook(str(path))
        self.wv = openpyxl.load_workbook(str(path), data_only=True)
        self.calculated = True
        probe = self.wv[S05]["H62"].value if S05 in self.wv.sheetnames else None
        if probe is None:                                    # never opened in Excel -> try to calculate it
            rc = _recalc(path)
            if rc:
                self.wv = openpyxl.load_workbook(str(rc), data_only=True)
                probe = self.wv[S05]["H62"].value
            self.calculated = probe is not None
        self.ret = return_pairs or {}
        self.tp_report_adj, self.filing_date, self.fs_profit = tp_report_adj, filing_date, fs_profit
        for s in (S03, S04, S05, S07, S09):
            if s not in self.wf.sheetnames:
                raise ValueError(f"Sheet '{s}' not found: this is not an firm CT working sheet.")
        self._compute()

    # inputs (as typed) and cached values
    def inp(self, sheet, cell):
        v = self.wf[sheet][cell].value
        if isinstance(v, str) and v.startswith("="):          # formula cell: use calculated value if we have it
            v = self.wv[sheet][cell].value
        return v

    def cached(self, sheet, cell):
        v = self.wv[sheet][cell].value
        return None if v is None else _num(v)

    def n(self, sheet, cell):
        return _num(self.inp(sheet, cell))

    def _compute(self):
        n, P = self.n, self.p
        self.rev = n(S03, "D9")
        self.profit = n(S03, "D9") - n(S03, "D10") - sum(n(S03, f"D{r}") for r in range(12, 22)) + n(S03, "D22")
        self.exempt_raw = [n(S04, f"D{r}") for r in range(9, 14)]
        self.exempt = sum(abs(x) for x in self.exempt_raw)
        self.reliefs = self.cached("22_BUSINESS_RESTRUCTURING", "D58") or 0.0 if "22_BUSINESS_RESTRUCTURING" in self.wf.sheetnames else 0.0
        # interest cap (Art. 30)
        int_inc, int_exp = abs(n(S03, "D14")), n(S03, "D15")
        self.nie = int_exp - int_inc
        ebitda = self.profit + self.nie + n(S03, "D13") + n("06_INTEREST_CAP", "D14")
        self.int_cap = max(ebitda * P["interest_cap_pct"], P["interest_safe_harbour"])
        self.int_disallow = max(self.nie - self.int_cap, 0.0)
        # TP: direction per row (column K) else the default direction of each category; adjustment is upward only
        self.has_direction = str(self.wf[S07]["K7"].value or "").lower().startswith("direction")
        dflt = {8: "Income", 9: "Expense", 10: "Expense", 11: "Income", 12: "Expense", 13: "Income"}
        self.tp_rows = []
        for r in range(8, 16):
            val, al = n(S07, f"D{r}"), self.inp(S07, f"I{r}")
            d = str(self.inp(S07, f"K{r}") or "").strip().title() if self.has_direction else dflt.get(r, "")
            self.tp_rows.append((r, self.wf[S07][f"B{r}"].value, val, al, d))
        self.tp_adj = 0.0
        for r, _, val, al, d in self.tp_rows:
            if val and al not in (None, "") and d:
                self.tp_adj += max(_num(al) - val, 0) if d == "Income" else max(val - _num(al), 0)
        self.conn = self.cached(S04, "D30") or 0.0
        rows = [n(S04, f"D{r}") for r in range(16, 30)]
        nd_other = sum(rows) - n(S04, "D17") - n(S04, "D28")            # B2 and B13 replaced by independently computed values
        self.nd = nd_other + self.int_disallow + self.tp_adj + self.conn
        self.other_adj = n(S04, "D33") + n(S04, "D34")
        self.ti_before_losses = self.profit - self.exempt - self.reliefs + self.nd + self.other_adj
        avail = n(S08, "D8") + n(S08, "D10") - n(S08, "D12") + n(S08, "D9")
        self.loss_cap = max(self.ti_before_losses * P["loss_cap"], 0.0)
        self.losses_used = min(self.loss_cap, avail)
        self.ti = self.ti_before_losses - self.losses_used
        self.gross_ct = max(self.ti - P["zero_band"], 0.0) * P["rate"]
        self.credits = sum(n(S09, f"D{r}") for r in (9, 10, 11))
        self.payable = max(self.gross_ct - self.credits, 0.0)
        self.sbr = str(self.inp("02_ELECTIONS", "D8") or "").strip().upper() == "YES" if "02_ELECTIONS" in self.wf.sheetnames else False
        self.period_end = _date(self.inp("01_CLIENT_INFO", "C9")) or _date(self.inp("01_CLIENT_INFO", "D9"))


def _ex(cid, title, sev, detail, loc, exp="", found=""):
    return Finding(cid, title, sev, detail, loc, str(exp), str(found))


def _f(x):
    return f"{x:,.0f}"


# ------------------------------------------------------------------ CT-01
def ct01_recompute(c: CT):
    if not c.calculated:
        raise NotRun("Workbook has no calculated values: open it in Excel, save, and upload again (or install LibreOffice)")
    out, tol = [], c.p["tolerance"]
    for label, cell, mine in (("Taxable income before losses", "H42", c.ti_before_losses), ("Taxable income", "H49", c.ti),
                              ("Gross CT (9% band)", "H54", c.gross_ct), ("CT payable", "H62", c.payable)):
        wb = c.cached(S05, cell)
        if wb is not None and abs(wb - mine) > tol:
            out.append(_ex("CT-01", f"{label} in the workbook differs from independent recomputation", "High",
                           f"Workbook {_f(wb)} vs recomputed {_f(mine)} (difference {_f(wb - mine)}). See CT-02/03 for likely causes.",
                           f"{S05}!{cell}", _f(mine), _f(wb)))
    return out


# ------------------------------------------------------------------ CT-02
def ct02_bridge(c: CT):
    out = []
    neg = [(i, v) for i, v in enumerate(c.exempt_raw) if v < 0]
    if neg and c.cached(S05, "H42") is not None:
        # sheet 04 tells the user to enter exempt income as NEGATIVE, sheet 05 then subtracts the 'Less' column
        g = [c.wf[S05][f"G{r}"].value for r in (11, 12, 13, 14)]
        if all(isinstance(x, str) and re.fullmatch(r"='04_ADJUSTMENTS'!D\d+", x) for x in g):          # plain link form; the newer form uses ABS()
            out.append(_ex("CT-02", "Exempt income sign error: negative entries are ADDED to taxable income", "High",
                           f"Sheet 04 says enter exempt income as negative; sheet 05 links it unsigned into the 'Less' column and H42 subtracts it, "
                           f"so exempt income of {_f(-sum(v for _, v in neg))} increases taxable income by that amount instead of reducing it.",
                           f"{S04}!D9:D13 -> {S05}!G11:G14 -> H42", "Deduction", "Addition"))
    if c.exempt_raw[4] != 0:
        g15 = c.wf[S05]["G15"].value
        if isinstance(g15, str) and "G11:G14" in g15 and "D13" not in g15:
            out.append(_ex("CT-02", "A5 Non-resident ships/aircraft income is not carried into the computation", "High",
                           f"A5 = {_f(c.exempt_raw[4])} on sheet 04 but sheet 05 G15 sums only A1-A4; cross-check CC3 will also fail.",
                           f"{S04}!D13 / {S05}!G15", "A1-A5", "A1-A4"))
    d14 = c.cached(S04, "D14")
    if d14 is not None and abs(abs(d14) - c.exempt) > c.p["tolerance"]:
        out.append(_ex("CT-02", "Exempt income total on sheet 04 does not equal the sum of its lines", "Medium",
                       f"{_f(d14)} vs {_f(c.exempt)}", f"{S04}!D14"))
    if abs(c.other_adj) > 0 and not str(c.wf[S04]["E34"].value or "").strip():
        out.append(_ex("CT-02", "Other adjustments entered without a law reference/support", "Medium", _f(c.other_adj), f"{S04}!E33:E34"))
    return out


# ------------------------------------------------------------------ CT-03
def ct03_tp(c: CT):
    out = []
    blank = [(r, name, v) for r, name, v, al, d in c.tp_rows if v > 0 and al in (None, "")]
    for r, name, v in blank:
        if c.has_direction:
            out.append(_ex("CT-03", "Related-party transaction with no arm's length value: adjustment taken as nil", "Medium",
                           f"{name}: value {_f(v)}. Enter the arm's length value or keep the TP benchmarking/documentation that supports a nil adjustment (Art. 34-35).",
                           f"{S07}!I{r}", "Arm's length value or evidence", "blank"))
        else:
            out.append(_ex("CT-03", "TP arm's length value left blank: workbook adds back the FULL transaction value", "High",
                           f"{name}: value {_f(v)} with no arm's length value; sheet 07 J = D - I returns {_f(v)} as the adjustment.",
                           f"{S07}!I{r}", "Arm's length value entered (or nil adjustment evidenced)", "blank"))
    if c.has_direction:
        for r, name, v, al, d in c.tp_rows:
            if v > 0 and not d:
                out.append(_ex("CT-03", "Transaction direction (Income/Expense) not selected", "Medium", name, f"{S07}!K{r}", "Income or Expense", "blank"))
    wb_adj = c.cached(S07, "D18")
    if wb_adj is not None and abs(wb_adj - c.tp_adj) > c.p["tolerance"] and not (blank and not c.has_direction):
        out.append(_ex("CT-03", "TP adjustment in sheet 07 differs from recomputation (upward adjustments only, direction-aware)", "Medium",
                       f"Workbook {_f(wb_adj)} vs recomputed {_f(c.tp_adj)}.",
                       f"{S07}!D18", _f(c.tp_adj), _f(wb_adj)))
    if c.tp_report_adj is not None and abs(c.tp_report_adj - c.tp_adj) > c.p["tolerance"]:
        out.append(_ex("CT-03", "TP adjustment in the TP report does not agree to the CT computation", "High",
                       f"TP report {_f(c.tp_report_adj)} vs CT working {_f(c.tp_adj)}", f"{S07}!D18", _f(c.tp_report_adj), _f(c.tp_adj)))
    return out


# ------------------------------------------------------------------ CT-04
def ct04_other(c: CT):
    out, tol, n = [], c.p["tolerance"], c.n
    ent_exp = n(S03, "D18")
    want = round(ent_exp * (1 - c.p["entertainment_deductible"]), 2)
    if abs(n(S04, "D16") - want) > tol and ent_exp:
        out.append(_ex("CT-04", "Entertainment add-back is not 50% of the P&L entertainment expense", "Medium",
                       f"P&L {_f(ent_exp)} -> disallow {_f(want)}; sheet 04 B1 shows {_f(n(S04, 'D16'))}", f"{S04}!D16", _f(want), _f(n(S04, "D16"))))
    fines = n(S03, "D19")
    if fines and abs(n(S04, "D19") - fines) > tol:
        out.append(_ex("CT-04", "Fines & penalties add-back differs from the P&L amount (non-deductible in full)", "Medium",
                       f"P&L {_f(fines)} vs B4 {_f(n(S04, 'D19'))}", f"{S04}!D19", _f(fines), _f(n(S04, "D19"))))
    don = n(S03, "D20")
    if n(S04, "D25") > don + tol:
        out.append(_ex("CT-04", "Non-QPBE donation add-back exceeds donations in the P&L", "Medium",
                       f"B10 {_f(n(S04, 'D25'))} > P&L {_f(don)}", f"{S04}!D25"))
    wb_int = c.cached(S04, "D17")
    if abs(n(S04, "D17") - c.int_disallow) > tol:
        out.append(_ex("CT-04", "Interest add-back (B2) differs from the Art. 30 recomputation", "High",
                       f"Sheet 04 B2 {_f(n(S04, 'D17'))} vs recomputed {_f(c.int_disallow)} (NIE {_f(c.nie)}, cap {_f(c.int_cap)} = higher of 30% EBITDA and AED 12M)",
                       f"{S04}!D17 / 06_INTEREST_CAP", _f(c.int_disallow), _f(n(S04, "D17"))))
    inc06, exp06 = abs(n("06_INTEREST_CAP", "D8")), n("06_INTEREST_CAP", "D9")
    if abs(inc06 - abs(n(S03, "D14"))) > tol or abs(exp06 - n(S03, "D15")) > tol:
        out.append(_ex("CT-04", "Interest income/expense on sheet 06 does not agree to the P&L on sheet 03", "Medium",
                       f"Sheet 06: income {_f(inc06)}, expense {_f(exp06)}; sheet 03: {_f(abs(n(S03, 'D14')))}, {_f(n(S03, 'D15'))}", "06_INTEREST_CAP!D8:D9"))
    return out


# ------------------------------------------------------------------ CT-05 / CT-06 : return tie-out
RET_LABELS = {
    "profit": r"accounting (profit|income)|net profit|profit (before|per)|profit or loss",
    "exempt": r"exempt income|total exempt",
    "ti": r"^taxable income(?! before)|taxable income \(|taxable income$|total taxable income",
    "losses": r"tax loss(es)? (utili[sz]ed|used|claimed)|losses utili[sz]ed",
    "payable": r"corporate tax payable|tax payable|corporate tax liability|ct payable|tax due",
    "rp_total": r"related part(y|ies).*(total|aggregate|value)|total.*related part",
}


def _ret_val(c: CT, key):
    rx = re.compile(RET_LABELS[key], re.I)
    for lab, v in c.ret.items():
        if rx.search(lab):
            from .loaders import parse_number
            x = parse_number(str(v))
            if x is not None:
                return lab, x
    return None


def ct05_return(c: CT):
    if not c.ret:
        raise NotRun("EmaraTax return figures not supplied")
    out, tol = [], c.p["tolerance"]
    pairs = [("profit", "Accounting profit", c.profit), ("exempt", "Exempt income", c.exempt), ("ti", "Taxable income", c.ti),
             ("losses", "Tax losses utilised", c.losses_used), ("payable", "Corporate tax payable", c.payable)]
    seen = 0
    for key, name, mine in pairs:
        r = _ret_val(c, key)
        if r is None:
            continue
        seen += 1
        if abs(abs(r[1]) - abs(mine)) > tol:
            out.append(_ex("CT-05", f"{name} in the return differs from the CT working", "High",
                           f"Return '{r[0]}' {_f(r[1])} vs recomputed working {_f(mine)}", "EmaraTax return", _f(mine), _f(r[1])))
    if not seen:
        raise NotRun("No recognisable figure labels in the return file (Accounting profit, Taxable income, Corporate tax payable ...)")
    if c.fs_profit is not None and abs(c.fs_profit - c.profit) > tol:
        out.append(_ex("CT-05", "Accounting profit in the CT working differs from the audited FS", "High",
                       f"FS {_f(c.fs_profit)} vs working {_f(c.profit)}", f"{S03}!D23", _f(c.fs_profit), _f(c.profit)))
    return out


def ct06_rp(c: CT):
    d = c.p["tp_disclosure"]
    total = sum(v for _, _, v, _, _ in c.tp_rows)
    out = []
    r = _ret_val(c, "rp_total") if c.ret else None
    if r and abs(r[1] - total) > c.p["tolerance"]:
        out.append(_ex("CT-06", "Related-party transaction total in the return differs from sheet 07", "High",
                       f"Return {_f(r[1])} vs sheet 07 {_f(total)}", "EmaraTax return / " + S07, _f(total), _f(r[1])))
    if not r and not c.ret:
        raise NotRun("EmaraTax return figures not supplied")
    if total > d["aggregate"] or any(v > d["category"] for _, _, v, _, _ in c.tp_rows):
        pass        # threshold status is shown on sheet 07; disclosure itself is tested in the TP module (TP-71)
    return out


# ------------------------------------------------------------------ CT-07 deadlines
def ct07_deadlines(c: CT):
    if not c.period_end:
        raise NotRun("Tax period end (01_CLIENT_INFO) is blank")
    due = add_months(c.period_end, c.p["return_months"])
    out = []
    wb_due = _date(c.inp(S09, "D15")) or _date(c.inp("01_CLIENT_INFO", "C10"))
    if wb_due and wb_due != due:
        out.append(_ex("CT-07", "Return due date in the workbook is not period end + 9 months", "High",
                       f"Period end {c.period_end:%d %b %Y} -> due {due:%d %b %Y}; workbook shows {wb_due:%d %b %Y}", f"{S09}!D15", f"{due:%d-%b-%Y}", f"{wb_due:%d-%b-%Y}"))
    fd = c.filing_date or _date(c.inp(S09, "D16"))
    if fd and fd > due:
        m = (fd.year - due.year) * 12 + fd.month - due.month + (1 if fd.day > due.day else 0)
        pen = min(m, 12) * c.p["late_filing"]["first12_per_month"] + max(m - 12, 0) * c.p["late_filing"]["after_12_per_month"]
        out.append(_ex("CT-07", "Return filed after the due date: late filing penalty", "High",
                       f"Filed {fd:%d %b %Y}, due {due:%d %b %Y}: {m} month(s) or part -> AED {pen:,.0f} (CD 75/2023 as amended). "
                       f"Late payment of AED {c.payable:,.0f} also accrues 14% p.a. monthly if unpaid.", f"{S09}!D16", f"{due:%d-%b-%Y}", f"{fd:%d-%b-%Y}"))
    return out


# ------------------------------------------------------------------ CT-08 / 09 / 10 (rule-based flags; judgement stays with the reviewer)
def ct08_relief(c: CT):
    out = []
    n06 = c.n("06_INTEREST_CAP", "D19")
    if c.cached("05_CT_COMPUTATION", "G47") is not None and c.cached("05_CT_COMPUTATION", "G47") > c.loss_cap + c.p["tolerance"]:
        out.append(_ex("CT-08", "Tax losses utilised exceed the 75% cap", "High",
                       f"Utilised {_f(c.cached(S05, 'G47'))} > cap {_f(c.loss_cap)}", f"{S05}!G47", _f(c.loss_cap), _f(c.cached(S05, "G47"))))
    if any(c.exempt_raw[1:3]) and not str(c.wf["12_AUDIT_WP"]["G12"].value or "").upper().count("REVIEWED"):
        out.append(_ex("CT-08", "Participation exemption claimed but working paper WP/CT/03 is not signed off", "Medium",
                       "A2/A3 > 0: confirm >=5% holding, 12 months, >=9% CT in the investee's jurisdiction, <50% passive (Art. 23 / MD 302/2024).", "12_AUDIT_WP!G12"))
    return out


def ct09_qfzp(c: CT):
    if "10_FREE_ZONE" not in c.wf.sheetnames:
        raise NotRun("Sheet 10_FREE_ZONE not present")
    n, P = c.n, c.p["de_minimis"]
    rev, qual = n("10_FREE_ZONE", "D8") or c.rev, n("10_FREE_ZONE", "D9")
    if not rev and not qual:
        raise NotRun("Free zone sheet not completed (not a QFZP engagement?)")
    non_q = max(rev - qual, 0)
    limit = min(P["abs"], rev * P["pct"])
    out = []
    ok = str(c.inp("14_QFZP_ELIGIBILITY", "D17") or "").strip().upper()
    if non_q > limit and ok != "NO":
        out.append(_ex("CT-09", "De minimis test fails but QFZP status is still claimed", "High",
                       f"Non-qualifying revenue {_f(non_q)} > lower of AED 5M and 5% of revenue ({_f(limit)}). QFZP status is lost for the period and 9% applies to all taxable income.",
                       "10_FREE_ZONE / 14_QFZP_ELIGIBILITY C10", _f(limit), _f(non_q)))
    if abs(rev - c.rev) > c.p["tolerance"] and c.rev:
        out.append(_ex("CT-09", "Free zone sheet revenue differs from the P&L revenue", "Medium", f"{_f(rev)} vs {_f(c.rev)}", "10_FREE_ZONE!D8"))
    return out


def ct10_elections(c: CT):
    out, sb = [], c.p["sbr"]
    if c.sbr:
        if c.rev > sb["revenue_limit"]:
            out.append(_ex("CT-10", "Small Business Relief elected but revenue exceeds AED 3M", "High", f"Revenue {_f(c.rev)}", "02_ELECTIONS!D8", _f(sb["revenue_limit"]), _f(c.rev)))
        if c.period_end and c.period_end > _date(sb["last_period_end"]):
            out.append(_ex("CT-10", "Small Business Relief claimed for a period ending after 31 Dec 2029", "High", f"Period end {c.period_end:%d %b %Y}", "02_ELECTIONS!D8"))
        mne = str(c.inp("01_CLIENT_INFO", "C29") or "").strip().lower()
        qf = str(c.inp("01_CLIENT_INFO", "C31") or "").strip().lower()
        if mne.startswith("y") or qf.startswith("y"):
            out.append(_ex("CT-10", "SBR is not available to MNE-group members or Qualifying Free Zone Persons", "High", f"MNE member: {mne or '-'}; QFZP: {qf or '-'}", "01_CLIENT_INFO!C29/C31"))
    return out


REGISTRY = {"CT-01": ct01_recompute, "CT-02": ct02_bridge, "CT-03": ct03_tp, "CT-04": ct04_other, "CT-05": ct05_return, "CT-06": ct06_rp,
            "CT-07": ct07_deadlines, "CT-08": ct08_relief, "CT-09": ct09_qfzp, "CT-10": ct10_elections}


def run_ct(ct_path, params, return_pairs=None, tp_report_adj=None, filing_date=None, fs_profit=None):
    c = CT(ct_path, params, return_pairs, tp_report_adj, filing_date, fs_profit)
    results = []
    for cid, fn in REGISTRY.items():
        try:
            f = fn(c)
            results.append(Result(cid, "EXC" if f else "PASS", f))
        except NotRun as e:
            results.append(Result(cid, "NOTRUN", [], str(e)))
    return results, c
