"""'Check this company' - read-only checks of the app against live Tally, so a wrong figure is caught before
anyone relies on it. Nothing is written to Tally.

collect() does every Tally read (background thread); evaluate() compares with the app's own data (UI thread).
With a capture folder, every request and Tally's raw reply are saved - those files become real-data tests."""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

ZERO = Decimal(0)


@dataclass
class Check:
    status: str          # ok | warn | err | info
    title: str
    detail: str = ""


@dataclass
class Remote:
    company_loaded: bool = False
    companies: list = field(default_factory=list)
    tally_ids: set | None = None
    reports: object = None
    sch3: object = None
    bank_closings: dict = field(default_factory=dict)          # ledger -> (as_on, closing) or error text
    numbers: dict = field(default_factory=dict)                # voucher type -> [(number, date)]
    errors: dict = field(default_factory=dict)                 # step -> message
    capture_dir: str = ""


def recording(client, folder: Path):
    """A copy of the Tally client that saves each request and reply into folder."""
    from ..tally.client import TallyClient
    rc = TallyClient(client.host, client.port, client.timeout)
    folder.mkdir(parents=True, exist_ok=True)
    n = [0]
    orig = rc._post

    def _post(xml: str) -> bytes:
        n[0] += 1
        body = orig(xml)
        tag = ""
        for key in ("<ID>", 'COLLECTION NAME="'):
            if key in xml:
                tag = xml.split(key, 1)[1].split("<" if key == "<ID>" else '"', 1)[0]
                break
        safe = "".join(ch for ch in tag if ch.isalnum())[:40] or "reply"
        (folder / f"{n[0]:02d}_{safe}_request.xml").write_text(xml, encoding="utf-8")
        (folder / f"{n[0]:02d}_{safe}_reply.xml").write_bytes(body)
        return body
    rc._post = _post
    return rc


def collect(client, company: str, fy_from: str, today: str, mapping: dict, ledgers: dict, banks: dict,
            vtypes: list[str], capture: Path | None = None, progress=lambda m: None) -> Remote:
    """banks: bank ledger -> statement as-on date (YYYYMMDD)."""
    from . import reports, sch3
    if capture is not None:
        client = recording(client, capture)
    r = Remote(capture_dir=str(capture or ""))

    def step(name, fn):
        progress(name)
        try:
            return fn()
        except Exception as e:                       # one failing check must not stop the others
            r.errors[name] = str(e)[:300]
            return None
    comps = step("Companies open in Tally", client.companies) or []
    r.companies = [c["name"] for c in comps]
    r.company_loaded = any(c.strip().lower() == company.strip().lower() for c in r.companies)
    if not r.company_loaded:
        return r
    r.tally_ids = step("Day book completeness", lambda: client.voucher_ids(company, fy_from, today))
    r.reports = step("Trial Balance / P&L / Balance Sheet", lambda: reports.fetch(client, company, fy_from, today))
    r.sch3 = step("Schedule III", lambda: sch3.fetch(client, company, fy_from, today, ledgers, mapping))
    for bl, as_on in banks.items():
        res = step(f"Bank balance: {bl}", lambda bl=bl, as_on=as_on: client.ledger_balance(company, bl, fy_from, as_on))
        r.bank_closings[bl] = (as_on, res["closing"] if res else None)
    for vt in vtypes:
        r.numbers[vt] = step(f"Voucher numbers: {vt}", lambda vt=vt: client.voucher_numbers(company, vt, fy_from, today)) or []
    return r


