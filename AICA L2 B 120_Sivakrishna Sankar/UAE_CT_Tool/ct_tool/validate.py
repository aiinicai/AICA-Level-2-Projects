"""Reconciliation and data-quality checks. Each check returns PASS / FAIL / WARN / INFO and a
plain-English detail. Nothing is forced to reconcile: where two files have different scopes the
difference is reported, not removed."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from .models import TrialBalance, GeneralLedger, MATCH_TOL


@dataclass
class Check:
    id: str
    description: str
    status: str            # PASS | FAIL | WARN | INFO
    detail: str = ""
    values: dict = field(default_factory=dict)


def _fmt(x: float) -> str:
    return f"{(0.0 if abs(x) < 0.005 else x):,.2f}"


def check_tb(tb: TrialBalance) -> list:
    out = []
    n = len(tb.accounts)
    out.append(Check("TB-01", "Accounts extracted", "PASS" if n else "FAIL", f"{n} account(s) read from {tb.source_file}"))
    td, tc = sum(a.debit for a in tb.accounts), sum(a.credit for a in tb.accounts)
    net = sum(a.net for a in tb.accounts)
    if abs(net) <= MATCH_TOL:
        out.append(Check("TB-02", "TB debits equal credits", "PASS",
                         f"Debits {_fmt(td)} / credits {_fmt(tc)} / net {_fmt(net)} ({tb.currency or 'source currency'})",
                         {"debit": td, "credit": tc, "net": net}))
    else:
        out.append(Check("TB-02", "TB debits equal credits", "FAIL",
                         f"TB does not balance: net {_fmt(net)} ({tb.currency or 'source currency'}). Check for missing accounts, "
                         "wrong signs, or an incomplete extraction.", {"debit": td, "credit": tc, "net": net}))
    codes = Counter(a.code for a in tb.accounts if a.code)
    dup_codes = [c for c, k in codes.items() if k > 1]
    names = Counter(a.name.strip().lower() for a in tb.accounts)
    dup_names = [c for c, k in names.items() if k > 1]
    if dup_codes or dup_names:
        out.append(Check("TB-03", "Duplicate accounts", "WARN",
                         f"Duplicate account codes: {dup_codes[:5]}; duplicate names: {dup_names[:5]}. "
                         "Confirm they are not the same account listed twice."))
    else:
        out.append(Check("TB-03", "Duplicate accounts", "PASS", "No duplicate codes or names."))
    zero = [a.name for a in tb.accounts if abs(a.net) < 0.005]
    if zero:
        out.append(Check("TB-04", "Zero-balance accounts", "INFO", f"{len(zero)} account(s) have a nil balance."))
    odd = [a.name for a in tb.accounts if a.notes]
    if odd:
        out.append(Check("TB-05", "Accounts with extraction notes", "WARN", f"{len(odd)} account(s) carry notes: {odd[:5]}"))
    for w in tb.warnings:
        out.append(Check("TB-W", "Extraction warning", "WARN", w))
    if any(a.opening is not None for a in tb.accounts):
        bad = []
        for a in tb.accounts:
            if a.opening is not None and a.movement is not None:
                if abs(a.opening + a.movement - a.net) > MATCH_TOL:
                    bad.append(a.name)
            elif a.opening is not None and (a.debit or a.credit):
                if abs(a.opening + (a.debit - a.credit) - a.net) > MATCH_TOL and abs(a.opening - a.net) > MATCH_TOL:
                    bad.append(a.name)
        out.append(Check("TB-06", "Opening balance + movement = closing", "WARN" if bad else "PASS",
                         f"{len(bad)} account(s) do not roll forward: {bad[:5]}" if bad else "Opening balance and movements roll forward to closing."))
    return out


def check_mapping(mapped: list) -> list:
    out = []
    unm = [m.account.name for m in mapped if m.line == "UNMAPPED"]
    dflt = [m.account.name for m in mapped if m.method == "hint-default"]
    flagged = [m for m in mapped if m.flags and m.method != "unmapped"]
    out.append(Check("MAP-01", "Every account mapped", "FAIL" if unm else "PASS",
                     f"{len(unm)} unmapped: {unm[:6]}" if unm else "All accounts are mapped to a statement line."))
    out.append(Check("MAP-02", "Accounts mapped only by default classification", "WARN" if dflt else "PASS",
                     f"{len(dflt)} account(s) fell back to the generic line for their TB classification - review: {dflt[:6]}" if dflt
                     else "No account relied on the default line."))
    if flagged:
        out.append(Check("MAP-03", "Mapping consistency flags", "WARN",
                         f"{len(flagged)} account(s) have flags (conflicting classification or abnormal balance): "
                         + "; ".join(m.account.name for m in flagged[:6])))
    return out


def check_statements(st, tr) -> list:
    out = []
    unm = f" Unmapped accounts net {_fmt(st.unmapped_net)} AED are excluded - this explains the difference." \
        if st.unmapped_accounts and abs(abs(st.bs_difference) - abs(st.unmapped_net)) < 1 else ""
    out.append(Check("FS-01", "Balance sheet balances", "PASS" if abs(st.bs_difference) <= 0.5 else "FAIL",
                     f"Assets {_fmt(st.total_assets)} vs liabilities + equity {_fmt(st.total_liabilities + st.total_equity)} "
                     f"(difference {_fmt(st.bs_difference)} AED)." + unm))
    from .mapping import fs_lines
    meta = fs_lines()
    pl = [a for a in tr.accounts if meta.get(a.line, {}).get("statement") == "PL" and abs(a.net_aed) > 0.005]
    if not pl:
        out.append(Check("FS-04", "Income statement accounts present", "FAIL",
                         "The trial balance has no profit and loss account with a balance. It looks like a post-closing TB (the year's result already rolled into retained "
                         "earnings), so the computation would show nil profit and nil tax. Use the pre-closing trial balance (income and expense accounts open) for the period."))
    else:
        out.append(Check("FS-04", "Income statement accounts present", "PASS", f"{len(pl)} income / expense account(s) with a balance."))
    out.append(Check("FS-02", "AED trial balance totals", "INFO",
                     f"Sum of AED net balances before any translation difference: {_fmt(tr.total_net_aed)} AED"))
    if tr.diff_applicable:
        out.append(Check("FS-03", "Currency translation difference", "WARN",
                         f"Derived difference of AED {_fmt(tr.translation_diff)} shown in equity - needs approval.",
                         {"diff": tr.translation_diff}))
    for f in tr.flags:
        out.append(Check("FX-W", "Currency note", "WARN", f))
    return out


def _acct_key(code: str, name: str) -> str:
    return code if code else name.strip().lower()


def check_gl(gl: GeneralLedger, tb: TrialBalance, period_start: Optional[str], period_end: Optional[str]) -> list:
    out = []
    n = len(gl.lines)
    out.append(Check("GL-01", "GL lines extracted", "PASS" if n else "FAIL", f"{n} line(s) from {gl.source_file}"))
    if not n:
        return out
    td, tc = sum(l.debit for l in gl.lines), sum(l.credit for l in gl.lines)
    out.append(Check("GL-02", "GL debits equal credits", "PASS" if abs(td - tc) <= MATCH_TOL else "WARN",
                     f"Debits {_fmt(td)} / credits {_fmt(tc)}"
                     + ("" if abs(td - tc) <= MATCH_TOL else " - a GL that lists one side of each entry per account may legitimately not balance; check scope.")))
    dates = [l.date for l in gl.lines if l.date]
    if dates:
        lo, hi = min(dates), max(dates)
        msg = f"GL dates run from {lo} to {hi}."
        st = "INFO"
        if period_start and period_end:
            outside = [l for l in gl.lines if l.date and not (period_start <= l.date <= period_end)]
            if outside:
                st = "WARN"
                msg += f" {len(outside)} line(s) fall outside the tax period {period_start} to {period_end}."
            else:
                st = "PASS"
                msg += f" All within the tax period {period_start} to {period_end}."
            if lo > period_start or hi < period_end:
                st = "WARN"
                msg += " The GL does not cover the whole period - it may be incomplete."
        out.append(Check("GL-03", "GL period coverage", st, msg))
    # duplicates
    sig = Counter((l.date, l.account_code or l.account_name, round(l.debit, 2), round(l.credit, 2), l.reference, l.description) for l in gl.lines)
    dups = {k: v for k, v in sig.items() if v > 1 and (k[3] or k[4] or k[5])}
    out.append(Check("GL-04", "Possible duplicated transactions", "WARN" if dups else "PASS",
                     f"{sum(v - 1 for v in dups.values())} line(s) are identical to another line (same date, account, amount, reference and narration)."
                     if dups else "No identical duplicate lines found."))
    neg = [l for l in gl.lines if l.debit < 0 or l.credit < 0]
    both = [l for l in gl.lines if l.debit and l.credit]
    if both:
        out.append(Check("GL-05", "Lines with both debit and credit", "INFO", f"{len(both)} line(s) have both a debit and a credit amount."))
    # GL vs TB movement
    if tb and tb.accounts:
        tbm = {_acct_key(a.code, a.name): a for a in tb.accounts}
        glm = {}
        for l in gl.lines:
            if period_start and period_end and l.date and not (period_start <= l.date <= period_end):
                continue
            glm[_acct_key(l.account_code, l.account_name)] = glm.get(_acct_key(l.account_code, l.account_name), 0.0) + l.net
        # only compare P&L-type movement when TB has no opening column (closing == movement for nominal accounts)
        diffs, matched, missing_in_gl, missing_in_tb = [], 0, [], []
        for k, a in tbm.items():
            if k in glm:
                # the GL may hold the whole year including the opening balance (compare with closing) or only the movement (closing less opening)
                refs = [a.net] + ([a.net - a.opening] if a.opening is not None else [])
                if any(abs(glm[k] - ref) <= MATCH_TOL for ref in refs):
                    matched += 1
                else:
                    diffs.append((a.name, glm[k], refs[-1]))
            else:
                missing_in_gl.append(a.name)
        for k in glm:
            if k not in tbm:
                missing_in_tb.append(k)
        status = "PASS" if not diffs and not missing_in_tb else "WARN"
        det = f"{matched} account(s) agree; {len(diffs)} differ"
        if diffs:
            det += " (" + "; ".join(f"{n}: GL {_fmt(g)} vs TB {_fmt(t)}" for n, g, t in diffs[:4]) + ")"
        det += f"; {len(missing_in_gl)} TB account(s) have no GL lines"
        if missing_in_tb:
            det += f"; {len(missing_in_tb)} GL account(s) not in the TB: {missing_in_tb[:4]}"
        det += ". Balance-sheet accounts may differ legitimately when the TB includes opening balances the GL omits."
        out.append(Check("GL-06", "GL movement agrees to TB", status, det))
    for w in gl.warnings:
        out.append(Check("GL-W", "GL extraction warning", "WARN", w))
    return out


def summarise(checks: list) -> dict:
    c = Counter(x.status for x in checks)
    return {"PASS": c.get("PASS", 0), "FAIL": c.get("FAIL", 0), "WARN": c.get("WARN", 0), "INFO": c.get("INFO", 0)}
