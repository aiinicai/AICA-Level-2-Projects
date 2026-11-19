"""Suggest the voucher for an invoice from learned memory + rules, and learn from approvals.

Confidence tiers: green = 2+ consistent approvals and no override in the last 3;
amber = one approval, warm-start or fuzzy match; red = nothing found / ledger missing in Tally.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .history import vouchers as _hv
from ..db.models import AuditLog, Company, MappingRule, Vendor, VoucherHistory, utcnow
from ..extract.schema import Invoice
from . import tds as tds_mod
from .masters import Masters
from .voucher import InvLine, VLine, Voucher

Q = Decimal("0.01")
DEFAULT_NARRATION = "Being {kind} from {supplier} vide Inv No. {inv_no} dt. {inv_date}"


def vendor_key(inv: Invoice) -> str:
    if inv.supplier_gstin:
        return inv.supplier_gstin
    if inv.supplier_pan:
        return f"PAN:{inv.supplier_pan}"
    return "NAME:" + re.sub(r"[^a-z0-9]", "", inv.supplier_name.lower())[:60]


def _keywords(text: str) -> list[str]:
    stop = {"and", "the", "for", "with", "from", "rs", "nos", "pcs", "qty", "rate", "amount", "total", "gst"}
    words = re.findall(r"[a-z]{3,}", text.lower())
    return [w for w, _ in Counter(w for w in words if w not in stop).most_common(5)]


def tier(rule: MappingRule | None) -> str:
    if rule is None:
        return "red"
    if rule.hits >= 2 and rule.overrides == 0 and rule.source == "user":
        return "green"
    return "amber"


@dataclass
class Suggestion:
    voucher: Voucher
    vendor: Vendor | None
    rule: MappingRule | None
    flags: list[str] = field(default_factory=list)       # compliance notes for the reviewer
    tds_note: str = ""


def _find_rule(session: Session, company_id: str, vkey: str, hsns: list[str], text: str) -> MappingRule | None:
    rules = session.scalars(select(MappingRule).where(MappingRule.company_id == company_id,
                                                      MappingRule.active.is_(True))).all()
    mine = [r for r in rules if r.vendor_key == vkey]
    if hsns:
        for r in sorted(mine, key=lambda r: -r.hits):
            if r.hsn and r.hsn[:4] in {h[:4] for h in hsns}:
                return r
    kws = set(_keywords(text))
    scored = sorted(mine, key=lambda r: (-len(kws & set(r.keywords or [])), -r.hits))
    if scored:
        return scored[0]
    if hsns:                                     # same HSN booked for another vendor
        for r in sorted(rules, key=lambda r: -r.hits):
            if r.hsn and r.hsn[:4] in {h[:4] for h in hsns}:
                return r
    return None


def suggest(session: Session, company: Company, m: Masters, inv: Invoice, today: date | None = None,
            style_override: str = "") -> Suggestion:
    cfg = company.settings or {}
    flags: list[str] = []
    vkey = vendor_key(inv)
    vendor = session.scalar(select(Vendor).where(Vendor.company_id == company.id, Vendor.vendor_key == vkey))

    # ---- party ledger
    party, p_conf, p_note = "", "red", "No matching party ledger"
    if vendor and vendor.party_ledger and vendor.party_ledger in m.ledgers:
        party, p_conf, p_note = vendor.party_ledger, "green", "Remembered for this vendor"
    elif inv.supplier_gstin and m.party_by_gstin(inv.supplier_gstin):
        party, p_conf, p_note = m.party_by_gstin(inv.supplier_gstin), "green", "GSTIN matches ledger in Tally"
    else:
        name, score = m.fuzzy(inv.supplier_name, m.names_under("Sundry Creditors", "Current Liabilities"))
        if name:
            party, p_conf, p_note = name, "amber", f"Name similar ({score:.0%}) to ledger"
    if inv.invoice_no:
        from .gstr2b import norm_no
        key = norm_no(inv.invoice_no)
        from .history import index as _hindex
        for vh in _hindex(session, company.id).by_ref.get(key, []):
            if norm_no(vh.reference) == key and (not party or vh.party == party or
                                                  any(e["ledger"] == party for e in vh.entries)):
                flags.append(f"DUPLICATE? Tally already has {vh.voucher_type} {vh.number} dated "
                             f"{vh.date[6:8]}-{vh.date[4:6]}-{vh.date[:4]} with reference {vh.reference}")
                break
    if not party:
        flags.append(f"{inv.supplier_name or inv.supplier_gstin} isn't a ledger in Tally yet: use 'Create supplier in Tally'")

    # ---- expense / purchase ledger
    rule = _find_rule(session, company.id, vkey, inv.hsn_codes, inv.raw_text)
    target, t_conf, t_note = "", "red", "No rule yet: pick a ledger"
    if rule and rule.target_name in m.ledgers | m.stock_items:
        target, t_conf = rule.target_name, tier(rule)
        t_note = f"Rule: {rule.hits} approval(s){', warm start from Tally history' if rule.source == 'warm_start' else ''}"
    elif rule:
        t_note = f"Rule points to '{rule.target_name}', which no longer exists in Tally"

    rcm = inv.reverse_charge or bool(vendor and vendor.rcm) or bool(rule and rule.rcm)
    blocked = bool(rule and rule.blocked_17_5)
    pending_2b = bool(company.itc_pending_2b)
    intra = (inv.supplier_gstin[:2] if inv.supplier_gstin else company.gstin[:2]) == \
        (inv.place_of_supply or company.gstin[:2])

    style = style_override or (vendor.voucher_style if vendor and vendor.voucher_style else "") \
        or company.voucher_style or "purchase_accounting"
    base_type = "Journal" if style == "journal" else "Purchase"
    vtype = cfg.get("voucher_type_name") or base_type
    v = Voucher(vtype=vtype, base_type=base_type, date=inv.invoice_date or date.today().strftime("%Y%m%d"),
                reference=inv.invoice_no, reference_date=inv.invoice_date, party=party)

    # ---- expense lines per tax slab (or one line)
    slabs = inv.taxes or []
    taxable_total = inv.taxable_total
    expense_lines: list[VLine] = []
    use_stock = style == "purchase_item" and inv.lines and all(l.qty for l in inv.lines)
    if use_stock:
        purchase_ledger = cfg.get("purchase_ledger") or m.find(r"purchase", "Purchase Accounts")
        for l in inv.lines:
            item, s = m.fuzzy(l.description, list(m.stock_items), 0.6)
            v.inventory.append(InvLine(item or l.description, l.qty, l.uom or "Nos", l.rate, l.taxable,
                                       purchase_ledger, (m.godowns or ["Main Location"])[0]))
            if not item:
                flags.append(f"No stock item matches '{l.description}'")
    else:
        if blocked:
            amt = inv.grand_total - inv.round_off - inv.tcs if inv.grand_total else taxable_total + inv.tax_total
            expense_lines.append(VLine(target, amt.quantize(Q), True, "expense",
                                       t_note + "; GST added to cost (blocked u/s 17(5))", t_conf))
        else:
            expense_lines.append(VLine(target, taxable_total.quantize(Q), True, "expense", t_note, t_conf))
    v.lines += expense_lines

    # ---- GST
    def gst_line(head: str, amt: Decimal, rate):
        if amt <= 0:
            return
        if rcm:
            inl = m.gst_ledger(head, rate, rcm=True)
            outl = m.gst_ledger(head, rate, rcm=True, output=True)
            v.lines.append(VLine(inl, amt, True, "gst_rcm_in", "RCM input", "amber" if inl else "red"))
            v.lines.append(VLine(outl, amt, False, "gst_rcm_out", "RCM output liability", "amber" if outl else "red"))
            return
        if blocked:
            return
        name = m.find(r"pending\s*2b|itc\s*pending", "Duties & Taxes") if pending_2b else ""
        name = name or m.gst_ledger(head, rate)
        v.lines.append(VLine(name, amt, True, "gst_in", f"Input {head.upper()} {rate or ''}%".strip(),
                             "green" if name else "red"))

    if rcm and not inv.tax_total and taxable_total:
        # unregistered supplier under RCM: compute tax at configured/default 18%
        rate = Decimal(str(cfg.get("rcm_default_rate", 18)))
        t = (taxable_total * rate / 100).quantize(Q)
        if intra:
            gst_line("cgst", (t / 2).quantize(Q), rate / 2)
            gst_line("sgst", (t / 2).quantize(Q), rate / 2)
        else:
            gst_line("igst", t, rate)
        flags.append(f"RCM computed at {rate}%: raise self-invoice (s.31(3)(f)) and pay in cash via GSTR-3B")
    elif len(slabs) > 1:
        for s in slabs:
            gst_line("igst", s.igst, s.rate)
            gst_line("cgst", s.cgst, s.rate / 2)
            gst_line("sgst", s.sgst, s.rate / 2)
    else:
        r = slabs[0].rate if slabs else None
        gst_line("igst", inv.igst_total, r)
        gst_line("cgst", inv.cgst_total, r / 2 if r else None)
        gst_line("sgst", inv.sgst_total, r / 2 if r else None)
    if inv.cess_total and not blocked:
        gst_line("cess", inv.cess_total, None)
    # one ledger used for several rates (e.g. a single 'Input CGST'): one line per ledger and side
    merged: list[VLine] = []
    for l in v.lines:
        same = next((x for x in merged if l.kind == "gst_in" and x.kind == "gst_in" and l.ledger and
                     x.ledger == l.ledger and x.dr == l.dr), None)
        if same:
            same.amount += l.amount
            same.note = f"{same.note}; {l.note}"
        else:
            merged.append(l)
    v.lines = merged
    if rcm and inv.tax_total:
        flags.append("Reverse charge: supplier should not charge GST; tax booked as RCM liability")

    # ---- TCS charged by supplier
    if inv.tcs:
        tcs_l = cfg.get("tcs_ledger") or m.find(r"tcs", None)
        v.lines.append(VLine(tcs_l, inv.tcs, True, "tcs", "TCS receivable", "amber" if tcs_l else "red"))

    # ---- party credit (gross, less TDS), TDS, round-off
    gross = inv.grand_total if inv.grand_total else taxable_total + inv.tax_total + inv.tcs + inv.round_off
    if rcm and inv.tax_total:
        gross -= inv.tax_total
    tds_amt, tds_note = Decimal(0), ""
    section = (vendor.tds_section if vendor else "") or (cfg.get("tds_by_ledger", {}).get(target, ""))
    if section and party:
        prior = tds_mod.paid_this_fy(session, company.id, party,
                                     datetime.strptime(v.date, "%Y%m%d").date())
        tds_amt, tds_note = tds_mod.compute(section, taxable_total, tds_mod.is_company_pan(inv.supplier_pan),
                                            prior, cfg.get("tds_sections"))
        if tds_amt:
            tds_l = (vendor.tds_ledger if vendor and vendor.tds_ledger else "") or \
                cfg.get("tds_ledgers", {}).get(section) or m.find(rf"tds.*{section[:4]}", "Duties & Taxes") \
                or m.find(r"tds", "Duties & Taxes")
            v.lines.append(VLine(tds_l, tds_amt, False, "tds", tds_note, "amber" if tds_l else "red"))
    elif party and vendor and vendor.tds_ledger and vendor.tds_rate and taxable_total:
        rate = Decimal(str(vendor.tds_rate)).quantize(Decimal("0.01"))
        tds_amt = (taxable_total * rate / 100).quantize(Decimal("1"))
        tds_note = f"TDS @ {rate.normalize()}% as approved before for this supplier"
        v.lines.append(VLine(vendor.tds_ledger, tds_amt, False, "tds", tds_note, "green"))
    elif party and taxable_total:
        hist = tds_mod.history_tds(session, company.id, party, m.ledgers)
        if hist:
            tds_amt = (taxable_total * hist["rate"] / 100).quantize(Decimal("1"))
            d = hist["last"]
            tds_note = (f"TDS @ {hist['rate'].normalize()}% to {hist['ledger']}, as in {hist['count']} past "
                        f"entr{'y' if hist['count'] == 1 else 'ies'} for this party (last {d[6:8]}-{d[4:6]}-{d[:4]})")
            v.lines.append(VLine(hist["ledger"], tds_amt, False, "tds", tds_note,
                                 "green" if hist["count"] >= 2 else "amber"))
    if inv.round_off:
        rl = cfg.get("round_off_ledger") or m.find(r"round", None)
        v.lines.append(VLine(rl, abs(inv.round_off), inv.round_off > 0, "round", "Round off",
                             "green" if rl else "red"))
    credit_days = vendor.credit_days if vendor and vendor.credit_days else 0
    if not credit_days:
        bcp = m.ledgers.get(party, {}).get("BILLCREDITPERIOD", "").split()
        credit_days = int(bcp[0]) if bcp and bcp[0].isdigit() else 0
    bill_wise = m.ledgers.get(party, {}).get("ISBILLWISEON", "").lower() == "yes"
    v.lines.insert(0, VLine(party, (gross - tds_amt).quantize(Q), False, "party", p_note, p_conf,
                            bill_ref=inv.invoice_no if bill_wise else "", credit_days=credit_days))

    # fix any paisa difference into round-off
    diff = (v.dr_total - v.cr_total).quantize(Q)
    if diff and abs(diff) <= 1:
        rl = cfg.get("round_off_ledger") or m.find(r"round", None)
        v.lines.append(VLine(rl, abs(diff), diff < 0, "round", "Paisa difference", "amber" if rl else "red"))

    if (inv.document_type or "").lower() == "credit_note":
        as_debit_note(v, inv, cfg, flags)

    tmpl = cfg.get("narration_template") or DEFAULT_NARRATION
    d = inv.invoice_date
    v.narration = tmpl.format(kind=("purchase return / credit note" if inv.document_type == "credit_note"
                                    else "purchase" if style != "journal" else "expense"),
                              supplier=inv.supplier_name or party, inv_no=inv.invoice_no,
                              inv_date=f"{d[6:8]}-{d[4:6]}-{d[:4]}" if len(d) == 8 else d,
                              gstin=inv.supplier_gstin)
    return Suggestion(v, vendor, rule, flags, tds_note)


def learn(session: Session, company: Company, inv: Invoice, v: Voucher, actor: str, save_rule: bool = True) -> None:
    """Record what the reviewer approved. Overrides bump the old rule's override count."""
    vkey = vendor_key(inv)
    party = next((l.ledger for l in v.lines if l.kind == "party"), v.party)
    vendor = session.scalar(select(Vendor).where(Vendor.company_id == company.id, Vendor.vendor_key == vkey))
    if vendor is None:
        vendor = Vendor(company_id=company.id, vendor_key=vkey, gstin=inv.supplier_gstin, pan=inv.supplier_pan,
                        names=[inv.supplier_name] if inv.supplier_name else [])
        session.add(vendor)
    vendor.party_ledger = party or vendor.party_ledger
    if inv.supplier_name and inv.supplier_name not in (vendor.names or []):
        vendor.names = (vendor.names or []) + [inv.supplier_name]
    if any(l.kind == "gst_rcm_in" for l in v.lines):
        vendor.rcm = True
    style = "journal" if v.base_type == "Journal" else ("purchase_item" if v.inventory else "purchase_accounting")
    vendor.voucher_style = "" if style == (company.voucher_style or "purchase_accounting") else style
    tds_line = next((l for l in v.lines if l.kind == "tds" or "tds" in (l.ledger or "").lower() and not l.dr), None)
    if tds_line and inv.taxable_total:
        vendor.tds_ledger = tds_line.ledger
        vendor.tds_rate = float((tds_line.amount * 100 / inv.taxable_total).quantize(Decimal("0.01")))
    elif not tds_line and vendor.tds_rate and not vendor.tds_section:
        vendor.tds_ledger, vendor.tds_rate = "", 0.0          # reviewer removed TDS: stop suggesting it
    if not save_rule:
        session.commit()
        return
    target = next((l.ledger for l in v.lines if l.kind == "expense"), "") or \
        (v.inventory[0].purchase_ledger if v.inventory else "")
    if not target:
        session.commit()
        return
    hsn = inv.hsn_codes[0] if inv.hsn_codes else ""
    blocked = any(l.kind == "expense" and "17(5)" in l.note for l in v.lines)
    rule = _find_rule(session, company.id, vkey, inv.hsn_codes, inv.raw_text)
    if rule and rule.vendor_key == vkey and rule.target_name == target:
        rule.hits += 1
        if rule.source == "warm_start":
            rule.source = "user"
    else:
        if rule and rule.vendor_key == vkey:
            rule.overrides += 1
            session.add(AuditLog(company_id=company.id, action="rule_override", entity="mapping_rules",
                                 entity_id=rule.id, before={"target": rule.target_name}, after={"target": target},
                                 updated_by=actor))
        rule = MappingRule(company_id=company.id, vendor_key=vkey, hsn=hsn, keywords=_keywords(inv.raw_text),
                           target_name=target, hits=1, source="user", blocked_17_5=blocked)
        session.add(rule)
    rule.last_used = utcnow()
    session.commit()