def evaluate(session: Session, company, r: Remote, local_ids: set, history_count: int,
             numbering_methods: dict, last_sync: str = "") -> list[Check]:
    from . import bank, numbering
    out: list[Check] = []
    if r.errors.get("Companies open in Tally"):
        return [Check("err", "Tally not reachable", r.errors["Companies open in Tally"])]
    if not r.company_loaded:
        return [Check("err", f"{company.name} is not open in Tally",
                      "Open it in Tally (F3) and run the check again. Open now: " + (", ".join(r.companies) or "none"))]
    out.append(Check("ok", "Tally reachable and company open"))

    # day book completeness
    if r.tally_ids is None:
        out.append(Check("warn", "Could not count Tally's vouchers", r.errors.get("Day book completeness", "")))
    else:
        missing = r.tally_ids - local_ids
        gone = {i for i in local_ids if i} - r.tally_ids
        if missing or gone:
            out.append(Check("warn", "The app's copy of the day book is out of date",
                             f"{len(missing)} voucher(s) in Tally are not in the app"
                             + (f", {len(gone)} in the app were changed or deleted in Tally" if gone else "")
                             + ". Press Sync Tally." + (f" Last sync: {last_sync}." if last_sync else "")))
        else:
            out.append(Check("ok", "Day book in the app matches Tally", f"{len(r.tally_ids)} vouchers this year"))

    # reports
    rep = r.reports
    if rep is None:
        out.append(Check("err", "Reports could not be built", r.errors.get("Trial Balance / P&L / Balance Sheet", "")))
    else:
        if rep.tb_mismatch:
            names = ", ".join(m[0] for m in rep.tb_mismatch[:6])
            out.append(Check("err", "Trial Balance differs from Tally's own Trial Balance",
                             f"Lines: {names}. Diagnostics saved; send them over."))
        elif rep.tally_tb:
            out.append(Check("ok", "Trial Balance matches Tally line by line",
                             f"Dr = Cr = {rep.tb_dr:,.2f}"))
        else:
            out.append(Check("warn", "Tally's Trial Balance could not be read for comparison",
                             "; ".join(n for n in rep.notes if "Trial Balance" in n)))
        diff = [n for n in rep.notes if n.startswith("Difference")]
        out.append(Check("err", "Balance Sheet does not balance", diff[0]) if diff else
                   Check("ok", "Balance Sheet balances", f"Net profit this year {rep.net_profit:,.2f}"))
        fx = [n for n in rep.trial_balance if n.name.lower().startswith("unadjusted forex")]
        if fx:
            out.append(Check("info", "Foreign-currency balances present",
                             f"Tally's revaluation line 'Unadjusted Forex Gain/Loss' {abs(fx[0].amount):,.2f} "
                             f"{'Dr' if fx[0].amount < 0 else 'Cr'} is included in the TB and Balance Sheet."))
    st = r.sch3
    if st is None:
        out.append(Check("warn", "Schedule III could not be built", r.errors.get("Schedule III", "")))
    else:
        gap = st.totals["eq_c"] - st.totals["as_c"]
        out.append(Check("ok" if abs(gap) < Decimal("0.01") else "err",
                         "Schedule III Balance Sheet " + ("balances" if abs(gap) < Decimal("0.01")
                                                          else f"differs by {abs(gap):,.2f}"),
                         " · ".join(st.notes)))

    # bank balances
    for bl, (as_on, closing) in r.bank_closings.items():
        if closing is None:
            out.append(Check("warn", f"{bl}: Tally balance not read", r.errors.get(f"Bank balance: {bl}", "")))
            continue
        chk = bank.balance_check(session, company.id, bl, closing, as_on)
        if chk.statement is None:
            continue
        d = chk.statement + chk.tally
        on = f"{as_on[6:8]}-{as_on[4:6]}-{as_on[:4]}"
        if abs(d) < Decimal("0.01"):
            out.append(Check("ok", f"{bl} agrees with the statement on {on}", f"{chk.statement:,.2f}"))
        else:
            out.append(Check("warn", f"{bl} differs from the statement on {on} by {abs(d):,.2f}",
                             f"{len(chk.pending_lines)} statement line(s) not posted, {len(chk.tally_only)} Tally "
                             f"entr(ies) not on the statement - see Bank > Check balance > Details"))

    # voucher numbering
    for vt, nums in r.numbers.items():
        method = numbering_methods.get(vt, "")
        if numbering.needs_number(method):
            nxt = numbering.next_number(session, company.id, vt, _dt.date.today().strftime("%Y%m%d"), nums)
            out.append(Check("info", f"{vt}: numbering '{method}'",
                             f"The app sends the number itself - next would be {nxt}."))
    if not company.gstin:
        out.append(Check("warn", "No GSTIN on this company", "Set it in Setup > Company (needed for GST checks)."))
    if r.capture_dir:
        out.append(Check("info", "Tally's replies saved for testing", r.capture_dir))
    return out


def local_state(session: Session, company_id: str, fy_from: str, today: str) -> tuple[set, int]:
    from . import history
    vs = [v for v in history.vouchers(session, company_id) if fy_from <= v.date <= today]
    # vouchers posted by the app carry Tally's own id (LASTVCHID = MASTERID), so they count too
    return {str(v.masterid) for v in vs if v.masterid}, len(vs)


def bank_dates(session: Session, company_id: str) -> dict:
    from ..db.models import BankLine
    from .bank import statement_closing
    out = {}
    banks = set(session.scalars(select(BankLine.bank_ledger).where(BankLine.company_id == company_id)))
    for bl in banks:
        lines = list(session.scalars(select(BankLine).where(BankLine.company_id == company_id,
                                                            BankLine.bank_ledger == bl)))
        as_on, _c = statement_closing(lines)
        if as_on:
            out[bl] = as_on
    return out
