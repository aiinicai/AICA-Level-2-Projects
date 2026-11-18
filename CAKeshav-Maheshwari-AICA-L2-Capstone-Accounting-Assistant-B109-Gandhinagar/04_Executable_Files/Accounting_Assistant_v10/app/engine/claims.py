"""Employee reimbursements and petty cash in bulk.

Input: a folder of bills (photos / PDFs, read like vendor invoices) and, optionally, the expense sheet
(Excel/CSV: date, employee, description, amount). Sheet rows are matched to bills by amount and date; a sheet row
without a bill still becomes a line (no GST).

Output, for review before posting:
- reimbursement: one Journal per bill - expense Dr (+ input GST Dr only for a proper tax invoice in the company's
  name) / the common reimbursement ledger Cr, narration "<description> Paid by <employee>" (the office's style);
- petty cash: one Payment per bill, Cash Cr.
Expense ledgers are suggested from what this company did before (past journals with 'Paid by' narrations,
earlier approvals) and from words on the bill."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ClaimLine, Company
from ..tally.parsers import gstin_valid
from .masters import Masters
from .voucher import Q, Voucher, VLine

ZERO = Decimal(0)
STD_RATES = (Decimal(5), Decimal(12), Decimal(18), Decimal(28), Decimal(3), Decimal("0.25"))

# words on a bill -> words to look for in the company's ledger names
HINTS = [
    (r"swiggy|zomato|restaurant|cafe|café|food|lunch|dinner|meal|snack|tea|coffee|hotel\b.*food|biryani|pizza",
     ("staff welfare", "refreshment", "food", "meal")),
    (r"uber|ola|rapido|taxi|cab|auto|fuel|petrol|diesel|toll|parking|metro|bus|train|irctc|flight|air|indigo|"
     r"vistara|travel", ("travel", "conveyance", "vehicle", "fuel")),
    (r"hotel|stay|lodg|oyo|makemytrip|booking\.com", ("travel", "lodging", "hotel")),
    (r"courier|dtdc|blue ?dart|delhivery|speed post|postage|india post", ("courier", "postage")),
    (r"stationery|xerox|print|paper|pen\b|notebook", ("stationery", "printing")),
    (r"mobile|recharge|airtel|jio|vodafone|vi\b|internet|broadband|wifi", ("telephone", "internet", "mobile")),
    (r"amazon|flipkart|mouse|keyboard|headphone|charger|cable|laptop|monitor", ("computer", "it ", "office")),
    (r"gift|diwali|festival|sweet", ("gift", "festival", "staff welfare")),
    (r"movie|outing|party|team|event|celebrat", ("staff welfare", "team")),
    (r"medical|pharma|medicine|hospital|clinic", ("medical", "staff welfare")),
    (r"clean|housekeep|repair|maintenance|plumb|electric", ("repair", "maintenance", "housekeeping")),
]


def dec(s) -> Decimal:
    try:
        return Decimal(str(s or "0").replace(",", "").strip() or "0")
    except InvalidOperation:
        return ZERO


# ------------------------------------------------------------------ expense sheet
@dataclass
class SheetRow:
    date: str
    employee: str
    description: str
    amount: Decimal
    bill_ref: str = ""


_COLS = {"date": ("date", "bill date", "dt"),
         "employee": ("employee", "name", "paid by", "emp", "staff", "claimant"),
         "description": ("description", "particulars", "details", "purpose", "narration", "expense", "item"),
         "amount": ("amount", "amt", "total", "value", "rs", "inr"),
         "bill_ref": ("bill no", "invoice no", "bill", "receipt", "ref")}


def _ymd(v) -> str:
    if isinstance(v, date):
        return v.strftime("%Y%m%d")
    s = str(v or "").strip()
    for pat, order in ((r"^(\d{4})-(\d{1,2})-(\d{1,2})", "ymd"), (r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", "dmy")):
        m = re.match(pat, s)
        if m:
            a, b, c = m.groups()
            y, mo, d = (a, b, c) if order == "ymd" else (c, b, a)
            y = ("20" + y) if len(y) == 2 else y
            try:
                return date(int(y), int(mo), int(d)).strftime("%Y%m%d")
            except ValueError:
                return ""
    return ""


def read_sheet(path: Path) -> list[SheetRow]:
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        ws = load_workbook(path, read_only=True, data_only=True).active
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    else:
        import csv
        rows = list(csv.reader(path.read_text(encoding="utf-8-sig", errors="replace").splitlines()))
    hdr_i, cols = -1, {}
    for i, r in enumerate(rows[:15]):
        found = {}
        for j, cell in enumerate(r):
            t = str(cell or "").strip().lower()
            for key, names in _COLS.items():
                if key not in found and any(t == n or t.startswith(n) for n in names):
                    found[key] = j
        if "amount" in found and ("date" in found or "employee" in found or "description" in found):
            hdr_i, cols = i, found
            break
    if hdr_i < 0:
        raise ValueError("Could not find the header row (need at least Amount and one of Date / Employee / "
                         "Description)")
    out = []
    for r in rows[hdr_i + 1:]:
        g = lambda k: r[cols[k]] if k in cols and cols[k] < len(r) else ""
        amt = dec(g("amount"))
        if not amt:
            continue
        out.append(SheetRow(_ymd(g("date")), str(g("employee") or "").strip(), str(g("description") or "").strip(),
                            amt.quantize(Q), str(g("bill_ref") or "").strip()))
    return out


# ------------------------------------------------------------------ bills -> lines
def line_from_invoice(company: Company, inv, kind: str, batch: str, path: Path, file_hash: str) -> ClaimLine:
    tax = inv.cgst_total + inv.sgst_total + inv.igst_total
    total = inv.grand_total or (inv.taxable_total + tax)
    cl = ClaimLine(company_id=company.id, kind=kind, batch=batch, file_path=str(path), file_hash=file_hash,
                   date=inv.invoice_date or "", supplier=inv.supplier_name or "", supplier_gstin=inv.supplier_gstin or "",
                   buyer_gstin=inv.buyer_gstin or "", bill_no=inv.invoice_no or "",
                   description=", ".join(l.description for l in inv.lines[:3] if getattr(l, "description", ""))[:300],
                   amount=str(Decimal(total).quantize(Q)), taxable=str(Decimal(inv.taxable_total).quantize(Q)),
                   cgst=str(inv.cgst_total), sgst=str(inv.sgst_total), igst=str(inv.igst_total))
    gst_rules(company, cl)
    return cl


def gst_rules(company: Company, cl: ClaimLine) -> None:
    """Input GST only on a proper tax invoice in the company's own name; otherwise the whole bill is expense."""
    tax = dec(cl.cgst) + dec(cl.sgst) + dec(cl.igst)
    issues = []
    ok = bool(tax)
    if tax:
        if not gstin_valid(cl.supplier_gstin):
            ok = False
            issues.append("Supplier GSTIN missing/invalid - GST added to expense")
        if not company.gstin or (cl.buyer_gstin or "").upper() != company.gstin.upper():
            ok = False
            issues.append("Bill not in the company's GSTIN - GST added to expense")
    cl.gst_claim = ok
    cl.issues = issues


