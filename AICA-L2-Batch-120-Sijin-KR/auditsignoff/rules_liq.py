"""Module B - liquidation clock and checklist tracker. Rules and clocks come from rules/params.yaml and the firm's liquidation workbook."""
from __future__ import annotations
from datetime import date, timedelta
from calendar import monthrange

from .models import Finding, Result


def add_business_days(start: date, n: int, params) -> date:
    hol = {h if isinstance(h, date) else date.fromisoformat(str(h)) for h in params.get("holidays", [])}
    wk = set(params.get("weekend", [5, 6]))
    d, k = start, 0
    while k < n:
        d += timedelta(days=1)
        if d.weekday() not in wk and d not in hol:
            k += 1
    return d


def add_months(d: date, m: int) -> date:
    y, mo = divmod(d.month - 1 + m, 12)
    y, mo = d.year + y, mo + 1
    return date(y, mo, min(d.day, monthrange(y, mo)[1]))


def _d(v):
    if v is None or v == "":
        return None
    return v if isinstance(v, date) else date.fromisoformat(str(v))


class Tracker:
    def __init__(self, inp, params, today):
        self.i, self.p, self.today = inp, params, today
        self.dates = {k: (_d(v) if not isinstance(v, list) else [_d(x) for x in v]) for k, v in (inp.get("dates") or {}).items()}
        self.findings, self.milestones = [], []

    def ms(self, check, name, basis, due, actual, sev="High", kind="deadline"):
        """Assess one clock. kind='deadline': actual must be <= due. kind='earliest': actual must be >= due."""
        status, f = "PENDING", None
        if due is None:
            status = "n/a"
        elif kind == "deadline":
            if actual:
                if actual <= due:
                    status = "OK"
                else:
                    status = "LATE"
                    f = f"Actioned {actual.isoformat()}, {(actual - due).days} day(s) after the due date {due.isoformat()}"
            else:
                if self.today > due:
                    status = "OVERDUE"
                    f = f"Due {due.isoformat()}; {(self.today - due).days} day(s) overdue as at {self.today.isoformat()} and not recorded as done"
                elif (due - self.today).days <= 7:
                    status = "DUE SOON"
                    f = f"Due {due.isoformat()} - {(due - self.today).days} day(s) left"
                    sev = "Medium"
        else:  # earliest
            if actual:
                if actual >= due:
                    status = "OK"
                else:
                    status = "TOO EARLY"
                    f = f"Report dated/planned {actual.isoformat()} is {(due - actual).days} day(s) before the earliest permitted date {due.isoformat()}"
            else:
                status = "PENDING"
        self.milestones.append({"check": check, "milestone": name, "basis": basis,
                                "due": due.isoformat() if due else "", "actual": actual.isoformat() if actual else "", "status": status})
        if f:
            self.findings.append(Finding(check, f"{name}: {status.lower()}", sev, f, basis, due.isoformat() if due else "", actual.isoformat() if actual else "-"))


