"""Suspicious transactions: rule-based red flags over the books (synced Tally vouchers), bank statements and the
app's invoices. Every flag is an INDICATOR FOR REVIEW, never a conclusion. Runs fully offline (no Gemini).

Rule groups
  A Cash limits (ITA 2025 s.185-188 / old 269SS, 269ST, 269T; s.34(3)/old 40A(3) style disallowance)
  B SFT-type thresholds (old AIR, Rule 114E style reporting)
  C TDS bypassing
  D Related parties (old 40A(2)(b), deemed dividend old 2(22)(e), Companies Act s.185)
  E Round tripping / circular flows / accommodation entries
  F Timing and book quality
  G GST (fake ITC, circular trading, e-way bill splitting, blocked credit, RCM, duplicates)
  H Banking patterns
  I Nature of expenditure (personal, capital, MSME 45 days)
  J Statistical anomalies (Benford, duplicates, round sums, dormant / new parties, volume jumps)

Section references follow the user's instruction: Income-tax Act 2025 numbers with the 1961 section in
brackets; they are labels only - verify against the bare Act before quoting in a report."""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import AuditLog, BankLine, Company, Invoice, RedFlagReview, VoucherHistory
from .masters import Masters
from .periods import Period, fy_start

ZERO = Decimal(0)
Q = Decimal("0.01")

DEFAULTS = {
    "cash_receipt_limit": 200000, "cash_loan_limit": 20000, "cash_expense_limit": 10000,
    "cash_transport_limit": 35000, "cash_asset_limit": 10000, "cash_donation_limit": 2000,
    "sft_cash_deposit_current": 5000000, "sft_cash_receipt_party": 200000, "sft_property": 3000000,
    "sft_investment": 1000000, "round_trip_days": 30, "round_trip_tolerance_pct": 5,
    "loan_window_days": 15, "high_cash_balance": 500000, "capital_item_limit": 10000,
    "msme_days": 45, "vague_narration_min": 50000, "new_party_days": 30, "new_party_amount": 200000,
    "dormant_days": 180, "dormant_amount": 100000, "volume_jump_x": 3, "volume_jump_min": 100000,
    "round_amount_min": 50000, "duplicate_days": 7, "eway_limit": 50000, "pan_quote_limit": 50000,
}

GROUP_NAMES = {"A": "Cash limits", "B": "SFT thresholds", "C": "TDS", "D": "Related parties",
               "E": "Round tripping & accommodation", "F": "Timing & book quality", "G": "GST",
               "H": "Banking patterns", "I": "Nature of expenditure", "J": "Statistical anomalies"}


@dataclass
class Flag:
    rule: str                 # e.g. "A1"
    title: str
    severity: str             # high | medium | low
    party: str = ""
    date: str = ""
    amount: Decimal = ZERO
    detail: str = ""
    refs: list = field(default_factory=list)     # voucher descriptions / guids (evidence)
    law: str = ""
    key: str = ""
    status: str = "open"
    note: str = ""
    reviewer: str = ""

    @property
    def group(self) -> str:
        return self.rule[0]

    def make_key(self) -> str:
        raw = f"{self.rule}|{self.party}|{self.date}|{self.amount}|{'|'.join(map(str, self.refs[:5]))}"
        self.key = hashlib.sha1(raw.encode()).hexdigest()[:24]
        return self.key


SEV_SCORE = {"high": 10, "medium": 4, "low": 1}


# ====================================================================== data access
@dataclass
class Book:
    """Pre-indexed view of the company's synced vouchers."""
    vouchers: list
    m: Masters
    cash: set
    bank: set
    primary: dict
    related: dict              # ledger -> relation text

    def prim(self, ledger: str) -> str:
        return self.primary.get(ledger, "")

    def is_party(self, ledger: str) -> bool:
        return self.prim(ledger) in ("Sundry Creditors", "Sundry Debtors")


def load_book(session: Session, company: Company, m: Masters, period: Period | None = None) -> Book:
    from .history import vouchers as _hv
    vchs = _hv(session, company.id, period.frm, period.to) if period else _hv(session, company.id)
    prim = {n: d.get("_primary", "") for n, d in m.ledgers.items()}
    cash = {n for n, p in prim.items() if p == "Cash-in-Hand"} | {n for n in prim if re.fullmatch(r"cash", n, re.I)}
    bank = {n for n, p in prim.items() if p in ("Bank Accounts", "Bank OD A/c")}
    related = {}
    for rp in (company.settings or {}).get("related_parties", []):
        for led in rp.get("ledgers", []) or [rp.get("name", "")]:
            if led:
                related[led] = rp.get("relation", "Related party")
    return Book(vchs, m, cash, bank, prim, related)


def _d(s: str) -> date:
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def _fmt(s: str) -> str:
    return f"{s[6:8]}-{s[4:6]}-{s[:4]}" if s and len(s) >= 8 else ""


def _vref(v) -> str:
    return f"{v.voucher_type} {v.number} dt {_fmt(v.date)}"


def _amt(e) -> Decimal:
    return Decimal(e["amount"])


# ====================================================================== the rules
def run(session: Session, company: Company, m: Masters, period: Period, today: date | None = None,
        bills: list | None = None, closings: dict | None = None) -> list[Flag]:
    today = today or date.today()
    th = {**DEFAULTS, **(company.settings or {}).get("redflag_thresholds", {})}
    bk = load_book(session, company, m, period)
    full = load_book(session, company, m, None)          # whole synced history for "first seen" / dormancy
    out: list[Flag] = []
    for fn in (_cash_rules, _sft_rules, _tds_rules, _related_rules, _round_trip_rules, _timing_rules, _gst_rules,
               _bank_rules, _expense_rules, _stat_rules):
        try:
            out += fn(session=session, company=company, bk=bk, full=full, th=th, period=period, today=today,
                      bills=bills, closings=closings)
        except Exception as e:                            # one broken rule never hides the others
            out.append(Flag("Z0", f"Rule group {fn.__name__} could not run", "low", detail=str(e)[:200]))
    for f in out:
        f.make_key()
    apply_reviews(session, company, out)
    return out


