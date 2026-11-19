"""Supplier context for the invoice screen: balance, recent entries, and copying a past entry onto a new invoice."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .history import vouchers as _hv
from ..db.models import VoucherHistory
from ..extract.schema import Invoice
from .masters import Masters
from .voucher import VLine, Voucher

Q = Decimal("0.01")


@dataclass
class PastEntry:
    vh: VoucherHistory
    amount: Decimal            # party-side amount
    party_dr: bool

    @property
    def label(self) -> str:
        d = self.vh.date
        return f"{d[6:8]}-{d[4:6]}-{d[:4]}"


def recent_entries(session: Session, company_id: str, party: str, limit: int = 5) -> list[PastEntry]:
    if not party:
        return []
    out = []
    from .history import index as _hidx
    rows = list(reversed(_hidx(session, company_id).by_ledger.get(party, [])))
    for v in rows:
        e = next((x for x in (v.entries or []) if x["ledger"] == party), None)
        if e:
            out.append(PastEntry(v, Decimal(e["amount"]).quantize(Q), e["dr"]))
            if len(out) >= limit:
                break
    return out


def balance_from_history(session: Session, company_id: str, party: str) -> Decimal:
    """Net movement in the synced period (Dr positive). Excludes opening balance: a fallback only."""
    net = Decimal(0)
    from .history import index as _hidx
    for v in _hidx(session, company_id).by_ledger.get(party, []):
        for e in v.entries or []:
            if e["ledger"] == party:
                net += Decimal(e["amount"]) if e["dr"] else -Decimal(e["amount"])
    return net


def fmt_balance(tally_sign_amount: Decimal) -> str:
    """Tally sign: negative = Dr."""
    v = tally_sign_amount
    return f"₹ {abs(v):,.2f} {'Dr' if v < 0 else 'Cr'}" if v else "₹ 0.00"


def _kind(ledger: str, m: Masters, party: str) -> str:
    low = ledger.lower()
    if ledger == party:
        return "party"
    if "tds" in low:
        return "tds"
    if re.search(r"round", low):
        return "round"
    if m.ledgers.get(ledger, {}).get("_primary") == "Duties & Taxes" or re.search(r"\b[csiu]t?gst\b|cess", low):
        if re.search(r"\bigst\b|integrated", low):
            return "igst"
        if re.search(r"\bcgst\b|central", low):
            return "cgst"
        if re.search(r"\b[su]t?gst\b|state|ut\s*tax", low):
            return "sgst"
        if "cess" in low:
            return "cess"
        return "tax_other"
    return "expense"


def copy_entry(past: VoucherHistory, inv: Invoice, m: Masters, party: str) -> Voucher:
    """Re-create a past entry for this invoice: same ledgers/type, this invoice's amounts."""
    ents = past.entries or []
    kinds = [(e, _kind(e["ledger"], m, party)) for e in ents]
    exp = [(e, Decimal(e["amount"])) for e, k in kinds if k == "expense" and e["dr"]]
    exp_total = sum((a for _, a in exp), Decimal(0))
    taxable = inv.taxable_total or (inv.grand_total - inv.tax_total - inv.round_off - inv.tcs)
    lines: list[VLine] = []
    # expenses: split this invoice's taxable value in the same proportions as last time
    run = Decimal(0)
    for i, (e, a) in enumerate(exp):
        amt = (taxable * a / exp_total).quantize(Q) if exp_total else Decimal(0)
        if i == len(exp) - 1:
            amt = (taxable - run).quantize(Q)
        run += amt
        lines.append(VLine(e["ledger"], amt, True, "expense", f"Copied from {past.voucher_type} {past.number}", "green"))
    heads = {"igst": inv.igst_total, "cgst": inv.cgst_total, "sgst": inv.sgst_total, "cess": inv.cess_total}
    used = set()
    for e, k in kinds:
        if k in heads and heads[k] and k not in used:
            lines.append(VLine(e["ledger"], heads[k].quantize(Q), e["dr"],
                               "gst_in" if e["dr"] else "gst_rcm_out", "This invoice's tax on last time's ledger",
                               "green"))
            used.add(k)
    for k, amt in heads.items():                               # tax head not present last time
        if amt and k not in used:
            lines.append(VLine("", amt.quantize(Q), True, "gst_in", f"{k.upper()} - pick ledger (not in copied entry)",
                               "red"))
    tds = next((e for e, k in kinds if k == "tds" and not e["dr"]), None)
    if tds and exp_total:
        rate = Decimal(tds["amount"]) * 100 / exp_total
        lines.append(VLine(tds["ledger"], (taxable * rate / 100).quantize(Decimal("1")), False, "tds",
                           f"TDS @ {rate.quantize(Decimal('0.01')).normalize()}% as in the copied entry", "green"))
    if inv.round_off:
        rl = next((e["ledger"] for e, k in kinds if k == "round"), "") or m.find(r"round", None)
        lines.append(VLine(rl, abs(inv.round_off), inv.round_off > 0, "round", "Round off", "green" if rl else "red"))
    dr = sum((l.amount for l in lines if l.dr), Decimal(0))
    cr = sum((l.amount for l in lines if not l.dr), Decimal(0))
    lines.insert(0, VLine(party, (dr - cr).quantize(Q), False, "party", "Balancing (supplier)", "green",
                          bill_ref=inv.invoice_no if m.ledgers.get(party, {}).get("ISBILLWISEON", "").lower() == "yes"
                          else ""))
    base = "Journal" if re.search(r"journal", past.voucher_type, re.I) else "Purchase"
    d = inv.invoice_date
    narr = (f"Being {'expense' if base == 'Journal' else 'purchase'} from {inv.supplier_name or party} vide Inv No. "
            f"{inv.invoice_no} dt. {d[6:8]}-{d[4:6]}-{d[:4]}") if len(d) == 8 else past.narration
    return Voucher(vtype=past.voucher_type, base_type=base, date=d or date.today().strftime("%Y%m%d"), lines=lines,
                   reference=inv.invoice_no, reference_date=inv.invoice_date, party=party, narration=narr)
