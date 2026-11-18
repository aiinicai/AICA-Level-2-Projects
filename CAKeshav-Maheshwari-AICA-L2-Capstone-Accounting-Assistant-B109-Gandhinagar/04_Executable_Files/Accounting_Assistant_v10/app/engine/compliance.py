"""v7 compliance views: TDS tracker, GST control panel, AP/AR ageing, global search and the month-end close
checklist. Figures come from Tally (synced vouchers, live bills) and the app's own records. Nothing here ever
blocks posting."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .history import vouchers as _hv
from ..db.models import BankLine, Company, Invoice, MappingRule, MasterCache, RecurringEntry, Vendor, VoucherHistory
from .masters import Masters
from .periods import Period, fy_start
from .tds import DEFAULT_SECTIONS

ZERO = Decimal(0)
Q = Decimal("0.01")


def _d(s: str) -> date:
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


# ====================================================================== E1 TDS tracker
_SEC_RE = re.compile(r"(?<!\d)(19[2-6][A-Z]{0,2}(?:-[A-Z])?|393)(?!\d)", re.I)


def tds_ledgers(m: Masters, company: Company) -> dict[str, str]:
    """TDS payable ledger -> section ('194C'...). From company settings, else the section printed in the name."""
    out = {}
    cfg = (company.settings or {}).get("tds_ledgers", {})
    for sec, led in cfg.items():
        if led:
            out[led] = sec
    for n, d in m.ledgers.items():
        if n in out or d.get("_primary") != "Duties & Taxes" or "tds" not in n.lower():
            continue
        mm = _SEC_RE.search(n.upper())
        out[n] = mm.group(0).upper() if mm else "TDS"
    return out


def due_date(month_key: str) -> str:
    """TDS deducted in a month is due on the 7th of the next month; March deductions by 30 April."""
    y, mth = int(month_key[:4]), int(month_key[4:6])
    if mth == 3:
        return f"{y}0430"
    ny, nm = (y + (mth == 12), mth % 12 + 1)
    return f"{ny}{nm:02d}07"


@dataclass
class TdsMonth:
    section: str
    month: str               # YYYYMM
    deducted: Decimal = ZERO
    paid: Decimal = ZERO
    due: str = ""

    @property
    def unpaid(self) -> Decimal:
        return max(self.deducted - self.paid, ZERO)


@dataclass
class TdsReport:
    months: list                               # [TdsMonth]
    deductions: list                           # 26Q rows
    near_threshold: list                       # [(party, section, credited, limit)]
    totals: dict = field(default_factory=dict)


def tds_tracker(session: Session, company: Company, m: Masters, period: Period,
                today: date | None = None) -> TdsReport:
    today = today or date.today()
    tl = tds_ledgers(m, company)
    months: dict[tuple, TdsMonth] = {}
    rows = []
    vendors = {v.party_ledger: v for v in session.scalars(select(Vendor).where(Vendor.company_id == company.id))
               if v.party_ledger}
    vchs = list(_hv(session, company.id, period.frm, period.to))
    for v in vchs:
        ents = v.entries or []
        tds_e = [e for e in ents if e["ledger"] in tl]
        if not tds_e:
            continue
        for e in tds_e:
            sec = tl[e["ledger"]]
            key = (sec, v.date[:6])
            mo = months.setdefault(key, TdsMonth(sec, v.date[:6], due=due_date(v.date[:6])))
            amt = Decimal(e["amount"])
            if e["dr"]:                                  # TDS ledger debited = deposited to the government
                mo.paid += amt
            else:
                mo.deducted += amt
                prim = lambda x: m.ledgers.get(x["ledger"], {}).get("_primary", "")
                creds = [x for x in ents if not x["dr"] and x["ledger"] not in tl]
                # deductee: a party ledger first (creditor, debtor, loan, capital), never a statutory dues ledger
                party = next((x for x in creds if prim(x) in ("Sundry Creditors", "Sundry Debtors", "Loans (Liability)",
                                                            "Unsecured Loans", "Secured Loans", "Capital Account")),
                             None) or next((x for x in creds if prim(x) not in ("Duties & Taxes", "Provisions",
                                                                                "Bank Accounts", "Cash-in-Hand")),
                                           None)
                base = sum((Decimal(x["amount"]) for x in ents if x["dr"] and
                            m.ledgers.get(x["ledger"], {}).get("_primary") not in ("Duties & Taxes",)), ZERO)
                pl = party["ledger"] if party else (v.party or "")
                if sec.startswith("192"):
                    pl = "Employees (salary - Form 24Q)"
                pan = (vendors[pl].pan if pl in vendors else "") or m.ledgers.get(pl, {}).get("INCOMETAXNUMBER", "")
                rate = (amt * 100 / base).quantize(Q) if base else ZERO
                rows.append({"date": v.date, "party": pl, "pan": pan, "section": sec, "amount": base.quantize(Q),
                             "tds": amt.quantize(Q), "rate": rate, "voucher": f"{v.voucher_type} {v.number}"})
    # payments are usually credited to the month they relate to only by challan; allocate surplus paid FIFO
    by_sec = defaultdict(list)
    for mo in sorted(months.values(), key=lambda x: x.month):
        by_sec[mo.section].append(mo)
    for sec, ms in by_sec.items():
        pool = sum((x.paid for x in ms), ZERO)
        for x in ms:
            x.paid = ZERO
        for x in ms:                                     # oldest deductions are settled first
            take = min(pool, x.deducted)
            x.paid, pool = take, pool - take
        if pool > 0 and ms:
            ms[-1].paid += pool
    near = tds_threshold_watch(session, company, m, today)
    out = sorted(months.values(), key=lambda x: (x.month, x.section))
    totals = {"deducted": sum((x.deducted for x in out), ZERO), "paid": sum((x.paid for x in out), ZERO),
              "overdue": sum((x.unpaid for x in out if x.due < today.strftime("%Y%m%d")), ZERO)}
    return TdsReport(out, rows, near, totals)


def party_sections(session: Session, company: Company, m: Masters, today: date | None = None) -> dict:
    """party ledger -> (code, source) where source is 'set' (user), 'vendor', 'guess' or ''.
    code may be tds_map.NA (not applicable)."""
    from . import tds_map
    today = today or date.today()
    lo = (fy_start(today).replace(year=fy_start(today).year - 1)).strftime("%Y%m%d")
    overrides = (company.settings or {}).get("tds_party", {})
    vendors = {v.party_ledger: v for v in session.scalars(select(Vendor).where(Vendor.company_id == company.id))
               if v.party_ledger}
    heads: dict[str, set] = defaultdict(set)
    goods: dict[str, int] = defaultdict(int)
    for v in _hv(session, company.id, lo):
        ents = v.entries or []
        parties = [e["ledger"] for e in ents if not e["dr"] and
                   m.ledgers.get(e["ledger"], {}).get("_primary") == "Sundry Creditors"]
        if not parties:
            continue
        dr = [e["ledger"] for e in ents if e["dr"] and m.ledgers.get(e["ledger"], {}).get("_primary") not in
              ("Duties & Taxes", "Sundry Creditors", "Bank Accounts", "Cash-in-Hand")]
        for p in parties:
            heads[p].update(dr)
            if any(m.ledgers.get(x, {}).get("_primary") == "Purchase Accounts" for x in dr):
                goods[p] += 1
    out = {}
    for p in set(heads) | set(overrides) | set(vendors):
        if p in overrides:
            out[p] = (tds_map.normalise(overrides[p]), "set")
        elif p in vendors and vendors[p].tds_section:
            out[p] = (tds_map.normalise(vendors[p].tds_section), "vendor")
        else:
            g = tds_map.guess(sorted(heads.get(p, [])), is_goods_purchase=goods.get(p, 0) > 0)
            out[p] = (g, "guess" if g else "")
    return out


def set_party_section(session: Session, company: Company, party: str, code: str) -> None:
    """Remembered for the company and used everywhere (tracker, threshold watch, invoice suggestions)."""
    from . import tds_map
    cfg = dict(company.settings or {})
    tp = dict(cfg.get("tds_party", {}))
    tp[party] = tds_map.normalise(code)
    cfg["tds_party"] = tp
    company.settings = cfg
    for v in session.scalars(select(Vendor).where(Vendor.company_id == company.id, Vendor.party_ledger == party)):
        v.tds_section = "" if tp[party] == tds_map.NA else tp[party]
    session.commit()


def tds_threshold_watch(session: Session, company: Company, m: Masters, today: date) -> list:
    """Parties credited this FY without any TDS, at 80% or more of their section's yearly limit.
    Section: set by the user, else the vendor setting, else guessed from the expense ledgers.
    Parties marked Not applicable are left out; unknown ones are listed with section '' so it can be set."""
    from . import tds_map
    lo = fy_start(today).strftime("%Y%m%d")
    tl = tds_ledgers(m, company)
    credited: dict[str, Decimal] = defaultdict(lambda: ZERO)
    goods: dict[str, Decimal] = defaultdict(lambda: ZERO)     # credits for purchase of goods (Purchase Accounts)
    deducted: set = set()
    for v in _hv(session, company.id, lo):
        ents = v.entries or []
        has_tds = any(e["ledger"] in tl for e in ents)
        if "payment" in v.voucher_type.lower() or "receipt" in v.voucher_type.lower():
            continue
        is_goods = any(e["dr"] and m.ledgers.get(e["ledger"], {}).get("_primary") == "Purchase Accounts"
                       for e in ents)
        for e in ents:
            if not e["dr"] and m.ledgers.get(e["ledger"], {}).get("_primary") == "Sundry Creditors":
                credited[e["ledger"]] += Decimal(e["amount"])
                if is_goods:
                    goods[e["ledger"]] += Decimal(e["amount"])
                if has_tds:
                    deducted.add(e["ledger"])
    secs = party_sections(session, company, m, today)
    out = []
    for party, amt in credited.items():
        if party in deducted:
            continue
        sec, src = secs.get(party, ("", ""))
        if sec == tds_map.NA:
            continue
        if src in ("", "guess") and goods[party] >= amt * Decimal("0.8"):
            # mainly goods bought: no 194C/194J; only 194Q (buyer turnover > Rs 10 crore, above Rs 50 lakh)
            sec, src = "194Q", "guess"
        cfg = DEFAULT_SECTIONS.get(sec) or DEFAULT_SECTIONS.get({"194I": "194I-B", "194J": "194J-P"}.get(sec, ""),
                                                              DEFAULT_SECTIONS["194C"])
        limit = Decimal(str(cfg.get("annual_limit") or (cfg.get("single_limit", 0) * (12 if cfg.get("monthly")
                                                                                     else 1)) or 0))
        if sec == "194Q":
            limit = Decimal("5000000")
        if limit and amt >= limit * Decimal("0.8"):
            out.append((party, sec, amt.quantize(Q), limit, src))
    return sorted(out, key=lambda x: -x[2])


def export_26q(rep: TdsReport, path, company: str, period_text: str) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "26Q deductee details"
    ws.append([f"{company} - TDS deductions {period_text} (prepare 26Q from this; verify PAN and section codes)"])
    hdr = ["Sr", "Deductee name", "PAN", "Section", "Date of payment / credit", "Amount paid / credited",
           "TDS rate %", "TDS deducted", "Date of deduction", "Voucher"]
    ws.append(hdr)
    for c in ws[2]:
        c.font = Font(bold=True)
    for i, r in enumerate(rep.deductions, 1):
        d = f"{r['date'][6:8]}-{r['date'][4:6]}-{r['date'][:4]}"
        from . import tds_map
        ws.append([i, r["party"], r["pan"] or "PAN NOT AVAILABLE", tds_map.label(r["section"], r["date"]), d,
                   float(r["amount"]),
                   float(r["rate"]), float(r["tds"]), d, r["voucher"]])
    ws2 = wb.create_sheet("Challan status")
    ws2.append(["Section", "Month", "Deducted", "Deposited", "Unpaid", "Due date"])
    for c in ws2[1]:
        c.font = Font(bold=True)
    from . import tds_map
    for mo in rep.months:
        ws2.append([tds_map.label(mo.section, mo.month + "01"), f"{mo.month[4:6]}-{mo.month[:4]}", float(mo.deducted), float(mo.paid),
                    float(mo.unpaid), f"{mo.due[6:8]}-{mo.due[4:6]}-{mo.due[:4]}"])
    for w, col in ((6, "A"), (34, "B"), (14, "C"), (10, "D"), (14, "E"), (16, "F"), (10, "G"), (14, "H"),
                   (14, "I"), (18, "J")):
        ws.column_dimensions[col].width = w
    wb.save(path)


# ====================================================================== E2 GST control panel
@dataclass
class GstPanel:
    reversal_180: list            # [(party, bill, bill date, days, pending, gst_if_known)]
    rcm: list                     # [(date, voucher, ledger, amount)]
    blocked: list                 # [(date, supplier, invoice no, gst)]
    b2b: dict                     # status -> count
    b2b_rows: list                # [(status, supplier, invoice no, total)]
    totals: dict = field(default_factory=dict)


def _gst_of(ex: dict) -> Decimal:
    return sum((Decimal(str(ex.get(k) or 0)) for k in ("igst_total", "cgst_total", "sgst_total", "cess_total")),
               ZERO)


def unpaid_bills(session: Session, company: Company, m: Masters, bills: list | None,
                 closings: dict | None) -> list:
    """Supplier bills that are really unpaid. Payments are often entered On Account or without Agst Ref, so
    Tally's pending bills overstate dues. For each supplier the actual ledger balance (Cr) is matched to its
    newest bills first (payments settle the oldest bills - FIFO); older bills count as paid.
    bills: Tally pending bills (live) or None; closings: {ledger: {"closing": Tally sign}} or None.
    Returns [(party, bill, date, amount_unpaid, working)]."""
    by_party: dict[str, list] = defaultdict(list)
    for b in bills or []:
        if Decimal(b["amount"]) > 0 and m.ledgers.get(b["party"], {}).get("_primary") in ("Sundry Creditors", None):
            by_party[b["party"]].append((b["name"], (b.get("date") or "")[:8], Decimal(b["amount"])))
    # suppliers that aren't bill-wise: their purchase / expense credits act as the bills
    credits: dict[str, list] = defaultdict(list)
    net: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for v in _hv(session, company.id):
        for e in v.entries or []:
            if m.ledgers.get(e["ledger"], {}).get("_primary") != "Sundry Creditors":
                continue
            amt = Decimal(e["amount"])
            net[e["ledger"]] += -amt if e["dr"] else amt
            if not e["dr"] and not re.search(r"payment|contra|receipt", v.voucher_type, re.I):
                credits[e["ledger"]].append((v.reference or f"{v.voucher_type} {v.number}", v.date, amt))
    out = []
    for party in set(by_party) | set(credits):
        if closings is not None and party in closings:
            bal = closings[party]["closing"]                # Tally sign: Cr (+) = we owe
            src = "ledger balance in Tally"
        else:
            bal = net.get(party, ZERO)
            src = "balance from synced entries (opening balances not included)"
        if bal <= 0:
            continue                                         # nothing owed: every bill is paid
        pool = by_party.get(party) or credits.get(party, [])
        left = bal
        for name, d, amt in sorted(pool, key=lambda x: x[1], reverse=True):     # newest first
            if left <= 0:
                break
            take = min(amt, left)
            left -= take
            out.append((party, name, d, take.quantize(Q),
                        f"Balance {bal:,.2f} ({src}) covers the newest bills first; {take:,.2f} of this bill "
                        f"is unpaid" + ("" if take == amt else f" (bill {amt:,.2f}, rest treated as paid)")))
    return out


def gst_panel(session: Session, company: Company, m: Masters, period: Period, bills: list | None,
              today: date | None = None, closings: dict | None = None) -> GstPanel:
    """bills: Tally's pending bills (live) or None when Tally can't be reached; closings: live ledger balances."""
    today = today or date.today()
    invs = list(session.scalars(select(Invoice).where(Invoice.company_id == company.id)))
    by_party_no = {}
    for r in invs:
        ex = r.extraction or {}
        if ex.get("invoice_no"):
            by_party_no[str(ex["invoice_no"]).strip().lower()] = ex
    # Rule 37: ITC on bills unpaid 180 days from the invoice date has to be reversed
    rev = []
    for party, name, bd, amt, why in unpaid_bills(session, company, m, bills, closings):
        if len(bd) != 8:
            continue
        days = (today - _d(bd)).days
        if days > 180:
            ex = by_party_no.get(str(name).strip().lower())
            gst = None
            if ex:
                total = Decimal(str(ex.get("grand_total") or 0))
                gst = (_gst_of(ex) * amt / total).quantize(Q) if total else _gst_of(ex)
            rev.append((party, name, bd, days, amt, gst, why))
    rev.sort(key=lambda x: -x[3])
    # RCM liability in the period
    rcm = []
    for v in _hv(session, company.id, period.frm, period.to):
        for e in v.entries or []:
            low = e["ledger"].lower()
            if re.search(r"rcm|reverse", low) and re.search(r"output|payable|liab", low) and not e["dr"]:
                rcm.append((v.date, f"{v.voucher_type} {v.number}", e["ledger"], Decimal(e["amount"])))
    # 17(5): invoices posted for suppliers / items marked blocked
    blocked_keys = {r.vendor_key for r in session.scalars(select(MappingRule).where(
        MappingRule.company_id == company.id, MappingRule.blocked_17_5.is_(True), MappingRule.active.is_(True)))}
    blocked = []
    b2b = defaultdict(int)
    b2b_rows = []
    for r in invs:
        ex = r.extraction or {}
        d = ex.get("invoice_date", "")
        if d and not period.contains(d):
            continue
        key = ex.get("supplier_gstin") or ""
        if r.status == "posted" and key and key in blocked_keys:
            blocked.append((d, ex.get("supplier_name", ""), ex.get("invoice_no", ""), _gst_of(ex)))
        b2b[r.status_2b or "unchecked"] += 1
        if (r.status_2b or "unchecked") not in ("matched", "unchecked"):
            b2b_rows.append((r.status_2b, ex.get("supplier_name") or key, ex.get("invoice_no", ""),
                             Decimal(str(ex.get("grand_total") or 0))))
    return GstPanel(rev, rcm, blocked, dict(b2b), b2b_rows,
                    {"reversal_pending": sum((x[4] for x in rev), ZERO),
                     "reversal_gst": sum((x[5] for x in rev if x[5] is not None), ZERO),
                     "rcm": sum((x[3] for x in rcm), ZERO), "blocked": sum((x[3] for x in blocked), ZERO)})


# ====================================================================== E3 ageing
BUCKETS = [("0-30", 0, 30), ("31-60", 31, 60), ("61-90", 61, 90), ("91-180", 91, 180), ("180+", 181, 10 ** 6)]


@dataclass
class AgeRow:
    party: str
    total: Decimal
    buckets: list            # amounts per BUCKETS
    bills: list              # [(bill, date, days, amount)]


def ageing(bills: list, m: Masters, receivable: bool, today: date | None = None) -> list[AgeRow]:
    """Age bills from the bill date. receivable=True -> debtors (Dr bills), False -> creditors (Cr bills)."""
    today = today or date.today()
    rows: dict[str, AgeRow] = {}
    for b in bills:
        amt = Decimal(b["amount"])
        if receivable != (amt < 0):
            continue
        prim = m.ledgers.get(b["party"], {}).get("_primary", "")
        if prim and prim not in (("Sundry Debtors",) if receivable else ("Sundry Creditors",)):
            continue
        bd = (b.get("date") or "")[:8]
        days = (today - _d(bd)).days if len(bd) == 8 else 0
        r = rows.setdefault(b["party"], AgeRow(b["party"], ZERO, [ZERO] * len(BUCKETS), []))
        a = abs(amt)
        r.total += a
        for i, (_l, lo, hi) in enumerate(BUCKETS):
            if lo <= days <= hi:
                r.buckets[i] += a
                break
        r.bills.append((b["name"], bd, days, a))
    for r in rows.values():
        r.bills.sort(key=lambda x: -x[2])
    return sorted(rows.values(), key=lambda r: -r.total)


def reminder_text(company: str, row: AgeRow, receivable: bool = True) -> tuple[str, str]:
    """A polite payment reminder (customer) or a payment-schedule note (supplier). Drafted only - never sent."""
    lines = "\n".join(f"  • Bill {n} dated {d[6:8]}-{d[4:6]}-{d[:4]} - Rs. {a:,.2f} ({days} days)"
                      for n, d, days, a in row.bills[:20])
    if receivable:
        subj = f"Payment reminder - outstanding of Rs. {row.total:,.2f}"
        body = (f"Dear Sir / Madam,\n\nAs per our books, the following bills are outstanding from {row.party}:\n\n"
                f"{lines}\n\nTotal outstanding: Rs. {row.total:,.2f}\n\nWe request you to kindly arrange the "
                f"payment at the earliest. If it has already been made, please share the payment details so that "
                f"we can update our records.\n\nRegards,\n{company}")
    else:
        subj = f"Payment schedule - {row.party}"
        body = (f"Bills of {row.party} pending in our books:\n\n{lines}\n\nTotal: Rs. {row.total:,.2f}\n\n"
                f"{company}")
    return subj, body


# ====================================================================== E4 global search
@dataclass
class Hit:
    company_id: str
    company: str
    kind: str                # Voucher | Invoice | Bank line | Ledger
    date: str
    text: str
    amount: Decimal | None
    ref: object              # row id / object to open


def search(session: Session, q: str, limit: int = 300) -> list[Hit]:
    q = q.strip()
    if len(q) < 2:
        return []
    names = {c.id: c.name for c in session.scalars(select(Company))}
    amt = None
    try:
        amt = Decimal(q.replace(",", "").replace("₹", "").strip())
    except Exception:
        pass
    low = q.lower()
    out: list[Hit] = []

    def amount_hit(a) -> bool:
        return amt is not None and a is not None and abs(Decimal(str(a)) - amt) < 1

    for v in session.scalars(select(VoucherHistory)):
        text = f"{v.voucher_type} {v.number} {v.party} {v.reference} {v.narration}"
        ents = v.entries or []
        total = sum((Decimal(e["amount"]) for e in ents if e["dr"]), ZERO)
        if low in text.lower() or any(low in e["ledger"].lower() for e in ents) or \
                amount_hit(total) or any(amount_hit(e["amount"]) for e in ents):
            out.append(Hit(v.company_id, names.get(v.company_id, ""), "Voucher", v.date,
                           f"{v.voucher_type} {v.number} · {v.party or (ents[0]['ledger'] if ents else '')} · "
                           f"{(v.narration or '')[:80]}", total, v))
        if len(out) >= limit:
            break
    for r in session.scalars(select(Invoice)):
        ex = r.extraction or {}
        text = f"{ex.get('supplier_name', '')} {ex.get('supplier_gstin', '')} {ex.get('invoice_no', '')} {r.file_path}"
        if low in text.lower() or amount_hit(ex.get("grand_total")):
            out.append(Hit(r.company_id, names.get(r.company_id, ""), "Invoice", ex.get("invoice_date", ""),
                           f"{ex.get('supplier_name', '')} · Inv {ex.get('invoice_no', '')} · {r.status}",
                           Decimal(str(ex.get("grand_total") or 0)), r))
    for b in session.scalars(select(BankLine)):
        if low in (b.narration or "").lower() or low in (b.reference or "").lower() or \
                amount_hit(b.withdrawal or b.deposit):
            out.append(Hit(b.company_id, names.get(b.company_id, ""), "Bank line", b.date,
                           f"{b.bank_ledger} · {(b.narration or '')[:80]} · {b.status}",
                           Decimal(str(b.withdrawal or b.deposit)), b))
    for mc in session.scalars(select(MasterCache).where(MasterCache.kind == "ledger")):
        g = (mc.data or {}).get("_gstin", "")
        if low in mc.name.lower() or (g and low in g.lower()):
            out.append(Hit(mc.company_id, names.get(mc.company_id, ""), "Ledger", "",
                           f"{mc.name} · {mc.parent}" + (f" · {g}" if g else ""), None, mc))
    order = {"Ledger": 0, "Invoice": 1, "Voucher": 2, "Bank line": 3}
    return sorted(out, key=lambda h: (order[h.kind], h.date or "0"), reverse=False)[:limit]


# ====================================================================== E5 month-end close
CLOSE_ITEMS = [
    ("bank", "Bank statements imported and reconciled"),
    ("invoices", "Purchase / expense invoices posted"),
    ("recurring", "Recurring entries (rent, salary, EMI…) posted"),
    ("gstr2b", "GSTR-2B reconciled"),
    ("tds", "TDS of the month deposited (due 7th)"),
    ("gst_returns", "GSTR-1 / GSTR-3B filed"),
    ("depreciation", "Depreciation / provisions / accruals posted"),
    ("lock", "Books locked for the month"),
]


@dataclass
class CloseItem:
    key: str
    label: str
    auto: str                # ok | pending | n/a (what the app can see)
    detail: str
    done: bool = False
    by: str = ""
    at: str = ""
    note: str = ""


def close_status(session: Session, company: Company, m: Masters, month: str,
                 today: date | None = None) -> list[CloseItem]:
    """month: YYYYMM. Automatic checks where the app can see the facts; ticks by the user are stored per month."""
    today = today or date.today()
    y, mo = int(month[:4]), int(month[4:6])
    start = date(y, mo, 1)
    end = date(y + (mo == 12), mo % 12 + 1, 1) - timedelta(days=1)
    per = Period(start, end)
    saved = (company.settings or {}).get("close", {}).get(month, {})
    out = []

    def item(key, auto, detail):
        lab = dict(CLOSE_ITEMS)[key]
        s = saved.get(key, {})
        out.append(CloseItem(key, lab, auto, detail, bool(s.get("done")), s.get("by", ""), s.get("at", ""),
                             s.get("note", "")))
    pend_bank = [l for l in session.scalars(select(BankLine).where(BankLine.company_id == company.id,
                                                                   BankLine.date >= per.frm,
                                                                   BankLine.date <= per.to))]
    n_new = sum(1 for l in pend_bank if l.status == "new")
    item("bank", "ok" if pend_bank and not n_new else "pending" if pend_bank else "n/a",
         f"{n_new} line(s) still to post" if n_new else (f"{len(pend_bank)} line(s), all done" if pend_bank
                                                          else "No statement imported for this month"))
    invs = [r for r in session.scalars(select(Invoice).where(Invoice.company_id == company.id))
            if per.contains((r.extraction or {}).get("invoice_date", ""))]
    n_open = sum(1 for r in invs if r.status not in ("posted", "exception"))
    item("invoices", "pending" if n_open else ("ok" if invs else "n/a"),
         f"{n_open} invoice(s) waiting" if n_open else f"{len(invs)} invoice(s) dated this month")
    recs = [r for r in session.scalars(select(RecurringEntry).where(RecurringEntry.company_id == company.id,
                                                                   RecurringEntry.active.is_(True)))]
    due = [r for r in recs if r.next_due and r.next_due <= per.to]
    item("recurring", "pending" if due else ("ok" if recs else "n/a"),
         ", ".join(r.name for r in due) + " still due" if due else f"{len(recs)} schedule(s) up to date")
    unchecked = sum(1 for r in invs if (r.status_2b or "unchecked") == "unchecked")
    mism = sum(1 for r in invs if (r.status_2b or "") in ("amount_mismatch", "not_in_2b"))
    item("gstr2b", "pending" if invs and (unchecked or mism) else ("ok" if invs else "n/a"),
         f"{unchecked} not checked, {mism} mismatch(es)" if invs else "No invoices this month")
    try:
        rep = tds_tracker(session, company, m, per, today)
        unpaid = sum((x.unpaid for x in rep.months), ZERO)
        item("tds", "pending" if unpaid else ("ok" if rep.months else "n/a"),
             f"Unpaid {unpaid:,.2f} (due {due_date(month)[6:8]}-{due_date(month)[4:6]})" if unpaid else
             ("Deducted and deposited" if rep.months else "No TDS deducted this month (as per synced entries)"))
    except Exception as e:
        item("tds", "n/a", str(e)[:80])
    item("gst_returns", "n/a", "Tick when filed")
    item("depreciation", "n/a", "Tick when posted")
    lu = (company.settings or {}).get("lock_until", "")
    item("lock", "ok" if lu and lu >= per.to else "pending",
         f"Locked up to {lu[6:8]}-{lu[4:6]}-{lu[:4]}" if lu else "Not locked (Company settings)")
    return out


def set_close(session: Session, company: Company, month: str, key: str, done: bool, actor: str,
              note: str = "") -> None:
    cfg = dict(company.settings or {})
    close = dict(cfg.get("close", {}))
    mo = dict(close.get(month, {}))
    mo[key] = {"done": done, "by": actor if done else "", "at": datetime.now().strftime("%d-%m-%Y %H:%M") if done
               else "", "note": note}
    close[month] = mo
    cfg["close"] = close
    company.settings = cfg
    session.commit()