def warm_start(session: Session, company: Company, m: Masters) -> int:
    """Seed vendor -> ledger rules from the last 12 months of Tally purchase/journal vouchers. Rules
    start amber (source=warm_start) until a user approves one."""
    counts: dict[str, Counter] = defaultdict(Counter)
    for vh in _hv(session, company.id):
        if re.search(r"payment|receipt|contra|sales", vh.voucher_type, re.I):
            continue
        parties = [e for e in vh.entries if not e["dr"] and m.ledgers.get(e["ledger"], {}).get("_gstin")]
        if not parties:
            continue
        gstin = m.ledgers[parties[0]["ledger"]]["_gstin"].upper()
        for e in vh.entries:
            if e["dr"] and m.ledgers.get(e["ledger"], {}).get("_primary") in (
                    "Direct Expenses", "Indirect Expenses", "Purchase Accounts", "Fixed Assets"):
                counts[gstin][e["ledger"]] += 1
    added = 0
    existing = {(r.vendor_key, r.target_name) for r in session.scalars(
        select(MappingRule).where(MappingRule.company_id == company.id))}
    for gstin, c in counts.items():
        ledger, n = c.most_common(1)[0]
        if (gstin, ledger) in existing:
            continue
        session.add(MappingRule(company_id=company.id, vendor_key=gstin, target_name=ledger, hits=n,
                                source="warm_start"))
        party = m.party_by_gstin(gstin)
        if party and not session.scalar(select(Vendor).where(Vendor.company_id == company.id,
                                                             Vendor.vendor_key == gstin)):
            session.add(Vendor(company_id=company.id, vendor_key=gstin, gstin=gstin, party_ledger=party,
                               names=[party]))
        added += 1
    session.commit()
    return added