def run_liq(inp, params, today=None):
    today = today or date.today()
    auth = str(inp["authority"]).lower()
    cfg = params["authorities"].get(auth)
    t = Tracker(inp, params, today)
    D = t.dates
    br, appt = D.get("board_resolution"), D.get("liquidator_appointment")
    planned = D.get("report_issue_planned")
    submitted = D.get("report_submitted")
    issue = submitted or planned

    notrun = {}
    if cfg is None:
        raise ValueError(f"Unknown authority '{auth}'. Known: {sorted(params['authorities'])}")
    if cfg.get("workflow_missing"):
        t.findings.append(Finding("LQ-01", f"No workflow for {auth.upper()} in the firm's liquidation workbook", "Medium",
                                  "Obtain and encode the authority checklist before relying on the clocks below.", "Liquidation workbook", "Authority workflow", "absent"))

    # LQ-01 / LQ-02 appointment
    b = inp.get("br") or {}
    if not br:
        t.findings.append(Finding("LQ-01", "Board Resolution date not recorded", "High", "Cannot start any clock", "Input", "Date of BR", "absent"))
    else:
        if b.get("filed_with_authority") is not True:
            t.findings.append(Finding("LQ-01", "Board Resolution not recorded as filed with the authority", "High", f"BR dated {br.isoformat()}", "BR", "Filed", "Not filed"))
        if b.get("liquidator_named_correctly") is not True:
            t.findings.append(Finding("LQ-01", "Liquidator not confirmed as correctly named in the Board Resolution", "High",
                                      "BR must name the firm (and the representing partner where the workbook requires it)", "BR", "Named", "Not confirmed"))
    if br and appt and appt < br:
        t.findings.append(Finding("LQ-02", "Liquidator appointment letter is dated before the Board Resolution", "High",
                                  f"Letter {appt.isoformat()} vs BR {br.isoformat()}", "Appointment letter", ">= BR date", appt.isoformat()))
    if not appt:
        t.findings.append(Finding("LQ-02", "Liquidator appointment letter date not recorded", "High", "FTA clock starts from this date", "Input", "Date", "absent"))

    # LQ-03 FTA notification
    if appt:
        due = add_business_days(appt, params["fta_notification_business_days"], params)
        t.ms("LQ-03", "FTA notification", f"{params['fta_notification_business_days']} business days from appointment letter (weekends{' and listed holidays' if params.get('holidays') else ' only - holiday list empty'} excluded)", due, D.get("fta_notified"))
    # LQ-04 VAT deregistration (internal rule)
    if br:
        due = br + timedelta(days=params["internal_vat_dereg_days_from_br"])
        t.ms("LQ-04", "VAT TRN deregistration initiated", f"{params['internal_vat_dereg_days_from_br']} days from BR (firm workbook rule)", due, D.get("vat_dereg_initiated"))
    # LQ-05 creditor block
    if cfg.get("creditor_block_days"):
        ads = [x for x in (D.get("newspaper_ads") or []) if x]
        if ads:
            earliest = max(ads) + timedelta(days=cfg["creditor_block_days"])
            t.ms("LQ-05", "Earliest report date after creditor block", f"{cfg['creditor_block_days']} days from last advertisement ({max(ads).isoformat()})", earliest, issue, kind="earliest")
        elif issue:
            t.findings.append(Finding("LQ-05", "Report planned/submitted but no newspaper advertisement recorded", "High",
                                      f"{auth.upper()} requires {cfg['creditor_block_days']}-day creditor block after advertisement", "Advertisement", "Ad dates", "absent"))
    # LQ-06 minimum gap
    if cfg.get("min_gap_days_br_to_report") and br:
        earliest = br + timedelta(days=cfg["min_gap_days_br_to_report"])
        if not (inp.get("partner_approval_short_gap")):
            t.ms("LQ-06", "Earliest report date (minimum gap from BR)", f"{cfg['min_gap_days_br_to_report']} days from BR unless Partner approves", earliest, issue, sev="Medium", kind="earliest")
    # LQ-07 one-year limit
    if cfg.get("max_months_to_report") and br:
        due = add_months(br, cfg["max_months_to_report"])
        t.ms("LQ-07", "Liquidation report submitted", f"Within {cfg['max_months_to_report']} months of BR", due, submitted)
    # LQ-08 expired licence
    if cfg.get("expired_licence_report_days") and D.get("trade_licence_expiry"):
        due = D["trade_licence_expiry"] + timedelta(days=cfg["expired_licence_report_days"])
        t.ms("LQ-08", "Report after licence expiry", f"{cfg['expired_licence_report_days']} days from licence expiry", due, submitted, sev="Medium")

    # clearances
    nocs = inp.get("nocs") or {}
    def pending(names):
        out = []
        for n in names:
            v = nocs.get(n)
            if v in (None, False, "") and str(v).lower() != "na":
                out.append(n)
        return out
    near = issue is not None and (issue - today).days <= 30
    pf, pl = pending(params["facility_nocs"]), pending(params["legal_nocs"])
    if pf:
        t.findings.append(Finding("LQ-10", "Facility NOCs outstanding", "Medium" if near else "Low", ", ".join(pf), "NOC tracker", "Obtained or NA", "Pending"))
    if pl:
        t.findings.append(Finding("LQ-11", "Legal NOCs / deregistrations outstanding", "High" if near else "Low", ", ".join(pl), "NOC tracker", "Obtained or NA", "Pending"))
    # banks
    pend_bank = []
    for bk in inp.get("bank_accounts") or []:
        miss = [k for k in ("no_liability_letter", "closure_letter") if not bk.get(k)]
        if miss:
            pend_bank.append(f"{bk.get('bank', '?')} ({bk.get('location', 'UAE')}): {', '.join(miss)}")
    if pend_bank:
        t.findings.append(Finding("LQ-13", "Bank letters outstanding", "Medium" if near else "Low", "; ".join(pend_bank), "Bank tracker", "All letters on file", "Pending"))
    # LQ-14 bank closure last
    bc = D.get("bank_closure")
    if bc and (pf or pl):
        t.findings.append(Finding("LQ-14", "Bank account closed while other clearances are still outstanding", "High",
                                  f"Closure {bc.isoformat()}; outstanding: {', '.join(pf + pl)}", "Tracker", "Bank closed last", bc.isoformat()))
    # LQ-19 mailbox reminder
    if submitted:
        t.milestones.append({"check": "LQ-19", "milestone": "Keep client mailbox active until", "basis": "1 year after completion",
                             "due": add_months(submitted, 12).isoformat(), "actual": "", "status": "REMINDER"})

    flagged = {f.check_id for f in t.findings}
    results = []
    impl = ["LQ-01", "LQ-02", "LQ-03", "LQ-04", "LQ-05", "LQ-06", "LQ-07", "LQ-08", "LQ-10", "LQ-11", "LQ-13", "LQ-14", "LQ-19"]
    for cid in impl:
        fl = [f for f in t.findings if f.check_id == cid]
        applicable = True
        note = ""
        if cid == "LQ-03" and not appt:
            applicable, note = False, "Appointment date missing"
        if cid in ("LQ-05",) and not cfg.get("creditor_block_days"):
            applicable, note = False, f"Not a {auth.upper()} requirement in firm workbook"
        if cid == "LQ-06" and not cfg.get("min_gap_days_br_to_report"):
            applicable, note = False, f"Not a {auth.upper()} requirement in firm workbook"
        if cid == "LQ-07" and not cfg.get("max_months_to_report"):
            applicable, note = False, f"Not a {auth.upper()} requirement in firm workbook"
        if cid == "LQ-08" and not (cfg.get("expired_licence_report_days") and D.get("trade_licence_expiry")):
            applicable, note = False, "Not applicable (authority rule or no expiry date)"
        if not applicable and not fl:
            results.append(Result(cid, "NOTRUN", [], note))
        else:
            results.append(Result(cid, "EXC" if fl else "PASS", fl))
    results += _answers(inp, auth, D, t)
    results.sort(key=lambda r: int(r.check_id.split("-")[1]))
    return results, t.milestones