# ---------------------------------------------------------------- A cash
def _cash_rules(bk: Book, th: dict, **_) -> list[Flag]:
    out = []
    rec_day: dict = defaultdict(lambda: [ZERO, []])
    pay_day: dict = defaultdict(lambda: [ZERO, [], 0])
    loan_groups = ("Loans (Liability)", "Secured Loans", "Unsecured Loans", "Current Liabilities", "Capital Account",
                   "Loans & Advances (Asset)")
    for v in bk.vouchers:
        ents = v.entries or []
        cash_dr = sum((_amt(e) for e in ents if e["ledger"] in bk.cash and e["dr"]), ZERO)
        cash_cr = sum((_amt(e) for e in ents if e["ledger"] in bk.cash and not e["dr"]), ZERO)
        if cash_dr:
            for e in ents:
                if not e["dr"] and e["ledger"] not in bk.cash and e["ledger"] not in bk.bank:
                    a = min(_amt(e), cash_dr)
                    rec_day[(e["ledger"], v.date)][0] += a
                    rec_day[(e["ledger"], v.date)][1].append(_vref(v))
                    if bk.prim(e["ledger"]) in loan_groups and a >= th["cash_loan_limit"] and \
                            re.search(r"loan|deposit|advance|capital|unsecured|director|partner", e["ledger"] +
                                      " " + (v.narration or ""), re.I):
                        out.append(Flag("A2", "Loan / deposit / advance accepted in cash", "high", e["ledger"],
                                        v.date, a, f"Cash received {a:,.2f} credited to {e['ledger']}",
                                        [_vref(v)], "ITA 2025 s.185 (old 269SS); penalty s.450 (old 271D)"))
        if cash_cr:
            for e in ents:
                if e["dr"] and e["ledger"] not in bk.cash and e["ledger"] not in bk.bank:
                    a = min(_amt(e), cash_cr)
                    p = pay_day[(e["ledger"], v.date)]
                    p[0] += a
                    p[1].append(_vref(v))
                    p[2] += 1
                    prim = bk.prim(e["ledger"])
                    if prim in loan_groups and a >= th["cash_loan_limit"] and \
                            re.search(r"loan|deposit|advance|unsecured", e["ledger"], re.I):
                        out.append(Flag("A2", "Loan / deposit repaid in cash", "high", e["ledger"], v.date, a,
                                        f"Cash paid {a:,.2f} debited to {e['ledger']}", [_vref(v)],
                                        "ITA 2025 s.188 (old 269T)"))
                    if prim == "Fixed Assets" and a > th["cash_asset_limit"]:
                        out.append(Flag("A5", "Fixed asset bought for cash", "medium", e["ledger"], v.date, a,
                                        f"Cash {a:,.2f} for {e['ledger']} - depreciation on the cash part is at risk",
                                        [_vref(v)], "old 43(1) proviso / 40A(3)"))
                    if re.search(r"donation", e["ledger"], re.I) and a > th["cash_donation_limit"]:
                        out.append(Flag("A6", "Donation paid in cash above ₹2,000", "medium", e["ledger"], v.date, a,
                                        "Deduction not available for cash donations above ₹2,000", [_vref(v)],
                                        "old 80G(5D)"))
    for (party, d), (amt, refs) in rec_day.items():
        if amt >= th["cash_receipt_limit"]:
            out.append(Flag("A1", "Cash received ₹2 lakh or more from one person in a day", "high", party, d, amt,
                            f"{len(refs)} entr(ies) on {_fmt(d)} total {amt:,.2f}", refs,
                            "ITA 2025 s.186 (old 269ST); penalty s.451 (old 271DA)"))
    # A3 / A4: cash expenses above the limit, and splitting below it
    by_party = defaultdict(list)
    for (party, d), (amt, refs, n) in pay_day.items():
        by_party[party].append((d, amt, refs, n))
        lim = th["cash_transport_limit"] if re.search(r"transport|freight|truck|lorry", party, re.I) \
            else th["cash_expense_limit"]
        if amt > lim and bk.prim(party) not in ("Loans (Liability)", "Unsecured Loans", "Secured Loans",
                                                "Capital Account", "Bank Accounts", "Duties & Taxes"):
            sev = "high" if n == 1 else "high"
            out.append(Flag("A3", f"Cash paid above ₹{lim:,} to one person in a day", sev, party, d, amt,
                            f"{n} payment(s) on {_fmt(d)} total {amt:,.2f} - disallowance risk", refs,
                            "ITA 2025 s.34(3) (old 40A(3)) read with Rule 6DD"))
    for party, days in by_party.items():
        days.sort()
        for i, (d, amt, refs, n) in enumerate(days):
            if amt > th["cash_expense_limit"]:
                continue
            window = [x for x in days[i:i + 4] if (_d(x[0]) - _d(d)).days <= 2 and x[1] <= th["cash_expense_limit"]]
            tot = sum((x[1] for x in window), ZERO)
            if len(window) >= 2 and tot > th["cash_expense_limit"] and all(x[1] >= th["cash_expense_limit"] * 0.7
                                                                           for x in window):
                out.append(Flag("A4", "Cash payments split to stay under the limit", "high", party, d, tot,
                                f"{len(window)} cash payments of {', '.join(f'{x[1]:,.0f}' for x in window)} within "
                                f"3 days", [r for x in window for r in x[2]], "s.34(3) (old 40A(3)) - splitting"))
                break
    return out


# ---------------------------------------------------------------- B SFT thresholds
def _sft_rules(bk: Book, th: dict, **_) -> list[Flag]:
    out = []
    dep = ZERO
    dep_refs = []
    cash_from: dict = defaultdict(lambda: [ZERO, []])
    inv = defaultdict(lambda: [ZERO, []])
    for v in bk.vouchers:
        ents = v.entries or []
        if any(e["ledger"] in bk.cash and not e["dr"] for e in ents):
            for e in ents:
                if e["ledger"] in bk.bank and e["dr"]:
                    dep += _amt(e)
                    dep_refs.append(_vref(v))
        if any(e["ledger"] in bk.cash and e["dr"] for e in ents):
            for e in ents:
                if not e["dr"] and bk.prim(e["ledger"]) == "Sundry Debtors":
                    cash_from[e["ledger"]][0] += _amt(e)
                    cash_from[e["ledger"]][1].append(_vref(v))
        for e in ents:
            led = e["ledger"]
            if bk.prim(led) == "Fixed Assets" and re.search(r"land|building|flat|plot|property|premises|office\s*"
                                                           r"(space|unit)|shop", led, re.I) and \
                    _amt(e) >= th["sft_property"]:
                out.append(Flag("B9", "Immovable property transaction ₹30 lakh or more", "medium", led, v.date,
                                _amt(e), "Reportable in SFT; check stamp duty value and TDS on property",
                                [_vref(v)], "SFT (Rule 114E type); TDS 393(1) Sl. 3(i) (old 194-IA)"))
            if bk.prim(led) == "Investments" and e["dr"]:
                inv[led][0] += _amt(e)
                inv[led][1].append(_vref(v))
    if dep >= th["sft_cash_deposit_current"]:
        out.append(Flag("B7", "Cash deposited in bank: ₹50 lakh or more in the period", "medium", "", "", dep,
                        f"{len(dep_refs)} cash deposit(s) - bank reports these in its SFT", dep_refs[:20],
                        "SFT (old AIR) - cash deposits in current accounts"))
    for party, (amt, refs) in cash_from.items():
        if amt > th["sft_cash_receipt_party"]:
            out.append(Flag("B8", "Cash received from a customer above ₹2 lakh in the period", "medium", party, "",
                            amt, f"{len(refs)} cash receipt(s)", refs[:20], "SFT - cash receipts for goods/services"))
    for led, (amt, refs) in inv.items():
        if amt >= th["sft_investment"]:
            out.append(Flag("B10", "Investments of ₹10 lakh or more", "low", led, "", amt, f"{len(refs)} purchase(s)",
                            refs[:20], "SFT - shares / MF / bonds / debentures"))
    return out