def as_debit_note(v: Voucher, inv: Invoice, cfg: dict, flags: list[str]) -> Voucher:
    """A supplier's credit note is a Debit Note in the buyer's books: every side reverses (party Dr, expense /
    stock and input GST Cr). TDS is not reversed automatically. The party line is set against the original bill
    when the note names it."""
    tds = [l for l in v.lines if l.kind == "tds"]
    party = next((l for l in v.lines if l.kind == "party"), None)
    if tds and party:
        party.amount += sum((l.amount for l in tds), Decimal(0))
        flags.append("TDS deducted on the original bill is not reversed here: adjust it in the next TDS payment "
                     "if needed")
    v.lines = [l for l in v.lines if l.kind != "tds"]
    for l in v.lines:
        l.dr = not l.dr
    for i in v.inventory:
        i.dr = not i.dr
    if v.base_type != "Journal":
        v.base_type = "Debit Note"
        v.vtype = cfg.get("debit_note_type_name") or "Debit Note"
    if party and inv.original_invoice_no:
        party.bill_ref, party.bills = "", [(inv.original_invoice_no, "Agst Ref", party.amount)]
        party.credit_days = 0
    elif party:
        flags.append("Credit note doesn't name the original invoice: set the bill reference before posting")
    return v


def apply_blocked_credit(v: Voucher) -> Voucher:
    """Reviewer marked ITC as not claimable (s.17(5)): fold input GST into the expense line."""
    gst = [l for l in v.lines if l.kind == "gst_in"]
    exp = next((l for l in v.lines if l.kind == "expense"), None)
    if not gst or exp is None:
        return v
    exp.amount += sum((l.amount for l in gst), Decimal(0))
    exp.note += "; GST added to cost (blocked u/s 17(5))"
    v.lines = [l for l in v.lines if l.kind != "gst_in"]
    return v
