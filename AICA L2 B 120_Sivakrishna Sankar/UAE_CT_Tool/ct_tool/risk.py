"""Risk-based review of the TB and GL.

Outputs RISK INDICATORS, not tax conclusions. An unusual or sensitive account is never described as
non-deductible or fraudulent - it is described as needing evidence. Where a category has a rule-based
adjustment (e.g. 50% of entertainment), the amount is carried as a PROPOSED figure only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from .fx import TranslationResult
from .mapping import fs_lines
from .models import GeneralLedger, TrialBalance, load_json

EXPENSE_CATS = ("ENT", "GIFT", "DON", "FINE", "PERS", "MISC", "PROF", "COMM", "REPAIR", "INT", "TAXN", "TAXF")
RISK_ORDER = {"Low": 1, "Medium": 2, "High": 3}
RISK_NAME = {1: "Low", 2: "Medium", 3: "High"}


@dataclass
class Flag:
    flag_id: str
    category: str
    category_label: str
    code: str
    name: str
    line: str
    amount_aed: float
    period: str
    reason: str
    tax_implication: str
    risk: str
    documents: list
    status: str                        # Risk indicator | Potential adjustment | Information required | Technical review required
    gl_refs: list = field(default_factory=list)
    adj_key: Optional[str] = None
    adj_pct: Optional[float] = None
    proposed_adjustment: Optional[float] = None
    mgmt_response: str = ""
    reviewer_conclusion: str = ""
    rule_ref: str = "NDE-01"


@dataclass
class TxnFlag:
    line_id: str
    date: Optional[str]
    code: str
    name: str
    amount_aed: float
    description: str
    counterparty: str
    reference: str
    tests: list
    risk: str


@dataclass
class RiskReview:
    flags: list
    txn_flags: list
    thresholds: dict
    notes: list = field(default_factory=list)


def _cfg():
    return load_json("risk_rules.json")


def _rate_risk(base: str, amount: float, th: dict) -> str:
    r = RISK_ORDER[base]
    if amount < th["materiality_aed"]:
        r -= 1
    elif amount >= th["high_aed"]:
        r += 1
    return RISK_NAME[max(1, min(3, r))]


def analyse(tr: TranslationResult, gl: Optional[GeneralLedger] = None, period_start: str = "", period_end: str = "",
            related_parties: Optional[list] = None, prior_tb: Optional[TrialBalance] = None,
            thresholds: Optional[dict] = None) -> RiskReview:
    cfg = _cfg()
    th = dict(cfg["thresholds"])
    th.update(thresholds or {})
    params = load_json("rules.json")["params"]
    lines = fs_lines()
    period = f"{period_start} to {period_end}" if period_start else ""
    cats = cfg["categories"]
    for c in cats:
        c["_re"] = re.compile(c["pattern"], re.I)
    flags, notes = [], []
    gl_by_acct = {}
    acct_rate, acct_stmt = {}, {}
    for a in tr.accounts:
        acct_rate[a.account.code or a.account.name.strip().lower()] = a.rate
        acct_stmt[a.account.code or a.account.name.strip().lower()] = lines[a.line]["statement"]
    if gl:
        for l in gl.lines:
            if l.reference == "OPENING":
                continue
            gl_by_acct.setdefault(l.account_code or l.account_name.strip().lower(), []).append(l)

    # ------------------------------------------------- account-level indicators
    for a in tr.accounts:
        acc = a.account
        amt = abs(a.net_aed)
        if amt < 0.5:
            continue
        stmt = lines[a.line]["statement"]
        key = acc.code or acc.name.strip().lower()
        for c in cats:
            by_line = a.line in c.get("lines", [])
            by_name = bool(c["_re"].search(acc.name))
            if c.get("only_lines") and a.line not in c["only_lines"]:
                continue
            if c.get("exclude") and re.search(c["exclude"], acc.name, re.I):
                continue
            if not (by_line or by_name):
                continue
            ap = c["applies_to"]
            if ap == "PL" and stmt != "PL":
                continue
            if ap == "BS" and stmt != "BS":
                continue
            # expense-type categories only make sense on debit balances (income accounts get other categories)
            if c["id"] in ("ENT", "GIFT", "DON", "FINE", "PERS", "MISC", "PROF", "COMM", "REPAIR", "INT", "TAXN", "TAXF") and a.net_aed <= 0:
                continue
            risk = _rate_risk(c["base_risk"], amt, th)
            refs = [l.line_id for l in gl_by_acct.get(key, [])][: th["max_gl_refs_per_flag"]]
            prop = None
            pct = None
            if c.get("adj_key"):
                pct = c.get("pct") if c.get("pct") is not None else params.get(c.get("pct_param", ""), None)
                if pct is not None and a.net_aed > 0:
                    prop = round(a.net_aed * pct, 2)
            reason = (f"Account name/type matches '{c['label']}'" if by_name or by_line else "") + \
                     f"; balance AED {amt:,.0f}" + (f" ({risk} because of size)" if risk != c["base_risk"] else "") + "."
            flags.append(Flag(
                flag_id=f"RF-{c['id']}-{key}", category=c["id"], category_label=c["label"], code=acc.code, name=acc.name,
                line=a.line, amount_aed=a.net_aed, period=period, reason=reason, tax_implication=c["implication"],
                risk=risk, documents=list(c["documents"]), status=c["status"], gl_refs=refs, adj_key=c.get("adj_key"),
                adj_pct=pct, proposed_adjustment=prop,
                rule_ref="NDE-01" if c["id"] in ("ENT", "DON", "FINE", "PERS", "TAXN", "TAXF") else
                         {"EXEMPT": "PE-01", "UNREAL": "RB-01", "RP": "RP-01", "INT": "INT-01", "PROV": "RB-01", "FX": "RB-01"}.get(c["id"], "NDE-01")))

    # ------------------------------------------------- movement against prior period (optional)
    if prior_tb:
        prior = {(a.code or a.name.strip().lower()): a for a in prior_tb.accounts}
        for a in tr.accounts:
            acc = a.account
            key = acc.code or acc.name.strip().lower()
            p = prior.get(key)
            if not p or abs(p.net) < 1:
                continue
            chg = (acc.net - p.net) / abs(p.net)
            diff_aed = abs(acc.net - p.net) * a.rate
            if abs(chg) >= th["movement_pct"] and diff_aed >= th["materiality_aed"] and lines[a.line]["statement"] == "PL":
                flags.append(Flag(
                    flag_id=f"RF-MOV-{key}", category="MOV", category_label="Significant movement vs prior period", code=acc.code,
                    name=acc.name, line=a.line, amount_aed=a.net_aed, period=period,
                    reason=f"Balance moved {chg:+.0%} against the prior-period TB (AED {diff_aed:,.0f}).",
                    tax_implication="Unexplained movements may indicate classification changes or one-off items.",
                    risk="Low" if diff_aed < th["high_aed"] else "Medium", documents=["Explanation of the movement"],
                    status="Information required", rule_ref="NDE-01"))

    # ------------------------------------------------- transaction-level tests
    txn = []
    rp_names = [n.strip().lower() for n in (related_parties or []) if len(n.strip()) >= 4]
    if gl:
        vague = [re.compile(p, re.I) for p in cfg["vague_narrations"]]
        pe = date.fromisoformat(period_end) if period_end else None
        ye_cut = (pe - timedelta(days=th["year_end_days"])).isoformat() if pe else None
        for l in gl.lines:
            if l.reference == "OPENING":
                continue                  # an opening balance brought forward is not a transaction of the period
            key = l.account_code or l.account_name.strip().lower()
            rate = acct_rate.get(key)
            if rate is None:
                continue
            amt_src = max(l.debit, l.credit)
            amt = amt_src * rate
            if amt < th["materiality_aed"] / 5:
                continue
            tests = []
            if amt >= th["round_min_aed"] and amt_src > 0 and abs(amt_src / th["round_multiple"] - round(amt_src / th["round_multiple"])) < 1e-9:
                tests.append(f"Round-sum amount (multiple of {th['round_multiple']:,})")
            if any(v.search((l.description or "").strip()) for v in vague) and amt >= th["materiality_aed"]:
                tests.append("Vague or missing narration")
            if ye_cut and l.date and l.date >= ye_cut and amt >= th["materiality_aed"]:
                tests.append(f"Entry in the last {th['year_end_days']} days of the period")
            text = f"{l.description} {l.counterparty}".lower()
            if rp_names and any(n in text for n in rp_names):
                tests.append("Counterparty/narration matches a declared related party")
            for c in cats:
                if c.get("narration") and c["_re"].search(f"{l.description} {l.counterparty}"):
                    # expense-type narrations only matter on debits to P&L accounts (not on sales or balance-sheet postings)
                    if c["id"] in EXPENSE_CATS and not (acct_stmt.get(key) == "PL" and l.net > 0):
                        continue
                    # only a transaction-level hit when the account name itself did not already trigger the category
                    if not c["_re"].search(l.account_name):
                        tests.append(f"Narration mentions '{c['label']}'")
            if amt >= th["high_aed"]:
                tests.append("Large entry")
            if acct_stmt.get(key) == "BS":
                tests = [t for t in tests if "related party" in t]      # balance-sheet postings: only related-party matches are of tax interest
            if tests:
                sev = 1
                if any("related party" in t or "Narration mentions" in t for t in tests):
                    sev = 3
                elif len(tests) >= 2 or "Large entry" in tests or "Vague" in tests[0]:
                    sev = 2
                txn.append(TxnFlag(l.line_id, l.date, l.account_code, l.account_name, l.net * rate, l.description,
                                   l.counterparty, l.reference, tests, RISK_NAME[sev]))
        txn.sort(key=lambda t: (-RISK_ORDER[t.risk], -abs(t.amount_aed)))
        if len(txn) > th["max_txn_flags"]:
            notes.append(f"{len(txn)} transactions were flagged; only the {th['max_txn_flags']} highest-priority are listed.")
            txn = txn[: th["max_txn_flags"]]
        # link transaction flags back to account flags by account
        by_acct = {}
        for t in txn:
            by_acct.setdefault(t.code or t.name.strip().lower(), []).append(t.line_id)
        for f in flags:
            k = f.code or f.name.strip().lower()
            if k in by_acct:
                f.gl_refs = list(dict.fromkeys(by_acct[k] + f.gl_refs))[: th["max_gl_refs_per_flag"]]
    else:
        notes.append("No GL was provided: transaction-level tests (round sums, vague narrations, year-end entries, related-party counterparties) were not run.")
    flags.sort(key=lambda f: (-RISK_ORDER[f.risk], -abs(f.amount_aed)))
    return RiskReview(flags, txn, th, notes)