# ---------------------------------------------------------------- C TDS
def _tds_rules(session: Session, company: Company, bk: Book, th: dict, period: Period, today: date, **_) -> list:
    from . import compliance, tds_map
    out = []
    near = compliance.tds_threshold_watch(session, company, bk.m, today)
    for party, sec, amt, limit, src in near:
        if amt >= limit:
            out.append(Flag("C11", "Paid above the TDS limit with no TDS deducted", "high", party, "", amt,
                            f"Credited {amt:,.2f} this FY against the {tds_map.label(sec, today.strftime('%Y%m%d'))} "
                            f"limit of {limit:,.0f} (section {('guessed' if src == 'guess' else 'as set')})", [],
                            "ITA 2025 s.393 / s.397 - disallowance under s.35 (old 40(a)(ia))"))
    rep = compliance.tds_tracker(session, company, bk.m, period, today)
    for mo in rep.months:
        if mo.unpaid and mo.due < today.strftime("%Y%m%d"):
            out.append(Flag("C13", f"TDS {tds_map.label(mo.section, mo.month + '01')} not deposited by the due date",
                            "high", "", mo.due,
                            mo.unpaid, f"Deducted {mo.deducted:,.2f} in {mo.month[4:6]}-{mo.month[:4]}, unpaid "
                                       f"{mo.unpaid:,.2f}, due {_fmt(mo.due)}", [], "Interest and penalty apply"))
    pans_needed = {r["party"] for r in rep.deductions if not r["pan"] and not str(r["section"]).startswith("192")
                   and bk.prim(r["party"]) not in ("Duties & Taxes", "Provisions")}
    for p in pans_needed:
        out.append(Flag("C14", "TDS deducted for a party without PAN in Tally", "medium", p, "", ZERO,
                        "Higher rate applies without PAN; add the PAN in the ledger", [],
                        "ITA 2025 s.397 (old 206AA)"))
    for r in rep.deductions:
        exp = {"194C": 1, "194J-P": 10, "194J-T": 2, "194I-B": 10, "194I-P": 2, "194H": 2, "194A": 10}.get(
            tds_map.normalise(r["section"]))
        if exp and r["rate"] and r["rate"] + Decimal("0.4") < exp:
            out.append(Flag("C16", "TDS rate lower than the section rate", "medium", r["party"], r["date"], r["tds"],
                            f"{r['rate']}% deducted on {r['amount']:,.2f}; section rate {exp}%", [r["voucher"]],
                            "Short deduction"))
    # C12 bills split under the single-bill limit (contracts)
    bills = defaultdict(list)
    tl = compliance.tds_ledgers(bk.m, company)
    for v in bk.vouchers:
        ents = v.entries or []
        if any(e["ledger"] in tl for e in ents) or re.search(r"payment|receipt|contra", v.voucher_type, re.I):
            continue
        for e in ents:
            if not e["dr"] and bk.prim(e["ledger"]) == "Sundry Creditors" and 25000 <= _amt(e) < 30000:
                bills[e["ledger"]].append((v.date, _amt(e), _vref(v)))
    for party, bs in bills.items():
        if len(bs) >= 3:
            out.append(Flag("C12", "Several bills just under the ₹30,000 single-bill limit", "medium", party,
                            bs[-1][0], sum((b[1] for b in bs), ZERO),
                            f"{len(bs)} bills between ₹25,000 and ₹30,000 with no TDS", [b[2] for b in bs][:10],
                            "Contract TDS splitting (393(1) Sl. 6(i), old 194C)"))
    # C15 same PAN / GSTIN on two ledgers
    pan: dict = defaultdict(list)
    for n, d in bk.m.ledgers.items():
        p = (d.get("INCOMETAXNUMBER") or "").strip().upper()
        g = (d.get("_gstin") or "").strip().upper()
        if re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", p):
            pan[p].append(n)
        elif len(g) == 15:
            pan[g[2:12]].append(n)
    for p, names in pan.items():
        if len(set(names)) > 1:
            out.append(Flag("C15", "Same PAN under more than one ledger", "medium", " / ".join(sorted(set(names))), "",
                            ZERO, f"PAN {p[:5]}XXXX{p[-1]} - TDS limits and 2B matching can be split across ledgers",
                            [], "Check for duplicate ledgers"))
    return out


# ---------------------------------------------------------------- D related parties
def _related_rules(bk: Book, th: dict, **_) -> list[Flag]:
    out = []
    if not bk.related:
        return out
    totals = defaultdict(lambda: [ZERO, ZERO, []])
    interest_paid = any(re.search(r"interest", e["ledger"], re.I) and e["dr"] and
                        bk.prim(e["ledger"]) in ("Indirect Expenses", "Direct Expenses")
                        for v in bk.vouchers for e in v.entries or [])
    for v in bk.vouchers:
        for e in v.entries or []:
            if e["ledger"] in bk.related:
                t = totals[e["ledger"]]
                t[0 if e["dr"] else 1] += _amt(e)
                t[2].append(_vref(v))
    for led, (dr, cr, refs) in totals.items():
        rel = bk.related[led]
        prim = bk.prim(led)
        out.append(Flag("D17", f"Transactions with related party ({rel})", "low", led, "", max(dr, cr),
                        f"Debits {dr:,.2f} · credits {cr:,.2f} · {len(refs)} voucher(s) - check arm's length",
                        refs[:30], "old 40A(2)(b); Companies Act s.188; AS 18 disclosure"))
        if prim in ("Loans & Advances (Asset)", "Current Assets", "Sundry Debtors") and dr > cr:
            out.append(Flag("D18", "Loan / advance to a related party", "high", led, "", dr - cr,
                            f"Net debit {dr - cr:,.2f}. For a closely held company with accumulated profits this can "
                            f"be deemed dividend; loans to directors need Companies Act s.185 compliance", refs[:30],
                            "Deemed dividend (old 2(22)(e)); Companies Act s.185 / s.186"))
            if interest_paid and not any(re.search(r"interest", r, re.I) for r in refs):
                out.append(Flag("D19", "Interest-free loan to a related party while paying interest", "medium", led,
                                "", dr - cr, "Interest expense exists but no interest is charged to this party",
                                refs[:10], "Disallowance of interest on diverted borrowed funds (old 36(1)(iii))"))
    return out


# ---------------------------------------------------------------- E round tripping
def _money_moves(bk: Book):
    """(date, party, amount, direction 'out'|'in', voucher) for bank / cash movements with a counter ledger."""
    for v in bk.vouchers:
        ents = v.entries or []
        money = [e for e in ents if e["ledger"] in bk.bank or e["ledger"] in bk.cash]
        others = [e for e in ents if e not in money]
        if not money or not others:
            continue
        for e in others:
            yield v.date, e["ledger"], _amt(e), ("out" if e["dr"] else "in"), v


