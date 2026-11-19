"""Export receivables in foreign currency (USD clients): invoice register, realisation, exchange difference,
FIRC / e-BRC, LUT, the 9-month realisation watch (FEMA), and month-end revaluation.

Everything is read from the day book the app already has (Sync keeps the foreign amount and rate of each entry).
The proposed entries follow the office's own practice seen in Tally: for each realised invoice a 'Forex' voucher
Dr/Cr <client> (Agst Ref <invoice>) / Cr/Dr 'Forex Gain Or Loss' for the exchange difference."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Company, ExportRecord
from .masters import Masters
from .voucher import Q, Voucher, VLine

ZERO = Decimal(0)
BASE = ("", "₹", "inr", "rs", "rs.", "rupees", "?")


@dataclass
class ExInvoice:
    key: str             # invoice number (or Tally GUID)
    party: str
    date: str
    cur: str
    fc: Decimal
    rate: Decimal        # booked rate
    inr: Decimal
    guid: str = ""
    received_fc: Decimal = ZERO
    realised_inr: Decimal = ZERO      # foreign received x receipt rate
    booked_diff: Decimal = ZERO       # exchange difference already entered in Tally (Cr = gain positive)
    receipts: list = field(default_factory=list)   # (receipt guid, date, fc, rate)

    @property
    def outstanding_fc(self) -> Decimal:
        return max(ZERO, self.fc - self.received_fc)

    @property
    def diff(self) -> Decimal:
        """Realised exchange gain (+) / loss (-) on what has been received."""
        return (self.realised_inr - self.received_fc * self.rate).quantize(Q)

    @property
    def pending_diff(self) -> Decimal:
        return (self.diff - self.booked_diff).quantize(Q)

    @property
    def due_9m(self) -> str:
        y, m, d = int(self.date[:4]), int(self.date[4:6]), int(self.date[6:8])
        m += 9
        y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
        import calendar
        return f"{y}{m:02d}{min(d, calendar.monthrange(y, m)[1]):02d}"

    def status(self, today: date) -> str:
        if self.outstanding_fc <= Decimal("0.01"):
            return "realised"
        left = (date(int(self.due_9m[:4]), int(self.due_9m[4:6]), int(self.due_9m[6:8])) - today).days
        if left < 0:
            return "overdue"
        return "due soon" if left <= 30 else ("part received" if self.received_fc else "outstanding")


@dataclass
class ExReceipt:
    guid: str
    party: str
    date: str
    cur: str
    fc: Decimal
    rate: Decimal
    inr: Decimal
    bank: str
    bills: list
    narration: str = ""
    record: ExportRecord | None = None


def forex_ledgers(m: Masters, session: Session | None = None, company_id: str = "") -> dict:
    """ledger -> currency symbol, from the ledger master (CURRENCYNAME) or from foreign entries in the day book."""
    out = {}
    for n, d in m.ledgers.items():
        cur = str(d.get("CURRENCYNAME", "") or "").strip()
        if cur and cur.lower() not in BASE:
            out[n] = cur
    if session is not None and company_id:
        from . import history
        for v in history.vouchers(session, company_id):
            for e in v.entries or []:
                if e.get("fc") and e["ledger"] not in out and m.ledgers.get(e["ledger"], {}).get("_primary") in (
                        "Sundry Debtors", "Sundry Creditors"):
                    out[e["ledger"]] = e.get("cur") or "$"
    return out


def register(session: Session, company: Company, m: Masters, today: date | None = None
             ) -> tuple[list[ExInvoice], list[ExReceipt]]:
    from . import history
    today = today or date.today()
    fx = forex_ledgers(m, session, company.id)
    debtors = {n for n in fx if m.ledgers.get(n, {}).get("_primary") == "Sundry Debtors"}
    recs = {r.voucher_guid: r for r in session.scalars(select(ExportRecord).where(ExportRecord.company_id == company.id))}
    invoices: dict = {}
    receipts: list[ExReceipt] = []
    diffs: list = []                                    # (party, bill name, Cr-positive amount)
    for v in history.vouchers(session, company.id):
        for e in v.entries or []:
            if e["ledger"] not in debtors:
                continue
            fc = Decimal(e.get("fc") or "0")
            inr = Decimal(e["amount"])
            if e["dr"] and fc:
                key = v.number or v.reference or v.guid
                invoices[(e["ledger"], key)] = ExInvoice(key, e["ledger"], v.date, e.get("cur") or fx[e["ledger"]],
                                                         fc, Decimal(e.get("rate") or "0") or (inr / fc).quantize(
                                                             Decimal("0.0001")), inr, v.guid)
            elif not e["dr"] and fc:
                bank = next((x["ledger"] for x in v.entries if x["dr"] and x["ledger"] not in debtors), "")
                receipts.append(ExReceipt(v.guid, e["ledger"], v.date, e.get("cur") or fx[e["ledger"]], fc,
                                          Decimal(e.get("rate") or "0") or (inr / fc).quantize(Decimal("0.0001")),
                                          inr, bank, [b.get("name", "") for b in e.get("bills", []) if b.get("name")],
                                          v.narration or "", recs.get(v.guid)))
            elif not fc and inr:
                # exchange difference entered in Tally (party Dr = gain, as Tally users book 'Forex' vouchers)
                names = [b.get("name", "") for b in e.get("bills", []) if b.get("name")]
                diffs.append((e["ledger"], names[0] if names else "", inr if e["dr"] else -inr))
    # allocate receipts to invoices: saved allocation > bill reference in Tally > oldest first
    open_inv = sorted(invoices.values(), key=lambda i: (i.party, i.date, i.key))
    for r in sorted(receipts, key=lambda r: r.date):
        left = r.fc
        plan = []
        if r.record and r.record.allocation:
            plan = [(k, Decimal(str(a))) for k, a in r.record.allocation.items()]
        else:
            for name in r.bills:
                inv = invoices.get((r.party, name))
                if inv and inv.outstanding_fc:
                    plan.append((name, min(left, inv.outstanding_fc)))
                    left -= plan[-1][1]
            for inv in open_inv:
                if left <= 0:
                    break
                if inv.party == r.party and inv.outstanding_fc and inv.key not in [p[0] for p in plan]:
                    take = min(left, inv.outstanding_fc)
                    plan.append((inv.key, take))
                    left -= take
        for key, fc in plan:
            inv = invoices.get((r.party, key))
            if not inv or fc <= 0:
                continue
            inv.received_fc += fc
            inv.realised_inr += (fc * r.rate).quantize(Q)
            inv.receipts.append((r.guid, r.date, fc, r.rate))
    for party, name, amt in diffs:
        inv = invoices.get((party, name))
        if inv:
            inv.booked_diff += amt
    return sorted(invoices.values(), key=lambda i: (i.date, i.key)), receipts


def revaluation(invoices: list[ExInvoice], rate: Decimal) -> dict:
    """party -> unrealised gain (+) / loss (-) on the foreign amount still outstanding at `rate`."""
    out: dict = {}
    for i in invoices:
        if i.outstanding_fc > 0:
            out[i.party] = out.get(i.party, ZERO) + ((rate - i.rate) * i.outstanding_fc).quantize(Q)
    return out


def gain_loss_ledger(m: Masters) -> str:
    for want in ("forex gain", "exchange", "forex", "fluctuation"):
        for n in sorted(m.ledgers):
            if want in n.lower() and m.ledgers[n].get("_primary") in ("Indirect Expenses", "Indirect Incomes",
                                                                      "Direct Expenses", "Direct Incomes"):
                return n
    return "Forex Gain Or Loss"


def forex_voucher(m: Masters, company: Company, party: str, cur: str, amount: Decimal, on: str, bill: str = "",
                  narration: str = "") -> Voucher:
    """amount: gain (+) / loss (-). Party Dr for a gain, with a zero foreign amount (Tally's way of carrying an
    exchange difference); voucher type 'Forex' when the company has it, else Journal."""
    vt = "Forex" if "Forex" in m.voucher_types else "Journal"
    gain = amount > 0
    a = abs(amount).quantize(Q)
    pl = VLine(party, a, gain, "party", "", "green", fx_cur=cur, fx_qty=Decimal(0), fx_rate=None)
    if bill:
        pl.bills = [(bill, "Agst Ref", a)]
    gl = VLine(gain_loss_ledger(m), a, not gain, "other", "", "green")
    return Voucher(vt, on, [pl, gl] if gain else [gl, pl], party=party,
                   narration=narration or f"Exchange {'gain' if gain else 'loss'} on {bill or party}", base_type="Journal")


def save_record(session: Session, company_id: str, guid: str, **kw) -> ExportRecord:
    r = session.scalar(select(ExportRecord).where(ExportRecord.company_id == company_id,
                                                  ExportRecord.voucher_guid == guid))
    if r is None:
        r = ExportRecord(company_id=company_id, voucher_guid=guid)
        session.add(r)
    for k, v in kw.items():
        setattr(r, k, v)
    session.commit()
    return r


def lut(company: Company) -> dict:
    return dict((company.settings or {}).get("lut", {}))


def lut_status(company: Company, today: date | None = None) -> str:
    today = today or date.today()
    l = lut(company)
    if not l.get("no"):
        return "No LUT entered - exports of services without IGST need a valid LUT for the year"
    to = l.get("to", "")
    if to and to < today.strftime("%Y%m%d"):
        return f"LUT {l['no']} expired on {to[6:8]}-{to[4:6]}-{to[:4]} - file the new one"
    return f"LUT {l['no']} valid" + (f" till {to[6:8]}-{to[4:6]}-{to[:4]}" if to else "")


def parse_remittance(narration: str) -> tuple[Decimal, Decimal, str] | None:
    """Bank narration 'INW ... USD50000.0@95.1625' -> (50000.0, 95.1625, 'USD'). Read on this PC only."""
    import re
    m_ = re.search(r"\b(USD|EUR|GBP|AUD|CAD|SGD|AED|JPY)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*@\s*([0-9]+(?:\.[0-9]+)?)",
                   narration or "", re.I)
    if not m_:
        return None
    return Decimal(m_.group(2).replace(",", "")), Decimal(m_.group(3)), m_.group(1).upper()


def to_excel(invoices: list[ExInvoice], receipts: list[ExReceipt], path, today: date | None = None) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    today = today or date.today()
    wb = Workbook()
    ws = wb.active
    ws.title = "Export invoices"
    hdr = ["Invoice", "Date", "Client", "Cur", "Foreign amt", "Booked rate", "INR booked", "Received (foreign)",
           "Outstanding (foreign)", "Realised INR", "Exchange diff", "Entered in Tally", "Still to enter",
           "Realise by (9 months)", "Status"]
    ws.append(hdr)
    for c in ws[1]:
        c.font = Font(bold=True)
    d = lambda s: f"{s[6:8]}-{s[4:6]}-{s[:4]}" if s else ""
    for i in invoices:
        ws.append([i.key, d(i.date), i.party, i.cur, float(i.fc), float(i.rate), float(i.inr), float(i.received_fc),
                   float(i.outstanding_fc), float(i.realised_inr), float(i.diff), float(i.booked_diff),
                   float(i.pending_diff), d(i.due_9m), i.status(today)])
    ws2 = wb.create_sheet("Receipts")
    ws2.append(["Date", "Client", "Cur", "Foreign amt", "Rate", "INR", "Bank", "FIRC no", "FIRC date", "e-BRC no",
                "e-BRC date"])
    for c in ws2[1]:
        c.font = Font(bold=True)
    for r in receipts:
        rec = r.record
        ws2.append([d(r.date), r.party, r.cur, float(r.fc), float(r.rate), float(r.inr), r.bank,
                    rec.firc_no if rec else "", d(rec.firc_date) if rec else "", rec.ebrc_no if rec else "",
                    d(rec.ebrc_date) if rec else ""])
    wb.save(path)
