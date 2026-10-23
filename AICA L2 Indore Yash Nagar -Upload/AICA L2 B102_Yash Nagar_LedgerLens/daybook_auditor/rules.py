"""Deterministic checks on a normalised Day Book. No AI involved: every finding here is
reproducible and traceable to a voucher.

Statutory references below are to the Income-tax Act, 1961 and CGST Act. For financial
years beginning on or after 1 April 2026 the Income-tax Act, 2025 renumbers these
provisions, so verify section numbers and thresholds before relying on them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .narration import benford_findings, narration_findings, repeated_findings, threshold_findings

FINDING_COLS = ["severity", "rule", "date", "vch_type", "vch_no", "voucher_id",
                "ledger", "amount", "detail", "reference", "source"]
SEVERITY_RANK = {"High": 0, "Medium": 1, "Low": 2}

R_CASH_PAY = "Cash payment above limit"
R_CASH_NEAR = "Cash payment just below limit"
R_CASH_RCPT = "Cash receipt above limit"
R_NEG_CASH = "Negative cash balance"
R_DUP = "Possible duplicate voucher"
R_IMBAL = "Debit not equal to credit"
R_GAP = "Voucher number gap"
R_PERIOD = "Date outside financial year"
R_UNDATED = "Dates hidden in the export"
R_SUNDAY = "Large entry on Sunday"
R_ROUND = "Round-sum entry"
R_NARR = "Missing narration"
R_SUSP = "Suspense / miscellaneous ledger"
R_TDS = "Possible TDS non-deduction"
R_GST = "GST ledger inconsistency"

REF = {
    R_CASH_PAY: "Sec 40A(3)/(3A) IT Act: cash payment above Rs 10,000 per person per day is disallowed",
    R_CASH_NEAR: "Sec 40A(3) IT Act: amounts just under the limit can indicate splitting",
    R_CASH_RCPT: "Sec 269ST IT Act: cash receipt of Rs 2 lakh or more from a person in a day is prohibited",
    R_NEG_CASH: "Cash book cannot be in credit; indicates unrecorded receipts or wrong dating",
    R_DUP: "Duplicate payment/recording risk",
    R_IMBAL: "Double-entry integrity",
    R_GAP: "Completeness of voucher series (SA 500 / internal control)",
    R_PERIOD: "Cut-off: transaction falls outside the period under review",
    R_UNDATED: "Tests that depend on the date (per-day cash totals, cut-off, weekends, negative cash) cannot be run on undated vouchers",
    R_SUNDAY: "Unusual-timing entry; verify supporting documents",
    R_ROUND: "Round-sum entries may be estimates or management journals; verify support",
    R_NARR: "Documentation: large entry without explanation",
    R_SUSP: "Suspense balances must be cleared and classified before finalisation",
    R_GST: "CGST Act: intra-state supply attracts CGST+SGST, inter-state attracts IGST, never both",
}

# (label, ledger-name pattern, per-voucher threshold in Rs, severity). Thresholds are
# the single-payment / annual limits as understood for FY 2025-26; adjust as the law changes.
DEFAULT_TDS_RULES = [
    ("194C Contractor/transport/advertising", r"contract|labou?r charges|job work|transport|freight|cartage|advertis|catering|security charges|housekeeping", 30_000, "Medium"),
    ("194J Professional/technical fees", r"professional|consultan|legal|audit fee|technical|software (dev|charges)|director.?s? (fee|sitting)", 50_000, "Medium"),
    ("194I Rent", r"\brent\b|\blease (rent|charges)", 50_000, "Medium"),
    ("194H Commission/brokerage", r"commission|brokerage", 20_000, "Medium"),
    ("194A Interest (other than bank)", r"interest (paid|on (loan|unsecured|deposit))|interest expense", 5_000, "Low"),
]

CASH = re.compile(r"^(?!.*(discount|credit)).*\bcash\b", re.I)
BANKISH = re.compile(r"bank|hdfc|icici|\bsbi\b|axis|kotak|\bpnb\b|\bcash\b", re.I)
TAXISH = re.compile(r"\b(tds|tcs|gst|igst|cgst|sgst|utgst)\b", re.I)
NON_PARTY = re.compile(r"\bsales?\b|income|revenue|interest received|discount", re.I)
SUSPENSE = re.compile(r"suspense|miscellaneous|\bmisc\b|difference|unallocated|clearing", re.I)
HARD_SUSPENSE = re.compile(r"suspense|difference|unallocated|clearing", re.I)
IGST = re.compile(r"\bigst\b|integrated", re.I)
CGST = re.compile(r"\bcgst\b|central (gst|tax)", re.I)
SGST = re.compile(r"\b[su]t?gst\b|state (gst|tax)", re.I)
TDS_LEDGER = re.compile(r"\btds\b|tax deducted", re.I)


@dataclass
class Config:
    fy_start: date
    fy_end: date
    cash_payment_limit: float = 10_000
    cash_receipt_limit: float = 200_000
    round_sum_min: float = 100_000
    weekend_min: float = 100_000
    narration_min: float = 25_000
    duplicate_days: int = 7
    duplicate_min: float = 5_000
    opening_cash: float = 0.0
    near_threshold_pct: float = 2.0       # "just below a limit" means within this % under it
    repeat_min: int = 3                   # same party, same amount, this many times ...
    repeat_days: int = 31                 # ... within this many days
    benford_min: int = 100                # fewest amounts for the first-digit test
    run_narration_tests: bool = True
    tds_rules: list = field(default_factory=lambda: list(DEFAULT_TDS_RULES))


def summarise_vouchers(df: pd.DataFrame) -> pd.DataFrame:
    """One row per voucher with its Dr/Cr lines as lists of (ledger, amount)."""
    out = []
    for vid, g in df.groupby("voucher_id", sort=False):
        first = g.iloc[0]
        dr, cr = g[g["side"] == "Dr"], g[g["side"] == "Cr"]
        out.append({
            "voucher_id": vid, "date": first["date"], "vch_type": first["vch_type"],
            "vch_no": first["vch_no"], "narration": first["narration"],
            "dr_total": dr["amount"].sum(), "cr_total": cr["amount"].sum(),
            "dr_lines": list(zip(dr["ledger"], dr["amount"])),
            "cr_lines": list(zip(cr["ledger"], cr["amount"])),
        })
    v = pd.DataFrame(out)
    v["total"] = v[["dr_total", "cr_total"]].max(axis=1)
    return v


def _mk(rule, sev, r, detail, ledger="", amount=None, ref=None):
    return {"severity": sev, "rule": rule, "date": r["date"], "vch_type": r["vch_type"],
            "vch_no": r["vch_no"], "voucher_id": r["voucher_id"], "ledger": ledger,
            "amount": r["total"] if amount is None else amount, "detail": detail,
            "reference": ref if ref is not None else REF.get(rule, ""), "source": "Rule"}


def _inr(x: float) -> str:
    return f"Rs {x:,.0f}"


def _fmt(d) -> str:
    return d.strftime("%d/%m/%Y") if hasattr(d, "strftime") and pd.notna(d) else "an undated day"


def _counterparty(lines, exclude_non_party=False):
    best = None
    for ledger, amt in lines:
        if BANKISH.search(ledger) or TAXISH.search(ledger):
            continue
        if exclude_non_party and NON_PARTY.search(ledger):
            continue
        if best is None or amt > best[1]:
            best = (ledger, amt)
    return best[0] if best else None


def _period(recs, cfg):
    out = []
    lo, hi = pd.Timestamp(cfg.fy_start), pd.Timestamp(cfg.fy_end)
    undated = [r for r in recs if pd.isna(r["date"])]
    if undated and len(undated) > 0.2 * len(recs):
        # A whole export with hidden dates (TallyPrime Educational Mode) is one finding, not hundreds.
        out.append(_mk(R_UNDATED, "Medium", undated[0],
                       f"The date is hidden on {len(undated)} of {len(recs)} vouchers (for example TallyPrime Educational "
                       "Mode writes 'Educational' for every date except the 1st, 2nd and 31st). Per-day cash totals, "
                       "cut-off, weekend and negative-cash tests were limited or skipped; the other tests ran on all vouchers. "
                       "Export from a licensed TallyPrime for full date analysis.", "", 0.0))
        undated = []
    for r in recs:
        if pd.isna(r["date"]):
            if r in undated:
                out.append(_mk(R_PERIOD, "High", r, "Voucher has no valid date."))
        elif not (lo <= r["date"] <= hi):
            out.append(_mk(R_PERIOD, "High", r, f"Dated {_fmt(r['date'])}, outside {_fmt(lo)} to {_fmt(hi)}."))
    return out


def _cash(recs, cfg):
    out, pay, rcpt = [], {}, {}
    for r in recs:
        if r["vch_type"].lower() == "contra":
            continue
        cash_cr = sum(a for l, a in r["cr_lines"] if CASH.search(l))
        cash_dr = sum(a for l, a in r["dr_lines"] if CASH.search(l))
        # an undated voucher cannot be grouped by day, so it is tested on its own
        day = r["date"] if pd.notna(r["date"]) else r["voucher_id"]
        if cash_cr > 0 and (p := _counterparty(r["dr_lines"])):
            pay.setdefault((day, p), []).append((r, cash_cr))
        if cash_dr > 0 and (p := _counterparty(r["cr_lines"], exclude_non_party=True)):
            rcpt.setdefault((day, p), []).append((r, cash_dr))

    for (d, party), items in pay.items():
        total = sum(a for _, a in items)
        if total > cfg.cash_payment_limit:
            nos = ", ".join(str(r["vch_no"]) for r, _ in items)
            detail = f"Cash paid to {party} on {_fmt(d)}: {_inr(total)} across {len(items)} voucher(s) [{nos}]."
            narr = " ".join(str(items[0][0]["narration"] or "").split())[:110]
            if len(items) == 1 and narr:
                detail += f' Narration: "{narr}"'
            out.append(_mk(R_CASH_PAY, "Medium" if total < 5 * cfg.cash_payment_limit else "High",
                           items[0][0], detail, party, total))
        else:
            for r, a in items:
                if a >= 0.9 * cfg.cash_payment_limit:
                    out.append(_mk(R_CASH_NEAR, "Low", r,
                                   f"Cash payment of {_inr(a)} to {party}, just under the {_inr(cfg.cash_payment_limit)} limit.",
                                   party, a))
    for (d, party), items in rcpt.items():
        total = sum(a for _, a in items)
        if total >= cfg.cash_receipt_limit:
            nos = ", ".join(str(r["vch_no"]) for r, _ in items)
            out.append(_mk(R_CASH_RCPT, "High", items[0][0],
                           f"Cash received from {party} on {_fmt(d)}: {_inr(total)} across {len(items)} voucher(s) [{nos}].",
                           party, total))
    return out


def _neg_cash(recs, cfg):
    net: dict = {}
    for r in recs:
        if pd.isna(r["date"]):
            continue
        dr = sum(a for l, a in r["dr_lines"] if CASH.search(l))
        cr = sum(a for l, a in r["cr_lines"] if CASH.search(l))
        if dr or cr:
            net[r["date"]] = net.get(r["date"], 0.0) + dr - cr
    bal, bad = cfg.opening_cash, []
    for d in sorted(net):
        bal += net[d]
        if bal < -0.5:
            bad.append((d, bal))
    if not bad:
        return []
    first = bad[0][0]
    r = next(x for x in recs if x["date"] == first and sum(a for l, a in x["cr_lines"] if CASH.search(l)) > 0)
    worst = min(bad, key=lambda t: t[1])
    detail = (f"Cash balance is negative at the close of {len(bad)} day(s), first on {_fmt(first)}; "
              f"lowest {_inr(worst[1])} on {_fmt(worst[0])} (assuming opening cash of {_inr(cfg.opening_cash)}).")
    return [_mk(R_NEG_CASH, "High", r, detail, "Cash", abs(worst[1]))]


def _duplicates(recs, cfg):
    sigs: dict = {}
    for r in recs:
        key = (r["vch_type"], tuple(sorted((l, round(a, 2)) for l, a in r["dr_lines"])),
               tuple(sorted((l, round(a, 2)) for l, a in r["cr_lines"])))
        sigs.setdefault(key, []).append(r)
    out = []
    for rs in sigs.values():
        rs = sorted((x for x in rs if pd.notna(x["date"])), key=lambda x: x["date"])
        for prev, cur in zip(rs, rs[1:]):
            if cur["total"] >= cfg.duplicate_min and (cur["date"] - prev["date"]).days <= cfg.duplicate_days:
                out.append(_mk(R_DUP, "High", cur,
                               f"Same ledgers and amounts as {cur['vch_type']} {prev['vch_no']} dated {_fmt(prev['date'])}."))
    return out


def _imbalance(recs):
    return [_mk(R_IMBAL, "High", r, f"Debits {_inr(r['dr_total'])} vs credits {_inr(r['cr_total'])}.",
                amount=abs(r["dr_total"] - r["cr_total"]))
            for r in recs if abs(r["dr_total"] - r["cr_total"]) > 0.5]


def _gaps(v):
    out = []
    d = v.copy()
    m = d["vch_no"].astype(str).str.extract(r"^(.*?)(\d+)\D*$")
    d["pfx"], d["num"] = m[0], pd.to_numeric(m[1], errors="coerce")
    d["_pos"] = range(len(d))
    d = d.dropna(subset=["num"])
    # With hidden dates the file order (chronological in a Tally export) is the only order there is.
    d = d.sort_values("_pos") if d["date"].isna().any() else d.sort_values(["date", "num"])
    for (vtype, pfx), g in d.groupby(["vch_type", "pfx"]):
        if len(g) < 5:
            continue
        seq = [int(x) for x in g["num"]]
        # A series that restarts (for example every month) repeats numbers; a continuous one never does.
        restarts = len(seq) != len(set(seq))
        missing, first_row, basis = [], None, ""
        if restarts:
            # Restarting series: numbers repeat, so a gap is a jump of up to 20 within one run.
            prev = None
            for rec in g.to_dict("records"):
                n = int(rec["num"])
                if prev is not None and 1 < n - prev <= 20:
                    missing += list(range(prev + 1, n))
                    first_row = first_row or rec
                prev = n
        else:
            # One continuous series, which may be entered out of date order (batches, back-dating): a gap is a number
            # between the lowest and highest that does not exist anywhere in the export.
            have = set(seq)
            if max(seq) - min(seq) > 5 * len(have):
                continue
            missing = [n for n in range(min(seq), max(seq) + 1) if n not in have]
            first_row = g.iloc[0].to_dict() if missing else None
            basis = f" (series {min(seq)} to {max(seq)})"
        if missing:
            out.append(_mk(R_GAP, "Low", first_row,
                           f"{len(missing)} number(s) missing in {vtype} series: {_ranges(missing, pfx)}{basis}. "
                           "Check for deleted or cancelled vouchers.", amount=0.0))
    return out


def _ranges(nums: list[int], prefix: str = "") -> str:
    """[9, 10, 11, 29] -> '9-11, 29'."""
    out, start, prev = [], None, None
    for n in sorted(set(nums)) + [None]:
        if start is None:
            start = n
        elif n is None or n != prev + 1:
            out.append(f"{prefix}{start}" if start == prev else f"{prefix}{start}-{prefix}{prev}")
            start = n
        prev = n
    return ", ".join(out)


def _simple_flags(recs, cfg):
    out = []
    for r in recs:
        t = r["vch_type"].lower()
        if pd.notna(r["date"]) and r["date"].weekday() == 6 and r["total"] >= cfg.weekend_min:
            out.append(_mk(R_SUNDAY, "Low", r, f"{_inr(r['total'])} posted on a Sunday ({_fmt(r['date'])})."))
        if t in ("payment", "journal") and r["total"] >= cfg.round_sum_min and r["total"] % 10_000 == 0:
            out.append(_mk(R_ROUND, "Low", r, f"Exact round amount of {_inr(r['total'])}."))
        if t in ("payment", "journal", "receipt") and not str(r["narration"]).strip() and r["total"] >= cfg.narration_min:
            out.append(_mk(R_NARR, "Medium" if t == "journal" else "Low", r,
                           f"{r['vch_type']} of {_inr(r['total'])} has no narration."))
        for ledger, amt in r["dr_lines"] + r["cr_lines"]:
            if SUSPENSE.search(ledger):
                # A true suspense ledger is a Medium flag; a "Miscellaneous ..." ledger is only worth a Low look.
                sev = "Medium" if HARD_SUSPENSE.search(ledger) else "Low"
                out.append(_mk(R_SUSP, sev, r, f"Ledger '{ledger}' used for {_inr(amt)}.", ledger, amt))
    return out


def _tds(recs, cfg):
    out = []
    for r in recs:
        if r["vch_type"].lower() not in ("payment", "journal", "purchase"):
            continue
        lines = r["dr_lines"] + r["cr_lines"]
        if any(TDS_LEDGER.search(l) for l, _ in lines):
            continue
        for ledger, amt in r["dr_lines"]:
            for label, pattern, threshold, sev in cfg.tds_rules:
                if amt >= threshold and re.search(pattern, ledger, re.I):
                    out.append(_mk(R_TDS, sev, r,
                                   f"{_inr(amt)} booked to '{ledger}' with no TDS ledger in the voucher. "
                                   f"Check Sec {label} (threshold {_inr(threshold)}).", ledger, amt))
                    break
    return out


def _gst(recs):
    out = []
    for r in recs:
        igst = cgst = sgst = 0.0
        for ledger, amt in r["dr_lines"] + r["cr_lines"]:
            if IGST.search(ledger):
                igst += amt
            elif CGST.search(ledger):
                cgst += amt
            elif SGST.search(ledger):
                sgst += amt
        if igst > 0 and (cgst > 0 or sgst > 0):
            out.append(_mk(R_GST, "High", r, "IGST and CGST/SGST both charged in the same voucher."))
        elif (cgst > 0) != (sgst > 0) or abs(cgst - sgst) > 1:
            out.append(_mk(R_GST, "Medium", r, f"CGST {_inr(cgst)} and SGST {_inr(sgst)} are not equal."))
    return out


def run_rules(df: pd.DataFrame, cfg: Config, ledger_level: bool = True) -> pd.DataFrame:
    v = summarise_vouchers(df)
    recs = v.to_dict("records")
    out = _period(recs, cfg) + _duplicates(recs, cfg) + _gaps(v)
    out += [f for f in _simple_flags(recs, cfg) if ledger_level or f["rule"] != R_SUSP]
    mostly_undated = v["date"].isna().mean() > 0.2
    if ledger_level:
        out += _cash(recs, cfg) + _imbalance(recs) + _tds(recs, cfg) + _gst(recs)
        if not mostly_undated:       # a cash balance built from the dated vouchers alone would be wrong
            out += _neg_cash(recs, cfg)
    # Tests that read narrations and the shape of amounts work on any export, condensed or detailed.
    if cfg.run_narration_tests:
        out += narration_findings(recs, cfg, ledger_level, _mk) + threshold_findings(recs, cfg, _mk)
        out += repeated_findings(recs, cfg, _mk) + benford_findings(recs, cfg, _mk)
    res = pd.DataFrame(out, columns=FINDING_COLS)
    if res.empty:
        return res
    res["_rank"] = res["severity"].map(SEVERITY_RANK)
    return res.sort_values(["_rank", "date"], kind="stable").drop(columns="_rank").reset_index(drop=True)