def _round_trip_rules(session: Session, company: Company, bk: Book, full: Book, th: dict, period: Period,
                      **_) -> list:
    out = []
    moves = sorted(_money_moves(bk), key=lambda x: x[0])
    tol = Decimal(th["round_trip_tolerance_pct"]) / 100
    days = th["round_trip_days"]
    by_party = defaultdict(list)
    for mv in moves:
        by_party[mv[1]].append(mv)
    skip_groups = ("Duties & Taxes", "Bank Accounts", "Bank OD A/c", "Cash-in-Hand", "Indirect Expenses",
                   "Direct Expenses", "Sales Accounts", "Purchase Accounts", "Indirect Incomes", "Direct Incomes")
    for party, mvs in by_party.items():
        if bk.prim(party) in skip_groups:
            continue
        for i, (d, _p, amt, dirn, v) in enumerate(mvs):
            if amt < 50000:
                continue
            for d2, _p2, amt2, dir2, v2 in mvs[i + 1:]:
                gap = (_d(d2) - _d(d)).days
                if gap > days:
                    break
                if dir2 != dirn and abs(amt2 - amt) <= amt * tol:
                    out.append(Flag("E21", "Money went out and came back from the same party", "high", party, d, amt,
                                    f"{'Paid' if dirn == 'out' else 'Received'} {amt:,.2f} on {_fmt(d)} and "
                                    f"{'received' if dir2 == 'in' else 'paid'} {amt2:,.2f} on {_fmt(d2)} "
                                    f"({gap} days) - possible round tripping / accommodation", [_vref(v), _vref(v2)],
                                    "Unexplained credits (ITA 2025 s.102, old s.68)"))
                    break
    # E21b: paid to one party, a similar sum comes back from a related party
    if bk.related:
        outs = [m for m in moves if m[3] == "out" and m[2] >= 100000]
        ins = [m for m in moves if m[3] == "in" and m[1] in bk.related and m[2] >= 100000]
        for d, p, amt, _dir, v in outs:
            for d2, p2, amt2, _dir2, v2 in ins:
                if p2 != p and 0 <= (_d(d2) - _d(d)).days <= days and abs(amt2 - amt) <= amt * tol:
                    out.append(Flag("E21", "Paid out, similar amount back from a related party", "high", f"{p} → {p2}",
                                    d, amt, f"{amt:,.2f} paid to {p} on {_fmt(d)}; {amt2:,.2f} received from {p2} "
                                            f"on {_fmt(d2)}", [_vref(v), _vref(v2)], "Circular flow"))
    # E22 / G34 same party buys from us and sells to us
    sales = defaultdict(list)
    purch = defaultdict(list)
    for v in bk.vouchers:
        t = v.voucher_type.lower()
        for e in v.entries or []:
            if bk.is_party(e["ledger"]):
                if "sales" in t and e["dr"]:
                    sales[e["ledger"]].append((v.date, _amt(e), _vref(v)))
                if "purchase" in t and not e["dr"]:
                    purch[e["ledger"]].append((v.date, _amt(e), _vref(v)))
    for party in set(sales) & set(purch):
        s_tot = sum((x[1] for x in sales[party]), ZERO)
        p_tot = sum((x[1] for x in purch[party]), ZERO)
        if min(s_tot, p_tot) >= 100000 and abs(s_tot - p_tot) <= max(s_tot, p_tot) * Decimal("0.25"):
            out.append(Flag("G34", "Party is both customer and supplier for similar values", "high", party, "",
                            min(s_tot, p_tot), f"Sales {s_tot:,.2f} vs purchases {p_tot:,.2f} - check for circular "
                                               f"trading / fake ITC", [x[2] for x in sales[party][:5] +
                                                                      purch[party][:5]], "GST circular trading"))
    # E23 loans in and out quickly (window dressing)
    loan_groups = ("Loans (Liability)", "Secured Loans", "Unsecured Loans")
    for party, mvs in by_party.items():
        if bk.prim(party) not in loan_groups:
            continue
        for i, (d, _p, amt, dirn, v) in enumerate(mvs):
            if dirn != "in" or amt < 100000:
                continue
            for d2, _p2, amt2, dir2, v2 in mvs[i + 1:]:
                gap = (_d(d2) - _d(d)).days
                if gap > th["loan_window_days"]:
                    break
                if dir2 == "out" and abs(amt2 - amt) <= amt * tol:
                    around_ye = any(x[4:8] in ("0325", "0326", "0327", "0328", "0329", "0330", "0331",
                                                "0401", "0402", "0403", "0404", "0405") for x in (d, d2))
                    out.append(Flag("E23", "Loan taken and repaid within days" + (" around 31 March" if around_ye
                                                                                  else ""),
                                    "high" if around_ye else "medium", party, d, amt,
                                    f"Received {amt:,.2f} on {_fmt(d)}, repaid {amt2:,.2f} on {_fmt(d2)}",
                                    [_vref(v), _vref(v2)], "Window dressing / accommodation"))
                    break
    # E24 new unsecured loans / capital from parties with no history
    first_seen = {}
    for v in full.vouchers:
        for e in v.entries or []:
            first_seen.setdefault(e["ledger"], v.date)
    for d, p, amt, dirn, v in moves:
        if dirn == "in" and amt >= 100000 and bk.prim(p) in loan_groups + ("Capital Account",) and \
                first_seen.get(p) == d:
            out.append(Flag("E24", "Large loan / capital from a party with no history", "medium", p, d, amt,
                            "First transaction with this party - keep identity, creditworthiness and genuineness "
                            "evidence", [_vref(v)], "Unexplained cash credit (ITA 2025 s.102, old s.68)"))
    # E25 bogus purchase pattern: purchase -> bank payment -> similar cash withdrawal
    withdrawals = [(d, amt, v) for d, p, amt, dirn, v in moves if p in bk.cash and dirn == "out" and amt >= 50000]
    withdrawals += [(v.date, _amt(e), v) for v in bk.vouchers for e in v.entries or []
                    if e["ledger"] in bk.cash and e["dr"] and any(x["ledger"] in bk.bank and not x["dr"]
                                                                   for x in v.entries) and _amt(e) >= 50000]
    for d, p, amt, dirn, v in moves:
        if dirn != "out" or bk.prim(p) != "Sundry Creditors" or amt < 50000:
            continue
        if not any(x[2] is not v and 0 <= (_d(x[0]) - _d(d)).days <= 7 and abs(x[1] - amt) <= amt * Decimal("0.02")
                   for x in withdrawals):
            continue
        hit = next(x for x in withdrawals if x[2] is not v and 0 <= (_d(x[0]) - _d(d)).days <= 7 and
                   abs(x[1] - amt) <= amt * Decimal("0.02"))
        out.append(Flag("E25", "Supplier paid, then similar cash withdrawn", "high", p, d, amt,
                        f"Paid {amt:,.2f} to {p}; cash {hit[1]:,.2f} withdrawn on {_fmt(hit[0])} - pattern of "
                        f"accommodation / bogus purchase", [_vref(v), _vref(hit[2])],
                        "Bogus purchases (ITA 2025 s.103/104, old 69C); fake ITC under GST"))
    # E26 counterparty bank account changes (from bank statement narrations)
    acc: dict = defaultdict(set)
    for ln in session.scalars(select(BankLine).where(BankLine.company_id == company.id,
                                                     BankLine.date >= period.frm, BankLine.date <= period.to)):
        from .bank import counterparty
        cp = counterparty(ln.narration or "")
        for num in re.findall(r"\b\d{9,18}\b", ln.narration or ""):
            if cp and not re.fullmatch(r"\d{12}", num):       # 12-digit = UPI RRN, not an account
                acc[cp].add(num[-4:])
    for cp, nums in acc.items():
        if len(nums) > 1:
            out.append(Flag("E26", "Counterparty paid to different bank accounts", "medium", cp, "", ZERO,
                            f"Accounts ending {', '.join(sorted(nums))} - confirm the change with the vendor", [],
                            "Payment diversion risk"))
    return out


