"""Typed entry for every Tally voucher type: Payment, Receipt, Contra, Sales, Purchase, Journal, Debit Note and
Credit Note. Mirrors Tally's own restrictions (cash/bank side of Payment / Receipt / Contra), splits GST by
place of supply, settles bills bill-wise, and respects each company's period lock."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from .history import vouchers as _hv
from ..db.models import AuditLog, Company, VoucherHistory
from ..gst_states import state_code
from .masters import Masters
from .voucher import VLine, Voucher

Q = Decimal("0.01")

# Tally's own cash/bank groups. Credit cards are treated as Bank OD / CC (user decision); card ledgers kept under
# any other group can be ticked per company ("Treat as bank/card", stored in company.settings["card_ledgers"]).
CASH_BANK_GROUPS = ("Bank Accounts", "Bank OD A/c", "Cash-in-Hand")

VOUCHER_TYPES = [
    # base type, Tally key, cash/bank side ("cr" = credit side locked, "dr", "both", "")
    ("Payment", "F5", "cr"),
    ("Receipt", "F6", "dr"),
    ("Contra", "F4", "both"),
    ("Sales", "F8", ""),
    ("Purchase", "F9", ""),
    ("Journal", "F7", ""),
    ("Debit Note", "Alt+F5", ""),
    ("Credit Note", "Alt+F6", ""),
]
CASH_SIDE = {b: s for b, _k, s in VOUCHER_TYPES}


def cash_bank_ledgers(m: Masters, company: Company | None = None) -> list[str]:
    extra = set((company.settings or {}).get("card_ledgers", []) if company else [])
    return sorted(n for n, d in m.ledgers.items() if d.get("_primary") in CASH_BANK_GROUPS or n in extra)


def is_cash_bank(m: Masters, company: Company | None, ledger: str) -> bool:
    return ledger in set(cash_bank_ledgers(m, company))


def voucher_type_names(m: Masters, base: str) -> list[str]:
    """Tally voucher types whose parent is this base type (custom types like 'Purchase GST' included)."""
    names = sorted(n for n, d in m.voucher_types.items() if n == base or d.get("_parent") == base)
    return names or [base]


def last_cash_bank(session: Session, company: Company, m: Masters, base: str) -> str:
    """Default for the cash/bank side: the one used most recently in this company for this voucher type."""
    from sqlalchemy import select
    cb = set(cash_bank_ledgers(m, company))
    types = set(voucher_type_names(m, base))
    for v in list(reversed(_hv(session, company.id)))[:400]:
        if v.voucher_type in types:
            for e in v.entries or []:
                if e["ledger"] in cb:
                    return e["ledger"]
    last = (company.settings or {}).get("last_cash_bank", {}).get(base, "")
    if last in cb:
        return last
    order = {"Bank Accounts": 0, "Bank OD A/c": 1, "Cash-in-Hand": 2}
    ranked = sorted(cb, key=lambda n: (order.get(m.ledgers.get(n, {}).get("_primary", ""), 3), n))
    return ranked[0] if ranked else ""


def check_restrictions(v: Voucher, m: Masters, company: Company | None) -> list[str]:
    """Tally-like rules for Payment / Receipt / Contra."""
    side = CASH_SIDE.get(v.base_type, "")
    if not side:
        return []
    cb = set(cash_bank_ledgers(m, company))
    out = []
    dr = [l for l in v.lines if l.dr]
    cr = [l for l in v.lines if not l.dr]
    if side == "cr" and not any(l.ledger in cb for l in cr):
        out.append("Payment: the credit side must be a bank, cash, CC/OD or credit card ledger")
    if side == "dr" and not any(l.ledger in cb for l in dr):
        out.append("Receipt: the debit side must be a bank, cash, CC/OD or credit card ledger")
    if side == "both" and any(l.ledger not in cb for l in v.lines if l.ledger):
        out.append("Contra: both sides must be bank, cash, CC/OD or credit card ledgers")
    return out


# ------------------------------------------------------------------ GST
def party_state(m: Masters, party: str) -> str:
    d = m.ledgers.get(party, {})
    g = d.get("_gstin", "")
    if len(g) == 15:
        return g[:2]
    return state_code(d.get("LEDSTATENAME", "")) or ""


def gst_lines(m: Masters, company: Company, party: str, taxable: Decimal, rate: Decimal, output: bool,
              dr: bool) -> list[VLine]:
    """CGST+SGST when the party is in the company's state (or unknown), IGST otherwise."""
    if not rate or not taxable:
        return []
    ours = state_code(company.state) or (company.gstin[:2] if company.gstin else "")
    theirs = party_state(m, party)
    inter = bool(ours and theirs and ours != theirs)
    word = "Output" if output else "Input"
    out = []
    if inter:
        amt = (taxable * rate / 100).quantize(Q)
        led = m.gst_ledger("igst", rate, output=output)
        out.append(VLine(led, amt, dr, "gst_out" if output else "gst_in", f"{word} IGST {rate}%",
                         "amber" if led else "red"))
    else:
        half = (taxable * rate / 200).quantize(Q)
        for head in ("cgst", "sgst"):
            led = m.gst_ledger(head, rate / 2, output=output)
            out.append(VLine(led, half, dr, "gst_out" if output else "gst_in", f"{word} {head.upper()} {rate / 2}%",
                             "amber" if led else "red"))
    return out