def match_sheet(lines: list[ClaimLine], sheet: list[SheetRow], company: Company, kind: str,
                batch: str) -> list[ClaimLine]:
    """Give each bill its sheet row (same amount, date within 7 days, or same bill no.); rows without a bill
    become lines of their own. Returns the new bill-less lines."""
    free = list(sheet)
    for cl in lines:
        amt = dec(cl.amount)
        best, score = None, None
        for r in free:
            s = None
            if r.bill_ref and cl.bill_no and r.bill_ref.lower() in cl.bill_no.lower():
                s = 0
            elif abs(r.amount - amt) < Decimal("1"):
                gap = abs((_d(r.date) - _d(cl.date)).days) if r.date and cl.date else 3
                s = gap if gap <= 7 else None
            if s is not None and (score is None or s < score):
                best, score = r, s
        if best:
            free.remove(best)
            cl.employee = cl.employee or best.employee
            cl.description = best.description or cl.description
            cl.date = cl.date or best.date
    extra = []
    for r in free:
        cl = ClaimLine(company_id=company.id, kind=kind, batch=batch, employee=r.employee, date=r.date,
                       description=r.description, bill_no=r.bill_ref, amount=str(r.amount), taxable=str(r.amount))
        cl.issues = ["No bill found for this sheet row"]
        extra.append(cl)
    return extra


def _d(s: str) -> date:
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


# ------------------------------------------------------------------ ledgers
def reimbursement_ledger(m: Masters, company: Company) -> str:
    cfg = (company.settings or {}).get("claims", {})
    if cfg.get("ledger") in m.ledgers:
        return cfg["ledger"]
    for n in sorted(m.ledgers):
        if "reimburs" in n.lower():
            return n
    return cfg.get("ledger") or "Employee Reimbursement"


def cash_ledger(m: Masters) -> str:
    cash = [n for n, d in m.ledgers.items() if d.get("_primary") == "Cash-in-Hand"]
    return cash[0] if cash else "Cash"


def learn_from_history(session: Session, company_id: str, credit_ledger: str) -> dict:
    """word -> expense ledger, from this company's past journals credited to the reimbursement ledger."""
    from . import history
    votes: dict = {}
    for v in history.vouchers(session, company_id):
        if not any(e["ledger"] == credit_ledger and not e["dr"] for e in v.entries or []):
            continue
        debits = [e["ledger"] for e in v.entries if e["dr"] and "gst" not in e["ledger"].lower()]
        if len(debits) != 1:
            continue
        for w in set(re.findall(r"[a-z]{4,}", (v.narration or "").lower())) - {"paid", "being", "expense", "with",
                                                                                "from", "team", "members"}:
            votes.setdefault(w, Counter())[debits[0]] += 1
    return {w: c.most_common(1)[0][0] for w, c in votes.items() if c.most_common(1)[0][1] >= 2}