# ---------------------------------------------------------------- F timing & book quality
def _timing_rules(session: Session, company: Company, bk: Book, full: Book, th: dict, period: Period, **_) -> list:
    out = []
    # F27 31 March entries reversed in April
    march = [v for v in full.vouchers if v.date[4:8] == "0331" and period.contains(v.date)]
    april = [v for v in full.vouchers if v.date[4:6] == "04" and int(v.date[6:8]) <= 30]
    for v in march:
        sig = sorted((e["ledger"], e["amount"], e["dr"]) for e in v.entries or [])
        tot = sum((_amt(e) for e in v.entries or [] if e["dr"]), ZERO)
        if tot < 50000:
            continue
        rev = sorted((e[0], e[1], not e[2]) for e in sig)
        for a in april:
            if a.date[:4] == str(int(v.date[:4])) and sorted((e["ledger"], e["amount"], e["dr"])
                                                             for e in a.entries or []) == rev:
                out.append(Flag("F27", "Year-end entry reversed in April", "medium", v.party or "", v.date, tot,
                                f"Reversed by {_vref(a)}", [_vref(v), _vref(a)], "Year-end window dressing"))
                break
    # F28 backdated: entered (Tally id order) long after later-dated vouchers
    with_id = [v for v in full.vouchers if (v.masterid or "").isdigit()]
    with_id.sort(key=lambda v: int(v.masterid))
    latest = ""
    for v in with_id:
        if latest and (_d(latest) - _d(v.date)).days > 45 and period.contains(v.date):
            out.append(Flag("F28", "Entry looks backdated", "medium", v.party or "", v.date,
                            sum((_amt(e) for e in v.entries or [] if e["dr"]), ZERO),
                            f"Entered after vouchers dated up to {_fmt(latest)} - check Tally's edit log",
                            [_vref(v)], "Companies Act audit trail (Rule 3(1))"))
        latest = max(latest, v.date)
    # F29 posted into a locked period (with override)
    for a in session.scalars(select(AuditLog).where(AuditLog.company_id == company.id,
                                                    AuditLog.action == "lock_override")):
        d = (a.after or {}).get("date", "")
        if period.contains(d):
            out.append(Flag("F29", "Posted into a locked period", "low", a.updated_by, d, ZERO,
                            f"Reason given: {(a.after or {}).get('reason', '')}", [], "Period lock override"))
    # F30 / F31 cash balance by day
    if bk.cash:
        open_bal = ZERO
        for n in bk.cash:
            from .masters import Masters  # noqa
            ob = bk.m.ledgers.get(n, {}).get("OPENINGBALANCE", "")
            try:
                open_bal += -Decimal(str(ob).replace(",", "").split()[0]) if ob else ZERO
            except Exception:
                pass
        bal = open_bal
        start_fy = fy_start(period.start).strftime("%Y%m%d")
        neg_days, high_months = [], {}
        by_day = defaultdict(lambda: ZERO)
        for v in full.vouchers:
            if v.date < start_fy:
                continue
            for e in v.entries or []:
                if e["ledger"] in bk.cash:
                    by_day[v.date] += _amt(e) if e["dr"] else -_amt(e)
        for d in sorted(by_day):
            bal += by_day[d]
            if period.contains(d):
                if bal < -1:
                    neg_days.append((d, bal))
                high_months[d[:6]] = (d, bal)
        if neg_days:
            d, b = neg_days[0]
            out.append(Flag("F30", "Cash balance goes negative", "high", ", ".join(sorted(bk.cash)), d, -b,
                            f"Negative on {len(neg_days)} day(s), first {_fmt(d)} ({b:,.2f}) - unrecorded cash "
                            f"receipts or wrong dates", [], "Unexplained cash (ITA 2025 s.102-104, old 68/69)"))
        for mth, (d, b) in high_months.items():
            if b > th["high_cash_balance"]:
                out.append(Flag("F31", "High cash balance", "low", ", ".join(sorted(bk.cash)), d, b,
                                f"Cash {b:,.2f} at {_fmt(d)} - verify physically", [], "Cash verification"))
    # F32 journals through cash
    for v in bk.vouchers:
        if "journal" in v.voucher_type.lower() and any(e["ledger"] in bk.cash for e in v.entries or []):
            out.append(Flag("F32", "Journal entry touching cash", "low", v.party or "", v.date,
                            sum((_amt(e) for e in v.entries or [] if e["dr"]), ZERO), "Cash should move through "
                                                                                       "Payment / Receipt vouchers",
                            [_vref(v)], "Book quality"))
    return out


# ---------------------------------------------------------------- G GST
_BLOCKED = r"motor\s*car|car\b|vehicle|food|catering|beverage|club|membership|gift|beauty|health\s*service|" \
           r"cosmetic|life\s*insurance|health\s*insurance|travel\s*benefit|personal"