@dataclass
class ItemLine:
    """One line on the typed Sales / Purchase / note screen: a ledger (or stock item) with taxable value."""
    ledger: str                 # sales/purchase/expense ledger (accounting mode) or ledger for the stock item
    taxable: Decimal
    gst_rate: Decimal = Decimal(0)
    stock_item: str = ""
    qty: Decimal = Decimal(0)
    rate: Decimal = Decimal(0)
    uom: str = "Nos"


@dataclass
class EntryForm:
    base: str                                  # one of VOUCHER_TYPES
    vtype: str
    date: str                                  # YYYYMMDD
    party: str = ""                            # party / counter ledger
    cash_bank: str = ""                        # Payment / Receipt / Contra
    amount: Decimal = Decimal(0)               # Payment / Receipt / Contra amount
    items: list[ItemLine] = field(default_factory=list)
    reference: str = ""
    reference_date: str = ""
    narration: str = ""
    bills: list = field(default_factory=list)  # [(name, type, amount)] for the party line
    contra_to: str = ""                        # Contra: the other cash/bank ledger (debited)
    round_off_ledger: str = ""
    journal_lines: list[VLine] = field(default_factory=list)


def build(form: EntryForm, m: Masters, company: Company) -> Voucher:
    b = form.base
    v = Voucher(vtype=form.vtype or b, base_type=b, date=form.date, reference=form.reference,
                reference_date=form.reference_date, narration=form.narration)
    amt = form.amount.quantize(Q)
    if b == "Payment":
        v.lines = [_party(form, amt, True, m), VLine(form.cash_bank, amt, False, "bank", "Paid from", "green")]
        v.party = form.party
    elif b == "Receipt":
        v.lines = [VLine(form.cash_bank, amt, True, "bank", "Received in", "green"), _party(form, amt, False, m)]
        v.party = form.party
    elif b == "Contra":                         # money moves from cash_bank (Cr) to contra_to (Dr)
        v.lines = [VLine(form.contra_to, amt, True, "bank", "Deposited / transferred to", "green"),
                   VLine(form.cash_bank, amt, False, "bank", "Withdrawn / transferred from", "green")]
    elif b == "Journal":
        v.lines = list(form.journal_lines)
    else:
        # Sales: party Dr, income + output GST Cr      Credit Note (sales return): the reverse
        # Purchase: expense + input GST Dr, party Cr   Debit Note (purchase return): the reverse
        output = b in ("Sales", "Credit Note")
        party_dr = b in ("Sales", "Debit Note")
        body_dr = not party_dr
        lines: list[VLine] = []
        for it in form.items:
            lines.append(VLine(it.ledger, it.taxable.quantize(Q), body_dr, "income" if output else "expense",
                               it.stock_item or "", "green"))
        rates: dict[Decimal, Decimal] = {}
        for it in form.items:
            if it.gst_rate:
                rates[it.gst_rate] = rates.get(it.gst_rate, Decimal(0)) + it.taxable
        for rate, taxable in sorted(rates.items()):
            lines += gst_lines(m, company, form.party, taxable, rate, output, body_dr)
        gross = sum((l.amount for l in lines), Decimal(0))
        rounded = gross.quantize(Decimal("1"))
        if rounded != gross and form.round_off_ledger:
            diff = rounded - gross
            lines.append(VLine(form.round_off_ledger, abs(diff), body_dr if diff > 0 else not body_dr, "round",
                               "Round off", "green"))
            gross = rounded
        party = VLine(form.party, gross.quantize(Q), party_dr, "party", "Party", "green")
        _apply_bills(party, form, m)
        if party.bill_type == "" and not party.bills and form.reference and _billwise(m, form.party):
            party.bill_ref = form.reference                      # New Ref = invoice / note number
        v.lines = [party] + lines
        v.party = form.party
        from .voucher import InvLine
        stock = [it for it in form.items if it.stock_item]
        if stock:
            v.inventory = [InvLine(it.stock_item, it.qty, it.uom, it.rate, it.taxable.quantize(Q), it.ledger,
                                   dr=body_dr) for it in stock]
            v.lines = [l for l in v.lines if not (l.kind in ("income", "expense") and l.note)]
    return v


