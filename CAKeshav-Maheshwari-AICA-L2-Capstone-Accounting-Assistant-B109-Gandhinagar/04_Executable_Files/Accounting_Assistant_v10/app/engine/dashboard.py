"""Home dashboard for one company: live money position from Tally + the app's own to-do counts."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import BankLine, Invoice
from . import entry, recurring
from .masters import Masters
from .periods import Period, fy_start

ZERO = Decimal(0)


@dataclass
class Dashboard:
    cash_bank: list = field(default_factory=list)          # [(ledger, balance Tally sign)]
    payables_week: list = field(default_factory=list)      # [(party, bill, due, amount)]
    receivables_overdue: list = field(default_factory=list)
    gst_payable: Decimal | None = None
    tds_payable: Decimal | None = None
    pending_invoices: int = 0
    pending_bank: int = 0
    recurring_due: list = field(default_factory=list)      # [(name, due)]
    errors: list = field(default_factory=list)


def _due(b: dict) -> str:
    if b.get("due"):
        return b["due"][:8]
    m = re.search(r"\d+", str(b.get("credit") or ""))
    if b.get("date") and m:
        d = datetime.strptime(b["date"][:8], "%Y%m%d") + timedelta(days=int(m.group(0)))
        return d.strftime("%Y%m%d")
    return b.get("date", "")[:8]


def local_counts(session: Session, company_id: str, period: Period, today: date | None = None) -> Dashboard:
    d = Dashboard()
    d.pending_invoices = session.scalar(select(func.count()).select_from(Invoice).where(
        Invoice.company_id == company_id, Invoice.status.not_in(["posted", "exception"]))) or 0
    d.pending_bank = session.scalar(select(func.count()).select_from(BankLine).where(
        BankLine.company_id == company_id, BankLine.status == "new",
        BankLine.date >= period.frm, BankLine.date <= period.to)) or 0
    d.recurring_due = [(r.name, r.next_due) for r in recurring.due(session, company_id, today, ahead_days=7)]
    return d


def fetch(client, session: Session, company, m: Masters, period: Period, today: date | None = None,
          progress=lambda s: None) -> Dashboard:
    today = today or date.today()
    d = local_counts(session, company.id, period, today)
    to = min(period.to, today.strftime("%Y%m%d"))
    fys = fy_start(period.end if period.end <= today else today).strftime("%Y%m%d")
    try:
        progress("Balances")
        closings = client.ledger_closings(company.name, fys, to)
        norm = lambda s: " ".join(str(s).lower().split())
        by_norm = {norm(n): v for n, v in closings.items()}
        rows = []
        for n in entry.cash_bank_ledgers(m, company):
            v = closings.get(n) or by_norm.get(norm(n))
            rows.append((n, v["closing"] if v else ZERO))
        # bank ledgers Tally knows that the local masters don't (created after the last Sync)
        known = {norm(n) for n, _ in rows}
        for n, v in closings.items():
            if norm(n) not in known and norm(v.get("parent", "")) in ("bank accounts", "bank od a/c", "cash-in-hand"):
                rows.append((n, v["closing"]))
        d.cash_bank = sorted(rows, key=lambda x: (x[1] == 0, x[1]))
        gst = tds = ZERO
        for n, v in closings.items():
            if m.ledgers.get(n, {}).get("_primary") != "Duties & Taxes":
                continue
            low = n.lower()
            if "tds" in low:
                tds += v["closing"]
            elif "tcs" in low:
                continue
            elif re.search(r"gst|cgst|sgst|igst|cess", low):
                gst += v["closing"]                    # output Cr (+) less input Dr (-)
        d.gst_payable, d.tds_payable = gst, tds
    except Exception as e:
        d.errors.append(f"Balances: {e}")
    try:
        progress("Bills")
        week = (today + timedelta(days=7)).strftime("%Y%m%d")
        t = today.strftime("%Y%m%d")
        for b in client.bills(company.name):
            due = _due(b)
            prim = m.ledgers.get(b["party"], {}).get("_primary", "")
            if b["amount"] > 0 and (prim == "Sundry Creditors" or not prim) and due and due <= week:
                d.payables_week.append((b["party"], b["name"], due, b["amount"]))
            elif b["amount"] < 0 and (prim == "Sundry Debtors" or not prim) and due and due < t:
                d.receivables_overdue.append((b["party"], b["name"], due, -b["amount"]))
        d.payables_week.sort(key=lambda x: x[2])
        d.receivables_overdue.sort(key=lambda x: x[2])
    except Exception as e:
        d.errors.append(f"Bills: {e}")
    return d


def activity(session: Session, company_id: str, days: int = 14, today: date | None = None) -> dict:
    """Day-by-day counts for the Home tiles' sparklines (local data, no Tally call):
    invoices read or updated, bank statement lines, and entries posted (the app's copy of the day book)."""
    from ..db.models import VoucherHistory
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    keys = [(start + timedelta(days=i)).strftime("%Y%m%d") for i in range(days)]
    out = {"invoices": dict.fromkeys(keys, 0), "bank": dict.fromkeys(keys, 0), "posted": dict.fromkeys(keys, 0)}
    lo = datetime.combine(start, datetime.min.time())
    for (ts,) in session.execute(select(Invoice.updated_at).where(Invoice.company_id == company_id,
                                                                  Invoice.updated_at >= lo)):
        k = ts.strftime("%Y%m%d")
        if k in out["invoices"]:
            out["invoices"][k] += 1
    for (d,) in session.execute(select(BankLine.date).where(BankLine.company_id == company_id,
                                                            BankLine.date >= keys[0], BankLine.date <= keys[-1])):
        if d in out["bank"]:
            out["bank"][d] += 1
    for (d,) in session.execute(select(VoucherHistory.date).where(VoucherHistory.company_id == company_id,
                                                                  VoucherHistory.date >= keys[0],
                                                                  VoucherHistory.date <= keys[-1])):
        if d in out["posted"]:
            out["posted"][d] += 1
    return {k: list(v.values()) for k, v in out.items()}