def _gst_rules(session: Session, company: Company, bk: Book, th: dict, period: Period, today: date,
               bills=None, closings=None, **_) -> list:
    from ..tally.parsers import gstin_valid
    out = []
    invs = [r for r in session.scalars(select(Invoice).where(Invoice.company_id == company.id))
            if period.contains((r.extraction or {}).get("invoice_date", "") or period.frm)]
    seen_no = defaultdict(list)
    per_day = defaultdict(list)
    for r in invs:
        ex = r.extraction or {}
        g = ex.get("supplier_gstin", "")
        tot = Decimal(str(ex.get("grand_total") or 0))
        if g and not gstin_valid(g):
            out.append(Flag("G33", "Supplier GSTIN is not valid", "high", ex.get("supplier_name", ""),
                            ex.get("invoice_date", ""), tot, f"GSTIN {g} fails the checksum - ITC at risk",
                            [f"Inv {ex.get('invoice_no', '')}"], "CGST s.16(2)(aa)"))
        if (r.status_2b or "") == "not_in_2b" and r.status == "posted":
            out.append(Flag("G33", "ITC taken on an invoice not in GSTR-2B", "high", ex.get("supplier_name", ""),
                            ex.get("invoice_date", ""), tot, "Supplier hasn't reported it", [f"Inv {ex.get('invoice_no', '')}"],
                            "CGST s.16(2)(aa) / Rule 36(4)"))
        key = (g or ex.get("supplier_name", ""), str(ex.get("invoice_no", "")).strip().lower())
        if key[1]:
            seen_no[key].append(r)
        if g and ex.get("invoice_date"):
            per_day[(g, ex["invoice_date"])].append((tot, ex))
        sup_state, our = g[:2], (company.gstin or "")[:2]
        igst = Decimal(str(ex.get("igst_total") or 0))
        cg = Decimal(str(ex.get("cgst_total") or 0))
        pos = ex.get("place_of_supply") or our
        if g and our and ((sup_state == pos and igst) or (sup_state != pos and cg)):
            out.append(Flag("G38", "Tax type doesn't match the place of supply", "medium", ex.get("supplier_name", ""),
                            ex.get("invoice_date", ""), tot, f"Supplier state {sup_state}, place of supply {pos}, "
                                                             f"{'IGST' if igst else 'CGST/SGST'} charged",
                            [f"Inv {ex.get('invoice_no', '')}"], "IGST Act s.7/8"))
        if tot >= th["round_amount_min"] and tot % 1000 == 0:
            out.append(Flag("G40", "Round-figure invoice", "low", ex.get("supplier_name", ""), ex.get("invoice_date", ""),
                            tot, "Exact round amount including tax", [f"Inv {ex.get('invoice_no', '')}"],
                            "Indicator only"))
    for key, rows in seen_no.items():
        if len(rows) > 1:
            out.append(Flag("G39", "Same supplier invoice number entered twice", "high", key[0], "",
                            Decimal(str((rows[0].extraction or {}).get("grand_total") or 0)),
                            f"Invoice {key[1]} appears {len(rows)} times", [r.file_path for r in rows][:5],
                            "Duplicate ITC"))
    for (g, d), rows in per_day.items():
        small = [x for x in rows if th["eway_limit"] * 0.8 <= x[0] < th["eway_limit"]]
        if len(small) >= 2 and sum((x[0] for x in small), ZERO) > th["eway_limit"]:
            out.append(Flag("G35", "Invoices split just under the e-way bill limit", "medium",
                            small[0][1].get("supplier_name", g), d, sum((x[0] for x in small), ZERO),
                            f"{len(small)} invoices of {', '.join(f'{x[0]:,.0f}' for x in small)} on one day",
                            [f"Inv {x[1].get('invoice_no', '')}" for x in small], "E-way bill (Rule 138)"))
    # G36 blocked credit claimed / G37 RCM missing - from the books
    for v in bk.vouchers:
        ents = v.entries or []
        gst_in = [e for e in ents if e["dr"] and bk.prim(e["ledger"]) == "Duties & Taxes" and
                  re.search(r"input|itc|cgst|sgst|igst", e["ledger"], re.I) and not re.search(r"output|payable|rcm",
                                                                                               e["ledger"], re.I)]
        heads = [e["ledger"] for e in ents if e["dr"] and bk.prim(e["ledger"]) in
                 ("Indirect Expenses", "Direct Expenses", "Fixed Assets")]
        text = " ".join(heads) + " " + (v.narration or "")
        if gst_in and re.search(_BLOCKED, text, re.I):
            out.append(Flag("G36", "GST input taken on a blocked item", "medium", v.party or "", v.date,
                            sum((_amt(e) for e in gst_in), ZERO), f"Expense: {', '.join(heads)[:80]}", [_vref(v)],
                            "CGST s.17(5)"))
        party = next((e["ledger"] for e in ents if not e["dr"] and bk.prim(e["ledger"]) == "Sundry Creditors"), "")
        if party and re.search(r"freight|transport|cartage|gta|legal|advocate|lawyer|security\s*service|"
                               r"sponsorship|director", text, re.I) and \
                not bk.m.ledgers.get(party, {}).get("_gstin") and \
                not any(re.search(r"rcm|reverse", e["ledger"], re.I) for e in ents):
            out.append(Flag("G37", "Possible RCM service from an unregistered party, no RCM entry", "medium", party,
                            v.date, sum((_amt(e) for e in ents if e["dr"]), ZERO), f"Expense: {', '.join(heads)[:80]}",
                            [_vref(v)], "CGST s.9(3) - RCM notified services"))
    # G41 ITC not reversed on bills unpaid 180 days (FIFO on the real balance)
    from . import compliance
    for party, name, bd, amt, why in compliance.unpaid_bills(session, company, bk.m, bills, closings):
        if len(bd) == 8 and (today - _d(bd)).days > 180:
            out.append(Flag("G41", "Bill unpaid over 180 days - ITC to be reversed", "medium", party, bd, amt, why,
                            [name], "CGST s.16(2) second proviso / Rule 37"))
    return out


# ---------------------------------------------------------------- H banking patterns
def _bank_rules(session: Session, company: Company, th: dict, period: Period, **_) -> list:
    out = []
    lines = list(session.scalars(select(BankLine).where(BankLine.company_id == company.id,
                                                        BankLine.date >= period.frm, BankLine.date <= period.to)
                                 .order_by(BankLine.date)))
    cash_deps = [l for l in lines if l.deposit and re.search(r"cash\s*dep|by\s*cash|csh\s*dep|cash\s*deposit|cdm",
                                                             l.narration or "", re.I)]
    under = [l for l in cash_deps if th["pan_quote_limit"] * 0.9 <= l.deposit < th["pan_quote_limit"]]
    if len(under) >= 2:
        out.append(Flag("H43", "Repeated cash deposits just under ₹50,000", "high", lines[0].bank_ledger if lines else "",
                        under[0].date, Decimal(str(sum(l.deposit for l in under))),
                        f"{len(under)} deposits between ₹45,000 and ₹49,999 - avoiding PAN quoting?",
                        [f"{_fmt(l.date)} {l.deposit:,.0f}" for l in under][:10], "Rule 114B / structuring"))
    wd = [l for l in lines if l.withdrawal and re.search(r"cash|self|atm|csh\s*wd", l.narration or "", re.I)
          and l.withdrawal >= 100000]
    for w in wd:
        for d in cash_deps:
            gap = (_d(d.date) - _d(w.date)).days
            if 0 < gap <= 7 and abs(d.deposit - w.withdrawal) <= w.withdrawal * 0.05:
                out.append(Flag("H44", "Large cash withdrawal followed by a similar deposit", "medium", w.bank_ledger,
                                w.date, Decimal(str(w.withdrawal)), f"Withdrawn {w.withdrawal:,.0f} on {_fmt(w.date)}, "
                                                                     f"deposited {d.deposit:,.0f} on {_fmt(d.date)}",
                                [w.narration[:60], d.narration[:60]], "Cash rotation"))
                break
    by_month = defaultdict(list)
    for l in lines:
        if l.deposit and re.search(r"\bupi\b|imps", l.narration or "", re.I) and l.status in ("new", "posted"):
            by_month[l.date[:6]].append(l)
    for mth, ls in by_month.items():
        names = {re.sub(r"\W", "", (l.narration or "").upper())[:30] for l in ls}
        if len(ls) >= 15 and len(names) >= 10:
            out.append(Flag("H45", "Many small UPI / IMPS credits from different people", "low", ls[0].bank_ledger,
                            mth + "01", Decimal(str(sum(l.deposit for l in ls))),
                            f"{len(ls)} credits in {mth[4:]}-{mth[:4]} - verify the nature (sales? loans?)", [],
                            "Unexplained credits"))
    for l in lines:
        n = l.narration or ""
        if re.search(r"return|bounce|rtn\b|dishono|insufficient|unpaid\s*chq|chq\s*ret", n, re.I):
            out.append(Flag("H46", "Cheque returned", "low", l.bank_ledger, l.date,
                            Decimal(str(l.withdrawal or l.deposit)), n[:100], [], "NI Act s.138 / party risk"))
        if re.search(r"swift|foreign|remit|inward\s*rem|outward\s*rem|\bfx\b|forex|\bfcy\b|usd|eur\b|gbp", n, re.I):
            out.append(Flag("H47", "Foreign remittance in the bank", "medium", l.bank_ledger, l.date,
                            Decimal(str(l.withdrawal or l.deposit)), n[:100] + " - keep 15CA/CB, FIRC, FEMA papers",
                            [], "ITA 2025 s.397 (old 195) / FEMA"))
    return out