def _yn(v):
    s = str(v or "").strip().lower()
    return True if s in ("yes", "y", "true") else False if s in ("no", "n", "false") else None


def _answers(inp, auth, D, t):
    """LQ-09, 12, 15, 16, 17, 18 from the tracker answers; blank = Not checked with the field to fill in."""
    g = lambda grp, k: (inp.get(grp) or {}).get(k)
    out = []

    def res(cid, fl, miss=None):
        if miss and not fl:
            out.append(Result(cid, "NOTRUN", [], "Fill in the tracker: " + ", ".join(miss)))
        else:
            out.append(Result(cid, "EXC" if fl else "PASS", fl))

    F = lambda cid, title, sev, det, loc, exp="", found="": Finding(cid, title, sev, det, loc, exp, found)
    # LQ-09
    fl, miss = [], []
    ai, dp = _yn(g("partners", "all_informed")), _yn(g("partners", "dispute"))
    if ai is None: miss.append("partners.all_informed")
    elif not ai: fl.append(F("LQ-09", "Not all partners are aware of the liquidation", "High", "Tracker answer: No", "Tracker - partners.all_informed", "Yes", "No"))
    if dp is None: miss.append("partners.dispute")
    elif dp: fl.append(F("LQ-09", "Legal dispute between partners", "High", "Tracker answer: Yes", "Tracker - partners.dispute", "No dispute", "Yes"))
    res("LQ-09", fl, miss)
    # LQ-12
    fl, miss = [], []
    for tax in ("vat", "ct"):
        r, pn = _yn(g(tax, "returns_filed_up_to_date")), _yn(g(tax, "penalties_outstanding"))
        if r is None: miss.append(f"{tax}.returns_filed_up_to_date")
        elif not r: fl.append(F("LQ-12", f"{tax.upper()} returns not filed up to date", "High", "Late filing must be cleared before deregistration", f"Tracker - {tax}.returns_filed_up_to_date", "Yes", "No"))
        if pn is None: miss.append(f"{tax}.penalties_outstanding")
        elif pn: fl.append(F("LQ-12", f"{tax.upper()} penalties outstanding", "High", "Settle administrative penalties before deregistration", f"Tracker - {tax}.penalties_outstanding", "No", "Yes"))
    res("LQ-12", fl, miss)
    # LQ-15
    fl, miss = [], []
    need = {"dmcc": ["physical_submission_done"], "difc": ["portal_balance_cleared", "psa_refund_cleared", "advert_one_file"]}.get(auth, ["advert_one_file"])
    for k in need:
        v = _yn(g("auth", k))
        if v is None: miss.append("auth." + k)
        elif not v: fl.append(F("LQ-15", f"{auth.upper()} condition not met: {k.replace('_', ' ')}", "High", "Authority-specific requirement per the firm workbook", f"Tracker - auth.{k}", "Yes", "No"))
    res("LQ-15", fl, miss)
    # LQ-16
    fl, miss = [], []
    for k, lab in (("built_from_tb", "Report not built from TB/GL/SOFP/income statement"), ("adjustments_posted", "Adjustments not posted before the report")):
        v = _yn(g("report", k))
        if v is None: miss.append("report." + k)
        elif not v: fl.append(F("LQ-16", lab, "High", "Tracker answer: No", f"Tracker - report.{k}", "Yes", "No"))
    res("LQ-16", fl, miss)
    # LQ-17
    fl, miss = [], []
    fd, fs, fr = D.get("fta_final_letter_date") or (inp.get("fta") or {}).get("final_letter_date"), str(g("fta", "final_letter_status") or "").strip().lower(), str(g("fta", "status_in_report") or "").strip().lower()
    if not fd and not fs:
        miss.append("fta.final_letter_date / fta.final_letter_status")
    else:
        if not fd: fl.append(F("LQ-17", "FTA final communication date not recorded", "High", "Attach the FTA final letter and record its date", "Tracker - fta.final_letter_date", "date", "blank"))
        if fs and fr and fs != fr: fl.append(F("LQ-17", "FTA status in the report differs from the FTA final communication", "High", f"FTA letter: {fs}; report: {fr}", "Tracker - fta.*", fs, fr))
        if fs and not fr: miss.append("fta.status_in_report")
    res("LQ-17", fl, miss)
    # LQ-18
    fl, miss = [], []
    oc, sp = _yn(g("legal", "open_claims")), _yn(g("legal", "settled_or_provided"))
    if oc is None: miss.append("legal.open_claims")
    elif oc and sp is None: miss.append("legal.settled_or_provided")
    elif oc and not sp: fl.append(F("LQ-18", "Legal claims/contingent liabilities are open and not settled or provided", "High", "Settle or provide before the report is issued", "Tracker - legal.*", "settled/provided", "open"))
    res("LQ-18", fl, miss)
    return out