def suggest_ledger(cl: ClaimLine, m: Masters, learned: dict, remembered: dict) -> tuple[str, str]:
    """(ledger, why)."""
    text = f"{cl.supplier} {cl.description}".lower()
    key = (cl.supplier or "").strip().lower()
    if key and remembered.get(key) in m.ledgers:
        return remembered[key], "used before for this supplier"
    hits = Counter(learned[w] for w in re.findall(r"[a-z]{4,}", text) if w in learned and learned[w] in m.ledgers)
    if hits:
        return hits.most_common(1)[0][0], "from earlier claims"
    expense = [n for n, d in m.ledgers.items() if d.get("_primary") in ("Indirect Expenses", "Direct Expenses")]
    for pat, words in HINTS:
        if re.search(pat, text):
            for w in words:
                for n in sorted(expense):
                    if w in n.lower():
                        return n, f"bill mentions '{re.search(pat, text).group(0)}'"
    return "", "pick a ledger"


# ------------------------------------------------------------------ duplicates
def duplicate_of(session: Session, cl: ClaimLine) -> str:
    q = select(ClaimLine).where(ClaimLine.company_id == cl.company_id, ClaimLine.id != (cl.id or ""),
                                ClaimLine.status != "skipped")
    for o in session.scalars(q):
        if cl.file_hash and o.file_hash == cl.file_hash:
            return f"same file already in {o.batch}"
        if cl.bill_no and o.bill_no and o.bill_no.lower() == cl.bill_no.lower() and \
                (o.supplier or "").lower() == (cl.supplier or "").lower():
            return f"bill {cl.bill_no} already in {o.batch}"
        if o.date == cl.date and o.amount == cl.amount and (o.employee or "") == (cl.employee or "") and o.date:
            return f"same date, amount and employee already in {o.batch}"
    return ""


# ------------------------------------------------------------------ vouchers
def build_voucher(cl: ClaimLine, m: Masters, company: Company) -> Voucher:
    amt = dec(cl.amount).quantize(Q)
    tax = dec(cl.cgst) + dec(cl.sgst) + dec(cl.igst)
    lines: list[VLine] = []
    exp_amt = (amt - tax) if cl.gst_claim else amt
    lines.append(VLine(cl.expense_ledger, exp_amt.quantize(Q), True, "expense", "", "green"))
    if cl.gst_claim:
        taxable = dec(cl.taxable) or (amt - tax)
        for head, val in (("cgst", dec(cl.cgst)), ("sgst", dec(cl.sgst)), ("igst", dec(cl.igst))):
            if not val:
                continue
            rate = _rate(val, taxable, head)
            led = m.gst_ledger(head, rate, output=False) or m.gst_ledger(head, None, output=False)
            lines.append(VLine(led, val.quantize(Q), True, "gst_in", f"Input {head.upper()}", "green" if led else "red"))
    credit = reimbursement_ledger(m, company) if cl.kind == "reimb" else cash_ledger(m)
    lines.append(VLine(credit, amt, False, "party", "", "green"))
    what = cl.description or cl.supplier or "Expense"
    bill = f" (Bill {cl.bill_no} dt {cl.date[6:8]}-{cl.date[4:6]}-{cl.date[:4]}{', ' + cl.supplier if cl.supplier else ''})" \
        if cl.bill_no and cl.date else ""
    narr = f"{what}{bill}" + (f"\tPaid by {cl.employee}" if cl.employee and cl.kind == "reimb" else "")
    vt = "Journal" if cl.kind == "reimb" else "Payment"
    return Voucher(vt, cl.date or date.today().strftime("%Y%m%d"), lines, reference=cl.bill_no or "",
                   reference_date=cl.date if cl.bill_no else "", narration=narr[:900], base_type=vt)


def _rate(val: Decimal, taxable: Decimal, head: str) -> Decimal | None:
    if not taxable:
        return None
    r = val / taxable * 100 * (2 if head in ("cgst", "sgst") else 1)
    best = min(STD_RATES, key=lambda s: abs(s - r))
    if abs(best - r) > Decimal("0.6"):
        return None
    return best / 2 if head in ("cgst", "sgst") else best


def remember(company: Company, cl: ClaimLine) -> None:
    if not cl.supplier or not cl.expense_ledger:
        return
    cfg = dict(company.settings or {})
    c = dict(cfg.get("claims", {}))
    mem = dict(c.get("suppliers", {}))
    mem[cl.supplier.strip().lower()] = cl.expense_ledger
    c["suppliers"] = mem
    cfg["claims"] = c
    company.settings = cfg


def summary(lines: list[ClaimLine]) -> dict:
    by_emp: dict = {}
    for cl in lines:
        if cl.status == "skipped":
            continue
        by_emp[cl.employee or "-"] = by_emp.get(cl.employee or "-", ZERO) + dec(cl.amount)
    return by_emp