# ---------------------------------------------------------------- I nature of expenditure
_PERSONAL = r"school|tuition|college\s*fee|jewel|gold|household|grocery|kirana|personal|family|wife|husband|son\b|" \
            r"daughter|birthday|wedding|marriage|holiday|vacation|club\s*membership|gym|salon|spa"
_CAPITAL = r"laptop|computer|desktop|\bac\b|air\s*condition|furniture|chair|table|mobile\s*(phone|handset)|iphone|" \
           r"printer|machine|inverter|refrigerator|fridge|television|\btv\b|cctv|server"


def _expense_rules(session: Session, company: Company, bk: Book, th: dict, today: date, bills=None,
                   closings=None, **_) -> list:
    out = []
    for v in bk.vouchers:
        ents = v.entries or []
        exp = [e for e in ents if e["dr"] and bk.prim(e["ledger"]) in ("Indirect Expenses", "Direct Expenses")]
        if not exp:
            continue
        text = " ".join(e["ledger"] for e in exp) + " " + (v.narration or "")
        tot = sum((_amt(e) for e in exp), ZERO)
        if re.search(r"depreciat|amorti[sz]", text, re.I):
            continue                         # depreciation names the assets it is charged on: not an expense item
        if re.search(_PERSONAL, text, re.I) and tot >= 5000:
            out.append(Flag("I48", "Looks like a personal expense", "medium", v.party or exp[0]["ledger"], v.date, tot,
                            (v.narration or exp[0]["ledger"])[:100], [_vref(v)], "ITA 2025 s.34 (old 37(1))"))
        if re.search(_CAPITAL, text, re.I) and tot >= th["capital_item_limit"]:
            out.append(Flag("I49", "Capital item charged to expenses", "low", v.party or exp[0]["ledger"], v.date, tot,
                            (v.narration or exp[0]["ledger"])[:100], [_vref(v)], "Capitalise and depreciate"))
    # I50 MSME paid late (45 days): suppliers tagged MSME
    msme = set((company.settings or {}).get("msme_parties", [])) | \
        {n for n, d in bk.m.ledgers.items() if d.get("_primary") == "Sundry Creditors" and
         re.search(r"\bmsme\b|micro|udyam", n, re.I)}
    if msme:
        from . import compliance
        for party, name, bd, amt, why in compliance.unpaid_bills(session, company, bk.m, bills, closings):
            if party in msme and len(bd) == 8 and (today - _d(bd)).days > th["msme_days"]:
                out.append(Flag("I50", "MSME supplier unpaid beyond 45 days", "high", party, bd, amt,
                                f"{(today - _d(bd)).days} days - deduction only when paid", [name],
                                "ITA 2025 s.37 (old 43B(h)); MSMED Act s.15"))
    return out


# ---------------------------------------------------------------- J statistics
BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}
HOLIDAYS = {"0126", "0815", "1002"}