def _billwise(m: Masters, ledger: str) -> bool:
    return m.ledgers.get(ledger, {}).get("ISBILLWISEON", "").lower() == "yes"


def _party(form: EntryForm, amt: Decimal, dr: bool, m: Masters) -> VLine:
    line = VLine(form.party, amt, dr, "party", "Party", "green")
    _apply_bills(line, form, m)
    return line


def _apply_bills(line: VLine, form: EntryForm, m: Masters) -> None:
    if form.bills:
        line.bills = list(form.bills)
    elif _billwise(m, form.party) and form.base in ("Payment", "Receipt"):
        line.bill_type = "On Account"


# ------------------------------------------------------------------ bill-wise settlement
@dataclass
class OpenBill:
    name: str
    date: str                   # YYYYMMDD
    amount: Decimal             # outstanding, positive
    dr: bool                    # True = party owes us (receivable), False = we owe the party (payable)
    due: str = ""


def open_bills_from_history(session: Session, company_id: str, party: str) -> list[OpenBill]:
    """Offline fallback: New Ref minus Agst Ref from the synced vouchers (excludes opening bills)."""
    from sqlalchemy import select
    bal: dict[str, Decimal] = {}
    first: dict[str, str] = {}
    for v in _hv(session, company_id):
        for e in v.entries or []:
            if e["ledger"] != party:
                continue
            for b in e.get("bills", []):
                if b.get("type") not in ("New Ref", "Agst Ref") or not b.get("name"):
                    continue
                signed = Decimal(b["amount"])          # Tally sign: negative = Dr
                bal[b["name"]] = bal.get(b["name"], Decimal(0)) + signed
                first.setdefault(b["name"], v.date)
    return [OpenBill(n, first[n], abs(x), x < 0) for n, x in bal.items() if abs(x) >= Decimal("0.01")]


def allocate(bills: list[OpenBill], picked: dict[str, Decimal], total: Decimal) -> list[tuple]:
    """Agst Ref for the ticked bills (part payment allowed); anything left over goes On Account (advance)."""
    out, used = [], Decimal(0)
    for b in bills:
        a = picked.get(b.name)
        if a:
            a = min(a, b.amount)
            out.append((b.name, "Agst Ref", a.quantize(Q)))
            used += a
    rest = (total - used).quantize(Q)
    if rest > 0:
        out.append(("", "On Account", rest))
    return out


# ------------------------------------------------------------------ period lock
class PeriodLocked(Exception):
    pass


def lock_date(company: Company) -> str:
    return (company.settings or {}).get("lock_until", "")


def check_lock(session: Session, company: Company, v: Voucher, override_reason: str = "", actor: str = "") -> None:
    """Raises PeriodLocked unless a reason is given; an override is written to the audit log."""
    lu = lock_date(company)
    if not lu or v.date > lu:
        return
    if not override_reason.strip():
        raise PeriodLocked(f"Books of {company.name} are locked up to {lu[6:8]}-{lu[4:6]}-{lu[:4]}. "
                           f"Give a reason to post into a locked period.")
    session.add(AuditLog(company_id=company.id, action="lock_override", entity="vouchers",
                         after={"date": v.date, "vtype": v.vtype, "reason": override_reason.strip(),
                                "lock_until": lu}, updated_by=actor))
    session.commit()


def remember_cash_bank(session: Session, company: Company, base: str, ledger: str) -> None:
    st = dict(company.settings or {})
    last = dict(st.get("last_cash_bank", {}))
    last[base] = ledger
    st["last_cash_bank"] = last
    company.settings = st
    session.commit()


def today_str() -> str:
    return date.today().strftime("%Y%m%d")
