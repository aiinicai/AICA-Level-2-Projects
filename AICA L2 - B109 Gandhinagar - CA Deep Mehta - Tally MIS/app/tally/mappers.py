"""Turn Tally XML records into clean Python records (ported from mappers.ts).

Amounts leave here as canonical debit-positive paise. Returned objects are plain data: the XML element they came
from can be released straight away.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from lxml import etree

from .values import (canonical_paise, clean_text, parse_bool, parse_credit_period, parse_qty, parse_rate,
                     parse_tally_date, tally_paise)
from .xmlstream import View

El = etree._Element


def num(s: str | None):
    if s is None or s.strip() == "":
        return None
    try:
        f = float(s.strip())
    except ValueError:
        return None
    return int(f) if f == int(f) else f


def name_of(n: El, v: View | None = None) -> str:
    a = n.get("NAME")
    return clean_text(a if a is not None else (v or View(n)).txt("NAME"))


def parent_of(n: El, v: View | None = None) -> str | None:
    p = clean_text((v or View(n)).txt("PARENT"))
    return p if p and p != "\u0004 Primary" and p.lower() != "primary" else None


def bool_or_none(v: View, tag: str):
    x = v.txt(tag)
    return None if x is None else parse_bool(x)


@dataclass(slots=True)
class Bill:
    name: str
    bill_type: str
    amount_paise: int
    bill_date: str | None = None
    credit_days: int | None = None
    due_date: str | None = None


@dataclass(slots=True)
class VoucherLine:
    ledger_name: str
    amount_paise: int
    cost_allocations: list[dict] = field(default_factory=list)
    bills: list[Bill] = field(default_factory=list)


@dataclass(slots=True)
class InvLine:
    item_name: str
    direction: str
    qty_e4: int
    billed_qty_e4: int | None
    unit: str | None
    rate_paise: int | None
    value_paise: int
    godown: str | None = None
    batch: str | None = None
    mfg_date: str | None = None
    expiry_date: str | None = None
    ledger_name: str | None = None


@dataclass(slots=True)
class Voucher:
    source_key: str
    guid: str | None
    master_id: int | None
    alter_id: int | None
    date: str
    voucher_type: str
    number: str | None
    reference: str | None
    party_name: str | None
    narration: str | None
    is_cancelled: bool
    is_optional: bool
    is_postdated: bool
    is_invoice: bool
    lines: list[VoucherLine]
    inventory: list[InvLine]
    warnings: list[str]


def map_company(n: El) -> dict:
    v = View(n)
    return {"name": name_of(n, v), "guid": v.txt("GUID"), "books_from": parse_tally_date(v.txt("BOOKSFROM")),
            "starting_from": parse_tally_date(v.txt("STARTINGFROM")),
            "last_voucher_date": parse_tally_date(v.txt("LASTVOUCHERDATE")),
            "currency": v.txt("BASECURRENCYSYMBOL", "CURRENCYNAME")}


def map_group(n: El) -> dict:
    v = View(n)
    return {"name": name_of(n, v), "parent": parent_of(n, v), "is_revenue": bool_or_none(v, "ISREVENUE"),
            "affects_gross_profit": bool_or_none(v, "AFFECTSGROSSPROFIT"),
            "is_deemed_positive": bool_or_none(v, "ISDEEMEDPOSITIVE"), "guid": v.txt("GUID"),
            "alter_id": num(v.txt("ALTERID"))}


def map_bill(b: El, opening: bool) -> Bill:
    v = View(b)
    cp = parse_credit_period(v.txt("BILLCREDITPERIOD"))
    amount = v.txt("OPENINGBALANCE", "AMOUNT") if opening else v.txt("AMOUNT")
    bill_type = clean_text(v.txt("BILLTYPE")) or ("Advance" if parse_bool(v.txt("ISADVANCE"))
                                                  else "New Ref" if opening else "On Account")
    return Bill(clean_text(v.txt("NAME")) or "(unnamed)", bill_type, canonical_paise(amount),
                parse_tally_date(v.txt("BILLDATE")), cp.get("days"), cp.get("due_date"))


def map_ledger(n: El) -> dict:
    v = View(n)
    closing_raw = v.txt("CLOSINGBALANCE")
    limit = tally_paise(v.txt("CREDITLIMIT"))
    cvs = []
    for c in v.kids("LEDGERCLOSINGVALUES.LIST"):
        cv = View(c)
        d = parse_tally_date(cv.txt("DATE"))
        if d is not None:
            cvs.append({"date": d, "amount_paise": canonical_paise(cv.txt("AMOUNT"))})
    return {
        "name": name_of(n, v), "parent": parent_of(n, v), "guid": v.txt("GUID"), "master_id": num(v.txt("MASTERID")),
        "alter_id": num(v.txt("ALTERID")), "opening_paise": canonical_paise(v.txt("OPENINGBALANCE")),
        "closing_paise": None if closing_raw is None or closing_raw.strip() == "" else canonical_paise(closing_raw),
        "is_billwise": parse_bool(v.txt("ISBILLWISEON")),
        "credit_days": parse_credit_period(v.txt("BILLCREDITPERIOD")).get("days"),
        "credit_limit_paise": None if limit is None else abs(limit),
        "gstin": v.txt("PARTYGSTIN", "GSTIN") or None, "state": v.txt("LEDSTATENAME", "STATENAME") or None,
        "currency": v.txt("CURRENCYNAME") or None,
        "opening_bills": [b for b in (map_bill(x, True) for x in v.kids("BILLALLOCATIONS.LIST")) if b.amount_paise != 0],
        "has_closing_values": v.has("LEDGERCLOSINGVALUES.LIST"),
        "closing_values": cvs,
    }


def map_voucher_type(n: El) -> dict:
    v = View(n)
    return {"name": name_of(n, v), "parent": parent_of(n, v)}


def map_cost_centre(n: El) -> dict:
    v = View(n)
    return {"name": name_of(n, v), "parent": parent_of(n, v), "category": clean_text(v.txt("CATEGORY")) or None,
            "guid": v.txt("GUID")}


def map_stock_group(n: El) -> dict:
    v = View(n)
    return {"name": name_of(n, v), "parent": parent_of(n, v), "guid": v.txt("GUID")}


def map_godown(n: El) -> dict:
    v = View(n)
    return {"name": name_of(n, v), "parent": parent_of(n, v)}


def map_unit(n: El) -> dict:
    v = View(n)
    simple = v.txt("ISSIMPLEUNIT")
    return {"name": name_of(n, v), "is_simple": True if simple is None else parse_bool(simple),
            "base_unit": v.txt("BASEUNITS") or None, "additional_unit": v.txt("ADDITIONALUNITS") or None,
            "conversion": v.txt("CONVERSION") or None, "decimals": num(v.txt("DECIMALPLACES"))}


def _stock_value(raw: str | None, qty_e4: int) -> int:
    x = abs(canonical_paise(raw))
    return -x if qty_e4 < 0 else x


def map_stock_item(n: El) -> dict:
    v = View(n)
    q = parse_qty(v.txt("OPENINGBALANCE"))
    oq = q[0] if q else 0
    cq_raw = v.txt("CLOSINGBALANCE")
    if cq_raw is None:
        cq = None
    else:
        cqq = parse_qty(cq_raw)
        cq = cqq[0] if cqq else 0
    cv_raw = v.txt("CLOSINGVALUE")
    return {
        "name": name_of(n, v), "parent": parent_of(n, v), "base_unit": clean_text(v.txt("BASEUNITS")) or None,
        "guid": v.txt("GUID"), "master_id": num(v.txt("MASTERID")), "alter_id": num(v.txt("ALTERID")),
        "opening_qty_e4": oq, "opening_value_paise": _stock_value(v.txt("OPENINGVALUE"), oq),
        "closing_qty_e4": cq, "closing_value_paise": None if cv_raw is None else _stock_value(cv_raw, cq or 0),
        "costing_method": v.txt("COSTINGMETHOD") or None, "hsn": v.txt("GSTHSNCODE", "HSNCODE") or None,
    }


def _cost_allocs(ev: View) -> list[dict]:
    out = []
    for cat in ev.kids("CATEGORYALLOCATIONS.LIST"):
        cv = View(cat)
        category = clean_text(cv.txt("CATEGORY")) or None
        for cc in cv.kids("COSTCENTREALLOCATIONS.LIST"):
            c = View(cc)
            out.append({"cost_centre": clean_text(c.txt("NAME")), "category": category,
                        "amount_paise": canonical_paise(c.txt("AMOUNT"))})
    return out


def _ledger_line(entry: El) -> VoucherLine | None:
    ev = View(entry)
    name = clean_text(ev.txt("LEDGERNAME"))
    if not name:
        return None
    bills = [b for b in (map_bill(x, False) for x in ev.kids("BILLALLOCATIONS.LIST")) if b.amount_paise != 0]
    return VoucherLine(name, canonical_paise(ev.txt("AMOUNT")), _cost_allocs(ev), bills)


def _inventory_lines(entry: El, forced: str | None = None) -> list[InvLine]:
    ev = View(entry)
    item = clean_text(ev.txt("STOCKITEMNAME"))
    if not item:
        return []
    actual = parse_qty(ev.txt("ACTUALQTY")) or parse_qty(ev.txt("BILLEDQTY"))
    billed = parse_qty(ev.txt("BILLEDQTY"))
    amount = canonical_paise(ev.txt("AMOUNT"))
    if forced:
        direction = forced
    elif ev.txt("ISDEEMEDPOSITIVE") is not None:
        direction = "in" if parse_bool(ev.txt("ISDEEMEDPOSITIVE")) else "out"
    else:
        direction = "in" if amount > 0 else "out"
    qty = actual[0] if actual else 0
    if qty < 0:
        qty = -qty
        direction = "out" if direction == "in" else "in"
    allocs = ev.kids("ACCOUNTINGALLOCATIONS.LIST")
    base = InvLine(item, direction, qty, abs(billed[0]) if billed else None, actual[1] if actual else None,
                   parse_rate(ev.txt("RATE")), abs(amount),
                   ledger_name=clean_text(View(allocs[0]).txt("LEDGERNAME")) if allocs else None)
    views = [View(b) for b in ev.kids("BATCHALLOCATIONS.LIST")]
    qty_batches = [b for b in views if parse_qty(b.txt("ACTUALQTY"))]
    if len(qty_batches) > 1:
        out = []
        for b in qty_batches:
            bq = parse_qty(b.txt("BILLEDQTY"))
            out.append(InvLine(
                item, direction, abs(parse_qty(b.txt("ACTUALQTY"))[0]), abs(bq[0]) if bq else None, base.unit,
                base.rate_paise, abs(canonical_paise(b.txt("AMOUNT"))),
                clean_text(b.txt("GODOWNNAME")) or None, clean_text(b.txt("BATCHNAME")) or None,
                parse_tally_date(b.txt("MFDON")), parse_tally_date(b.txt("EXPIRYPERIOD")), base.ledger_name))
        return out
    if views:
        b = views[0]
        base.godown = clean_text(b.txt("GODOWNNAME")) or None
        base.batch = clean_text(b.txt("BATCHNAME")) or None
        base.mfg_date = parse_tally_date(b.txt("MFDON"))
        base.expiry_date = parse_tally_date(b.txt("EXPIRYPERIOD"))
    return [base]


def map_voucher(n: El) -> Voucher | None:
    """Handles both TallyPrime (ALL*ENTRIES.LIST) and Tally.ERP 9 (LEDGERENTRIES.LIST) shapes without double counting."""
    warnings: list[str] = []
    v = View(n)
    date = parse_tally_date(v.txt("DATE"))
    vt = v.txt("VOUCHERTYPENAME")
    voucher_type = clean_text(vt if vt is not None else n.get("VCHTYPE"))
    if not date or not voucher_type:
        return None
    ledger_tag = "ALLLEDGERENTRIES.LIST" if v.kids("ALLLEDGERENTRIES.LIST") else "LEDGERENTRIES.LIST"
    inv_tag = "ALLINVENTORYENTRIES.LIST" if v.kids("ALLINVENTORYENTRIES.LIST") else "INVENTORYENTRIES.LIST"

    entry_lines = [l for l in (_ledger_line(e) for e in v.kids(ledger_tag)) if l]
    inventory: list[InvLine] = []
    alloc_lines: list[VoucherLine] = []
    for e in v.kids(inv_tag):
        inventory.extend(_inventory_lines(e))
        for a in View(e).kids("ACCOUNTINGALLOCATIONS.LIST"):
            l = _ledger_line(a)
            if l:
                alloc_lines.append(l)
    # TallyPrime collection exports repeat inventory accounting allocations inside ALLLEDGERENTRIES, Day Book-style
    # exports carry them only in ACCOUNTINGALLOCATIONS. Take whichever reading balances, so each is counted once.
    entries_only = sum(l.amount_paise for l in entry_lines)
    with_allocs = entries_only + sum(l.amount_paise for l in alloc_lines)
    lines = entry_lines
    if alloc_lines and entries_only != 0 and (with_allocs == 0 or abs(with_allocs) < abs(entries_only)):
        lines = entry_lines + alloc_lines
    if alloc_lines and entries_only != 0 and with_allocs != 0:
        warnings.append("Voucher does not balance with or without inventory accounting allocations; the closer reading was used")
    if lines is entry_lines and alloc_lines:
        # The ledger entry repeats the inventory allocation's amount but TallyPrime keeps the cost-centre split only on the
        # allocation inside the stock line: carry it over so cost-centre reports see sales/purchases.
        by_ledger: dict[str, list[dict]] = {}
        for a in alloc_lines:
            if a.cost_allocations:
                by_ledger.setdefault(a.ledger_name, []).extend(a.cost_allocations)
        for l in entry_lines:
            if not l.cost_allocations and l.ledger_name in by_ledger:
                l.cost_allocations = by_ledger.pop(l.ledger_name)
    for e in v.kids("INVENTORYENTRIESIN.LIST"):
        inventory.extend(_inventory_lines(e, "in"))
    for e in v.kids("INVENTORYENTRIESOUT.LIST"):
        inventory.extend(_inventory_lines(e, "out"))

    guid = clean_text(v.txt("GUID")) or None
    remote_id = n.get("REMOTEID")
    master_id = num(v.txt("MASTERID"))
    number = clean_text(v.txt("VOUCHERNUMBER")) or None
    party = clean_text(v.txt("PARTYLEDGERNAME", "PARTYNAME")) or None
    source_key = guid or remote_id or (f"MID:{master_id}" if master_id is not None else None)
    if not source_key:
        source_key = "SUR:" + hashlib.sha1(f"{voucher_type}|{number}|{date}|{party}".encode()).hexdigest()
        warnings.append("Voucher has no GUID/REMOTEID/MASTERID; a surrogate key was used (edits cannot be tracked reliably)")
    view = n.get("OBJVIEW") or v.txt("PERSISTEDVIEW") or ""
    return Voucher(
        source_key, guid, master_id, num(v.txt("ALTERID")), date, voucher_type, number,
        clean_text(v.txt("REFERENCE")) or None, party, clean_text(v.txt("NARRATION")) or None,
        parse_bool(v.txt("ISCANCELLED")), parse_bool(v.txt("ISOPTIONAL")), parse_bool(v.txt("ISPOSTDATED")),
        parse_bool(v.txt("ISINVOICE")) or bool(re.search("invoice", view, re.I)), lines, inventory, warnings)