def _stat_rules(company: Company, bk: Book, full: Book, th: dict, period: Period, **_) -> list:
    out = []
    amts = [abs(_amt(e)) for v in bk.vouchers for e in v.entries or []
            if e["dr"] and bk.prim(e["ledger"]) in ("Indirect Expenses", "Direct Expenses", "Purchase Accounts")
            and _amt(e) >= 10]
    if len(amts) >= 200:
        firsts = Counter(int(str(int(a))[0]) for a in amts if int(a) > 0)
        n = sum(firsts.values())
        mad = sum(abs(firsts.get(d, 0) / n - p) for d, p in BENFORD.items()) / 9
        if mad > 0.015:
            worst = max(BENFORD, key=lambda d: firsts.get(d, 0) / n - BENFORD[d])
            out.append(Flag("J51", "Expense amounts don't follow Benford's law", "medium" if mad > 0.022 else "low",
                            "", "", ZERO, f"MAD {mad:.4f} over {n} amounts; digit {worst} appears "
                                          f"{firsts.get(worst, 0) / n:.1%} vs expected {BENFORD[worst]:.1%} - "
                                          f"look at amounts starting with {worst}", [], "Forensic indicator"))
    # J52 duplicate payments
    pays = defaultdict(list)
    for d, p, amt, dirn, v in _money_moves(bk):
        if dirn == "out" and amt >= 5000 and bk.prim(p) not in ("Duties & Taxes",):
            pays[(p, amt)].append((d, v))
    for (p, amt), ds in pays.items():
        ds.sort(key=lambda x: x[0])
        for (d1, v1), (d2, v2) in zip(ds, ds[1:]):
            if (_d(d2) - _d(d1)).days <= th["duplicate_days"]:
                out.append(Flag("J52", "Possible duplicate payment", "medium", p, d2, amt,
                                f"Same amount paid on {_fmt(d1)} and {_fmt(d2)}", [_vref(v1), _vref(v2)],
                                "Recover / confirm"))
                break
    # J53 weekend / holiday entries
    for v in bk.vouchers:
        tot = sum((_amt(e) for e in v.entries or [] if e["dr"]), ZERO)
        if tot >= 100000 and (_d(v.date).weekday() == 6 or v.date[4:8] in HOLIDAYS):
            out.append(Flag("J53", "Large entry dated on a Sunday / national holiday", "low", v.party or "", v.date,
                            tot, "Check the document date", [_vref(v)], "Indicator only"))
    # J54 new party, large payments soon / J55 dormant party reactivated / J57 volume jump
    # Only the party's business side is counted (bills for a supplier, sales for a customer), so a 1,00,000 bill
    # and its 1,00,000 payment are 1,00,000 of business, not 2,00,000.
    first, last_by_party = {}, defaultdict(list)
    for v in full.vouchers:
        for e in v.entries or []:
            led = e["ledger"]
            if bk.is_party(led) and e["dr"] == _business_dr(bk, led, full):
                first.setdefault(led, v.date)
                last_by_party[led].append((v.date, _amt(e), v))
    for p, rows in last_by_party.items():
        f = first[p]
        early = [(d, a, v) for d, a, v in rows if (_d(d) - _d(f)).days <= th["new_party_days"] and period.contains(d)]
        tot = sum((a for _d2, a, _v in early), ZERO)
        if tot >= th["new_party_amount"] and period.contains(f):
            out.append(Flag("J54", "New party with large amounts in its first month", "medium", p, f, tot,
                            f"First entry {_fmt(f)}; {len(early)} entr(ies) of {tot:,.2f} within "
                            f"{th['new_party_days']} days", [_vref(v) for _d2, _a, v in early][:10], "KYC / genuineness"))
        rows.sort(key=lambda x: x[0])
        for (d1, _a1, _v1), (d2, a2, v2) in zip(rows, rows[1:]):
            if (_d(d2) - _d(d1)).days >= th["dormant_days"] and a2 >= th["dormant_amount"] and period.contains(d2):
                out.append(Flag("J55", "Dormant party suddenly active", "low", p, d2, a2,
                                f"No entries from {_fmt(d1)} to {_fmt(d2)}", [_vref(v2)], "Indicator only"))
                break
        months = defaultdict(lambda: ZERO)
        for d, a, _v in rows:
            months[d[:6]] += a
        ks = sorted(months)
        for i, k in enumerate(ks):
            prior = [months[x] for x in ks[max(0, i - 6):i]]
            if len(prior) >= 3 and period.contains(k + "01"):
                avg = sum(prior, ZERO) / len(prior)
                if months[k] >= th["volume_jump_min"] and avg and months[k] > avg * th["volume_jump_x"]:
                    out.append(Flag("J57", "Party's volume jumped far above its usual level", "low", p, k + "01",
                                    months[k], f"{months[k]:,.0f} in {k[4:]}-{k[:4]} vs average {avg:,.0f}", [],
                                    "Indicator only"))
                    break
    # J56 vague narrations
    for v in bk.vouchers:
        tot = sum((_amt(e) for e in v.entries or [] if e["dr"]), ZERO)
        if tot >= th["vague_narration_min"] and re.search(r"\badjust|settle(ment)?\b|as per (md|director|boss|sir)|"
                                                          r"\bmisc\b|sundry|being adjusted|personal", v.narration or "",
                                                          re.I):
            out.append(Flag("J56", "Large entry with a vague narration", "low", v.party or "", v.date, tot,
                            (v.narration or "")[:100], [_vref(v)], "Support required"))
    return out


_SIDE: dict = {}


def _business_dr(bk: Book, ledger: str, full: Book) -> bool:
    """True if this party's business shows as debits (customers), False if as credits (suppliers).
    Other parties (loans, advances): whichever side is larger over the whole book."""
    prim = bk.prim(ledger)
    if prim == "Sundry Debtors":
        return True
    if prim == "Sundry Creditors":
        return False
    key = (id(full), ledger)
    if key not in _SIDE:
        dr = cr = ZERO
        for v in full.vouchers:
            for e in v.entries or []:
                if e["ledger"] == ledger:
                    if e["dr"]:
                        dr += _amt(e)
                    else:
                        cr += _amt(e)
        _SIDE[key] = dr >= cr
    return _SIDE[key]


# ====================================================================== reviews (repository)
def apply_reviews(session: Session, company: Company, flags: list[Flag]) -> None:
    revs = {r.key: r for r in session.scalars(select(RedFlagReview).where(RedFlagReview.company_id == company.id))}
    for f in flags:
        r = revs.get(f.key) or revs.get(f"rule:{f.rule}|party:{f.party}")
        if r:
            f.status, f.note, f.reviewer = r.status, r.note, f"{r.reviewer} · {r.reviewed_at}"


def review(session: Session, company: Company, flag: Flag, status: str, note: str, actor: str,
           whole_party: bool = False) -> None:
    """explained / false_positive / open. whole_party: the same rule for this party stays quiet from now on."""
    key = f"rule:{flag.rule}|party:{flag.party}" if whole_party else flag.key
    r = session.scalar(select(RedFlagReview).where(RedFlagReview.company_id == company.id, RedFlagReview.key == key))
    if r is None:
        r = RedFlagReview(company_id=company.id, key=key)
        session.add(r)
    r.status, r.note, r.reviewer = status, note, actor
    r.reviewed_at = datetime.now().strftime("%d-%m-%Y %H:%M")
    session.commit()


def party_scores(flags: list[Flag]) -> list[tuple]:
    """(party, score, open flags, groups) - many small signals together push a party up."""
    sc = defaultdict(lambda: [0, 0, set()])
    for f in flags:
        if f.status != "open" or not f.party:
            continue
        s = sc[f.party]
        s[0] += SEV_SCORE[f.severity]
        s[1] += 1
        s[2].add(f.group)
    return sorted(((p, v[0] + 3 * (len(v[2]) - 1), v[1], "".join(sorted(v[2]))) for p, v in sc.items()),
                  key=lambda x: -x[1])


def related_transactions(session: Session, company: Company, m: Masters, period: Period) -> dict:
    """ledger -> list of vouchers with it (for the Related Parties view)."""
    bk = load_book(session, company, m, period)
    out = defaultdict(list)
    for v in bk.vouchers:
        for e in v.entries or []:
            if e["ledger"] in bk.related:
                out[e["ledger"]].append((v, e))
    return out


def to_excel(flags: list[Flag], path, company: str, period_text: str) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Red flags"
    ws.append([f"{company} - red flags {period_text} (indicators for review, not conclusions)"])
    hdr = ["Rule", "Group", "Severity", "Flag", "Party", "Date", "Amount", "Detail", "Law / reference", "Evidence",
           "Status", "Note", "Reviewed by"]
    ws.append(hdr)
    for c in ws[2]:
        c.font = Font(bold=True)
    fills = {"high": "FEE4E2", "medium": "FEF0C7", "low": "EEF4FF"}
    for f in sorted(flags, key=lambda f: (-SEV_SCORE[f.severity], f.rule)):
        ws.append([f.rule, GROUP_NAMES.get(f.group, ""), f.severity, f.title, f.party, _fmt(f.date), float(f.amount),
                   f.detail, f.law, "; ".join(map(str, f.refs[:10])), f.status.replace("_", " "), f.note, f.reviewer])
        ws.cell(ws.max_row, 3).fill = PatternFill("solid", fgColor=fills[f.severity])
    for col, w in zip("ABCDEFGHIJKLM", (6, 22, 9, 44, 30, 11, 14, 60, 34, 50, 12, 30, 22)):
        ws.column_dimensions[col].width = w
    wb.save(path)
