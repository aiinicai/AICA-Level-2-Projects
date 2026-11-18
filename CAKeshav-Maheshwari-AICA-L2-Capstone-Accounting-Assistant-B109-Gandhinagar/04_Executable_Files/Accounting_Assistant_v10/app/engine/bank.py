"""Bank statement import: parse any Excel/CSV/PDF statement, suggest the counter ledger, skip what Tally
already has, build Payment / Receipt / Contra vouchers, learn from approvals."""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .history import vouchers as _hv
from ..db.models import BankLine, BankRule, Company, VoucherHistory
from ..extract.parser import parse_date
from .masters import Masters
from .voucher import VLine, Voucher

Q = Decimal("0.01")

# ------------------------------------------------------------------ parsing
HEADER_KEYS = {
    "date": ["transaction date", "txn date", "txn dt", "tran date", "tran dt", "trans date", "trans dt",
             "date of transaction", "posting date", "post date", "book date", "date", "value date", "value dt"],
    "narration": ["narration", "description", "particulars", "transaction details", "transaction remarks",
                  "remarks", "details"],
    "ref": ["chq./ref.no.", "chq/ref no", "cheque no", "chq no", "ref no", "reference", "utr", "chq"],
    "withdrawal": ["withdrawal amt", "withdrawal amount", "withdrawals", "withdrawal", "debit amount", "debits",
                   "debit", "dr amount", "money out", "paid out", "dr"],
    "deposit": ["deposit amt", "deposit amount", "deposits", "deposit", "credit amount", "credits", "credit",
                "cr amount", "money in", "paid in", "cr"],
    "amount": ["transaction amount", "amount"],
    "drcr": ["dr/cr", "cr/dr", "debit/credit", "credit/debit", "dr/cr indicator", "txn type", "type"],
    "balance": ["closing balance", "available balance", "running balance", "balance", "bal"],
}


@dataclass
class Txn:
    date: str                     # YYYYMMDD
    narration: str
    ref: str
    withdrawal: Decimal
    deposit: Decimal
    balance: Decimal | None = None

    @property
    def amount(self) -> Decimal:
        return self.withdrawal or self.deposit

    @property
    def direction(self) -> str:
        return "out" if self.withdrawal else "in"

    def key(self) -> str:
        raw = f"{self.date}|{self.narration.strip()}|{self.withdrawal}|{self.deposit}|{self.balance}"
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class Statement:
    txns: list[Txn]
    mapping: dict = field(default_factory=dict)
    header: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    signature: str = ""


def _dec(v) -> Decimal:
    if v is None:
        return Decimal(0)
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v)).quantize(Q)
    t = str(v).replace(",", "").replace("₹", "").replace("INR", "").strip()
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()").strip()
    t = re.sub(r"\s*(Cr|Dr|CR|DR)\.?$", "", t)
    try:
        d = Decimal(t).quantize(Q) if t not in ("", "-") else Decimal(0)
    except InvalidOperation:
        return Decimal(0)
    return -d if neg else d


def _to_date(v) -> str:
    if hasattr(v, "strftime"):
        return v.strftime("%Y%m%d")
    return parse_date(str(v or "").strip())


def _rows(path: Path) -> list[list]:
    ext = path.suffix.lower()
    if ext == ".csv":
        import csv
        for enc in ("utf-8-sig", "cp1252"):
            try:
                with open(path, newline="", encoding=enc) as f:
                    return [r for r in csv.reader(f)]
            except UnicodeDecodeError:
                continue
    if ext == ".xls":
        try:
            import xlrd                                  # pure Python reader for old-format Excel
            book = xlrd.open_workbook(str(path))
            rows = []
            for sh in book.sheets():
                for i in range(sh.nrows):
                    row = []
                    for j in range(sh.ncols):
                        c = sh.cell(i, j)
                        if c.ctype == xlrd.XL_CELL_DATE:
                            row.append(xlrd.xldate.xldate_as_datetime(c.value, book.datemode))
                        else:
                            row.append(c.value)
                    rows.append(row)
            return rows
        except ImportError:
            raise ValueError("Reading .xls needs the 'xlrd' package: python -m pip install xlrd")
        except Exception:
            pass                                         # some banks send .xlsx or HTML named .xls
        try:
            from openpyxl import load_workbook
            wb = load_workbook(path, data_only=True, read_only=True)
            return [list(r) for ws in wb.worksheets for r in ws.iter_rows(values_only=True)]
        except Exception:
            text = path.read_bytes().decode("utf-8", errors="replace")
            if "<table" in text.lower():
                return _html_rows(text)
            raise ValueError("This .xls file couldn't be read. Open it in Excel and save as .xlsx or .csv")
    if ext in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        wb = load_workbook(path, data_only=True, read_only=True)
        rows = []
        for ws in wb.worksheets:
            rows += [list(r) for r in ws.iter_rows(values_only=True)]
        return rows
    raise ValueError(f"Unsupported statement type {ext}")


def _html_rows(text: str) -> list[list]:
    import html
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)
        rows.append([html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in cells])
    return rows


def detect_mapping(header: list[str]) -> dict:
    h = [re.sub(r"\s*/\s*", "/", re.sub(r"\s+", " ", str(c or "").strip().lower())) for c in header]
    m: dict[str, int] = {}
    # a Dr/Cr marker column ("Debit/Credit") contains the words debit and credit: claim it first so it is not
    # taken as the Withdrawal or Deposit column
    for name in HEADER_KEYS["drcr"]:
        hit = next((i for i, c in enumerate(h) if c == name or ("/" in name and name in c)), None)
        if hit is not None:
            m["drcr"] = hit
            break
    vd = next((i for i, c in enumerate(h) if c in ("value date", "value dt", "valuedate")), None)
    for key, names in HEADER_KEYS.items():
        if key == "drcr":
            continue
        for name in names:                         # earlier names win (txn date before value date)
            hit = next((i for i, c in enumerate(h) if c == name or (len(name) > 3 and name in c)), None)
            if hit is not None and hit not in m.values():
                m[key] = hit
                break
    if vd is not None and m.get("date") != vd:
        m["value_date"] = vd
    return m


def header_signature(header: list) -> str:
    """Fingerprint of a statement's header row: same bank layout -> same signature."""
    cells = [re.sub(r"[^a-z]", "", str(c or "").lower()) for c in header]
    cells = [c for c in cells if c]
    return hashlib.sha1("|".join(cells).encode()).hexdigest() if len(cells) >= 3 else ""


def preview(path: Path, limit: int = 80) -> tuple[list[list], int]:
    """Raw rows for the column-mapping screen, and the most likely header row index."""
    rows = [[("" if c is None else c) for c in r] for r in _rows(Path(path))[:limit]]
    best_i, best_n = 0, -1
    for i, r in enumerate(rows[:40]):
        mp = detect_mapping([str(c) for c in r])
        n = len(mp) * 10 + sum(1 for x in r if isinstance(x, str) and x.strip())
        if n > best_n:
            best_i, best_n = i, n
    return rows, best_i


def parse(path: Path, mapping: dict | None = None, saved: dict | None = None,
          header_index: int | None = None) -> Statement:
    """saved: {signature: mapping} remembered per bank layout (from the column-mapping screen)."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return parse_pdf(path)
    rows = _rows(path)
    hdr_i, best = None, {}
    if mapping is None and saved:
        for i, r in enumerate(rows[:60]):
            sig = header_signature(r)
            if sig and sig in saved:
                hdr_i, mapping = i, {k: int(v) for k, v in saved[sig].items() if v is not None}
                break
    if mapping is not None and header_index is not None:
        hdr_i = header_index
    for i, r in enumerate(rows[:60] if mapping is None else []):
        mp = detect_mapping([str(c or "") for c in r])
        if "date" in mp and "narration" in mp and (("withdrawal" in mp and "deposit" in mp) or "amount" in mp):
            hdr_i, best = i, mp
            break
    if mapping:
        best = mapping
        hdr_i = hdr_i if hdr_i is not None else 0
        if not ("date" in best and "narration" in best and
                (("withdrawal" in best and "deposit" in best) or "amount" in best)):
            raise ValueError("Map at least Date, Narration and either Withdrawal + Deposit or Amount")
    if hdr_i is None:
        raise ValueError("Couldn't find the header row (Date / Narration / Withdrawal / Deposit). "
                         "Use 'Map columns' to pick them.")
    header = [str(c or "").strip() for c in rows[hdr_i]]
    out, warn = [], []
    pending: Txn | None = None
    for r in rows[hdr_i + 1:]:
        g = lambda k: r[best[k]] if k in best and best[k] < len(r) else None
        d = _to_date(g("date"))
        if not d and "value_date" in best:
            d = _to_date(r[best["value_date"]] if best["value_date"] < len(r) else None)
        if not d:
            # continuation line of a wrapped narration: date and amount cells empty, narration present
            amounts_empty = all(g(k) in (None, "", 0, "0.00") for k in ("withdrawal", "deposit", "amount"))
            nar = str(g("narration") or "").strip()
            if pending and nar and g("date") in (None, "") and amounts_empty and not set(nar) <= {"*", "-", "="}:
                pending.narration += " " + nar
            continue
        if "withdrawal" in best and "deposit" in best:
            wd, dp = abs(_dec(g("withdrawal"))), abs(_dec(g("deposit")))
        else:
            amt = _dec(g("amount"))
            t = str(g("drcr") or "").strip().upper()
            if t.startswith("D") or (not t and amt < 0):
                wd, dp = abs(amt), Decimal(0)
            else:
                wd, dp = Decimal(0), abs(amt)
        if not wd and not dp:
            continue
        bal = _dec(g("balance")) if "balance" in best and g("balance") not in (None, "") else None
        pending = Txn(d, str(g("narration") or "").strip(), str(g("ref") or "").strip(), wd, dp, bal)
        out.append(pending)
    _check_balances(out, warn)
    st = Statement(out, best, header, warn)
    st.signature = header_signature(rows[hdr_i])
    return st


_PDF_LINE = re.compile(r"^\s*(\d{1,2}[/\-. ](?:\d{1,2}|[A-Za-z]{3})[/\-. ]\d{2,4})\s+(.*?)\s+"
                       r"((?:[\d,]+\.\d{2}\s*){1,3})(?:Cr|Dr|CR|DR)?\s*$")


def parse_pdf(path: Path) -> Statement:
    """Text-layer PDF statements: lines starting with a date and ending with 1-3 amounts. Direction comes from
    the running balance (balance up = deposit, down = withdrawal)."""
    from ..extract.readers import read_pdf
    doc = read_pdf(path)
    out, warn = [], []
    prev_bal = None
    pending = None
    for ln in doc.text.splitlines():
        ob = re.search(r"opening\s+balance\D*([\d,]+\.\d{2})", ln, re.I)
        if ob and not out:
            prev_bal = _dec(ob.group(1))
            continue
        m = _PDF_LINE.match(ln)
        if not m:
            if pending and ln.strip() and not re.search(r"page \d|opening balance|closing balance", ln, re.I):
                if len(ln.strip()) < 80 and not re.search(r"\d+\.\d{2}", ln):
                    pending.narration += " " + ln.strip()
            continue
        d = parse_date(m.group(1))
        nums = [_dec(x) for x in re.findall(r"[\d,]+\.\d{2}", m.group(3))]
        body = m.group(2)
        ref = ""
        rm = re.search(r"\b(\d{6,}|[A-Z]{4}\d{6,}\w*)\b", body)
        if rm:
            ref = rm.group(1)
        bal = nums[-1] if len(nums) >= 2 else None
        amt = nums[-2] if len(nums) >= 2 else nums[0]
        if bal is not None and prev_bal is not None:
            wd, dp = (amt, Decimal(0)) if bal < prev_bal else (Decimal(0), amt)
        else:
            dr = re.search(r"\b(dr|debit|withdrawal|to )\b", body, re.I)
            wd, dp = (amt, Decimal(0)) if dr else (Decimal(0), amt)
            if bal is None:
                warn.append(f"{d}: no balance column; direction guessed from text")
        prev_bal = bal if bal is not None else prev_bal
        pending = Txn(d, body.strip(), ref, wd, dp, bal)
        out.append(pending)
    if not out:
        raise ValueError("No transactions found in this PDF (scanned statements aren't supported; use Excel/CSV)")
    _check_balances(out, warn)
    return Statement(out, {"source": "pdf"}, [], warn)


def _check_balances(txns: list[Txn], warn: list[str]) -> None:
    bad = 0
    for a, b in zip(txns, txns[1:]):
        if a.balance is None or b.balance is None:
            continue
        exp = a.balance - b.withdrawal + b.deposit
        exp2 = a.balance + b.withdrawal - b.deposit          # statements printed newest-first
        if abs(exp - b.balance) > 1 and abs(exp2 - b.balance) > 1:
            bad += 1
    if bad:
        warn.append(f"{bad} line(s) don't follow from the running balance - check the column mapping")


# ------------------------------------------------------------------ matching
STOP = {"NEFT", "RTGS", "IMPS", "UPI", "TRF", "TRANSFER", "INB", "MOB", "MB", "BY", "TO", "FROM", "CR", "DR",
        "REF", "NO", "IFT", "ACH", "NACH", "CHQ", "CLG", "INWARD", "OUTWARD", "PAYMENT", "PVT", "LTD", "LIMITED",
        "PRIVATE", "THE", "AND", "BANK", "HDFC", "ICICI", "SBI", "INDUSIND", "INDB", "AXIS", "KOTAK", "YES",
        "FOR", "VIA", "ONLINE", "NETBANKING", "NET", "BANKING", "PAY", "PAID", "RECEIVED", "BENEFICIARY", "A/C",
        "ACCOUNT", "INR", "RS", "TXN", "TRAN", "NA", "AUTO", "DEBIT", "CREDIT", "FUNDS", "FUND", "INDIA"}


def tokens(text: str) -> list[str]:
    toks = re.findall(r"[A-Za-z][A-Za-z&]{2,}", text.upper())
    return [t for t in toks if t not in STOP]


_CP_SPLIT = re.compile(r"[/\-|:]+")


def counterparty(narration: str) -> str:
    """'UPI/DR/412345678901/RAMESH KUMAR/HDFC/...' -> 'RAMESH KUMAR';
    'NEFT-HDFC0000123-ABC TRADERS PVT LTD-INV 45' -> 'ABC TRADERS PVT LTD'."""
    up = narration.upper()
    if not re.search(r"\b(UPI|NEFT|IMPS|RTGS|IFT|INB|MMT|TRF)\b", up):
        return ""
    best = ""
    for part in _CP_SPLIT.split(up):
        p = part.strip()
        if len(p) < 4 or re.search(r"\d{4,}", p) or re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", p):
            continue                                  # numbers, UTRs, IFSC codes
        words = [w for w in re.findall(r"[A-Z&.]+", p) if w not in STOP]
        if len(words) >= 1 and len(" ".join(words)) > len(best):
            best = " ".join(words)
    return best if len(best) >= 4 else ""


@dataclass
class BankSuggestion:
    ledger: str
    vtype: str            # Payment | Receipt | Contra
    confidence: str       # green | amber | red
    note: str
    in_tally: str = ""    # description of the existing Tally voucher, if any


def _norm(s: str) -> str:
    return re.sub(r"\b(pvt|private|ltd|limited|llp|co|company|the|m/s|and)\b|[^a-z0-9]", "", s.lower())


def find_in_tally(session: Session, company_id: str, bank_ledger: str, t: Txn, days: int = 3) -> str:
    d0 = datetime.strptime(t.date, "%Y%m%d")
    lo, hi = (d0 - timedelta(days=days)).strftime("%Y%m%d"), (d0 + timedelta(days=days)).strftime("%Y%m%d")
    want_dr = t.direction == "in"           # deposit: bank is debited
    for v in _hv(session, company_id, lo, hi):
        for e in v.entries or []:
            if e["ledger"] == bank_ledger and e["dr"] == want_dr and abs(Decimal(e["amount"]) - t.amount) < 1:
                return f"{v.voucher_type} {v.number} on {v.date[6:8]}-{v.date[4:6]}-{v.date[:4]}"
    return ""


class SuggestContext:
    """Everything suggest() needs, prepared once per company + bank (instead of once per statement line):
    learned rules, normalised ledger names, an index of past Tally entries by narration word and by date."""

    def __init__(self, session: Session, company: Company, m: Masters, bank_ledger: str):
        self.rules = list(session.scalars(select(BankRule).where(BankRule.company_id == company.id,
                                                                 BankRule.active.is_(True))))
        self.names = [(n, _norm(n)) for n in sorted(m.ledgers, key=len, reverse=True)
                      if m.ledgers[n].get("_primary") not in ("Duties & Taxes",) and n != bank_ledger]
        self.party_pool = [n for n, d in m.ledgers.items() if d.get("_primary") in (
            "Sundry Creditors", "Sundry Debtors", "Loans & Advances (Asset)", "Current Liabilities",
            "Capital Account", "Unsecured Loans") and n != bank_ledger]
        self.by_token: dict[str, list] = {}
        self.by_date: dict[str, list] = {}
        for v in _hv(session, company.id):
            ents = v.entries or []
            bank_e = next((e for e in ents if e["ledger"] == bank_ledger), None)
            if not bank_e:
                continue
            others = [e["ledger"] for e in ents if e["ledger"] != bank_ledger]
            rec = (bank_e["dr"], Decimal(bank_e["amount"]), others, v)
            self.by_date.setdefault(v.date, []).append(rec)
            for tok in set(tokens(v.narration or "")):
                self.by_token.setdefault(tok, []).append(rec)
        self.fuzzy_cache: dict[str, tuple] = {}

    def in_tally(self, t: Txn, days: int = 3) -> str:
        d0 = datetime.strptime(t.date, "%Y%m%d")
        want_dr = t.direction == "in"
        for k in range(-days, days + 1):
            day = (d0 + timedelta(days=k)).strftime("%Y%m%d")
            for dr, amt, _o, v in self.by_date.get(day, []):
                if dr == want_dr and abs(amt - t.amount) < 1:
                    return f"{v.voucher_type} {v.number} on {v.date[6:8]}-{v.date[4:6]}-{v.date[:4]}"
        return ""


def suggest(session: Session, company: Company, m: Masters, bank_ledger: str, t: Txn,
            ctx: "SuggestContext | None" = None) -> BankSuggestion:
    if ctx is None:
        ctx = SuggestContext(session, company, m, bank_ledger)
    toks = set(tokens(t.narration))
    narr_norm = _norm(t.narration)
    in_tally = ctx.in_tally(t)

    def vtype_for(ledger: str) -> str:
        if m.ledgers.get(ledger, {}).get("_primary") in ("Bank Accounts", "Cash-in-Hand", "Bank OD A/c"):
            return "Contra"
        return "Payment" if t.direction == "out" else "Receipt"

    def mk(ledger, conf, note):
        return BankSuggestion(ledger, vtype_for(ledger), conf, note, in_tally)

    # 1) learned rules
    best, best_score = None, 0
    for r in ctx.rules:
        if r.direction and r.direction != t.direction:
            continue
        kw = set(r.keywords or [])
        if not kw:
            continue
        overlap = len(kw & toks) / len(kw)
        score = overlap * (1 + min(r.hits, 5) / 10)
        if overlap >= 0.6 and score > best_score and r.ledger in m.ledgers:
            best, best_score = r, score
    if best:
        return mk(best.ledger, "green" if best.hits >= 2 and best_score >= 0.9 else "amber",
                  f"Learned: {', '.join(best.keywords[:4])} → {best.ledger} ({best.hits}×)")

    # 2) a party / ledger name appears in the narration
    for n, nn in ctx.names:
        if len(nn) >= 5 and nn in narr_norm:
            return mk(n, "amber", f"Ledger name '{n}' appears in the narration")

    # 2b) the counterparty name inside UPI / NEFT / IMPS / RTGS narrations, matched loosely to party ledgers
    cp = counterparty(t.narration)
    if cp:
        if cp not in ctx.fuzzy_cache:
            ctx.fuzzy_cache[cp] = m.fuzzy(cp, ctx.party_pool, cutoff=0.8)
        hit, score = ctx.fuzzy_cache[cp]
        if hit:
            return mk(hit, "amber", f"Name in narration '{cp}' looks like '{hit}' ({score:.0%})")

    # 3) past Tally entries through this bank with similar narration
    votes: Counter = Counter()
    seen: dict[int, int] = {}
    recs: dict[int, tuple] = {}
    for tok in toks:
        for rec in ctx.by_token.get(tok, []):
            if rec[0] != (t.direction == "in"):
                continue
            seen[id(rec)] = seen.get(id(rec), 0) + 1
            recs[id(rec)] = rec
    for k, overlap in seen.items():
        if overlap >= 2 or (overlap == 1 and len(toks) <= 2):
            for led in recs[k][2]:
                votes[led] += overlap
    if votes:
        ledger, _ = votes.most_common(1)[0]
        return mk(ledger, "amber", "Similar narration in past Tally entries for this bank")

    # 4) common bank items
    up = t.narration.upper()
    patterns = [
        (r"\bCHG|CHARGE|CHRG|COMMISSION|SMS|AMC\b|DEBIT CARD FEE|SERVICE FEE", r"bank\s*charge", "Bank charges"),
        (r"\bGST\b|IGST|CGST|SGST", r"bank\s*charge", "GST on bank charges"),
        (r"\bINT(EREST)?\b.*\b(PD|PAID|CR|CREDIT)\b|^INT\.|INTEREST", r"interest", "Interest"),
        (r"\bATM\b|CASH\s*W|CSH\s*WDL|\bSELF\b", r"^cash$|cash\s*in\s*hand|petty\s*cash", "Cash withdrawal"),
        (r"SALARY|SAL\b|PAYROLL", r"salary\s*payable|salary", "Salary"),
        (r"\bTDS\b|\bTAX\b.*\bCHALLAN|OLTAS|CBDT", r"tds\s*payable|tds", "Tax payment"),
        (r"\bGSTN\b|GST\s*PMT|GST\s*CHALLAN|CPIN", r"gst\s*payable|electronic\s*cash", "GST payment"),
    ]
    for pat, led_pat, label in patterns:
        if re.search(pat, up):
            ledger = m.find(led_pat, None)
            if ledger:
                return mk(ledger, "amber", f"{label} (from narration)")
    return BankSuggestion("", "Payment" if t.direction == "out" else "Receipt", "red", "No match - pick a ledger",
                          in_tally)


def build_voucher(company: Company, m: Masters, bank_ledger: str, t: Txn, ledger: str, vtype: str,
                  narration: str = "") -> Voucher:
    amt = t.amount.quantize(Q)
    bill = "On Account" if m.ledgers.get(ledger, {}).get("ISBILLWISEON", "").lower() == "yes" else ""
    counter = VLine(ledger, amt, t.direction == "out", "party", "", "green", bill_ref=bill)
    counter.bill_type = "On Account" if bill else ""
    # foreign-currency client / supplier: carry the foreign amount and rate from the bank narration, the way
    # Tally itself records it (an INR-only amount on a USD ledger leaves Tally guessing the rate)
    from .exports import forex_ledgers, parse_remittance
    cur = forex_ledgers(m).get(ledger)
    if cur:
        fx = parse_remittance(f"{t.narration} {t.ref}")
        if fx:
            counter.fx_cur, counter.fx_qty, counter.fx_rate = cur, fx[0], fx[1]
    bank = VLine(bank_ledger, amt, t.direction == "in", "bank", "", "green")
    lines = [counter, bank] if t.direction == "out" else [bank, counter]
    narr = narration or (t.narration + (f" (Ref {t.ref})" if t.ref and t.ref not in t.narration else ""))
    return Voucher(vtype=vtype, base_type=vtype, date=t.date, lines=lines, narration=narr[:900])


def learn(session: Session, company: Company, bank_ledger: str, t: Txn, ledger: str) -> None:
    kw = [w for w, _ in Counter(tokens(t.narration)).most_common(4)]
    if not kw:
        return
    rules = session.scalars(select(BankRule).where(BankRule.company_id == company.id, BankRule.ledger == ledger,
                                                   BankRule.direction == t.direction)).all()
    for r in rules:
        if set(r.keywords or []) & set(kw):
            r.hits += 1
            r.keywords = list(dict.fromkeys((r.keywords or []) + kw))[:6] if r.hits < 3 else r.keywords
            session.commit()
            return
    session.add(BankRule(company_id=company.id, bank_ledger=bank_ledger, keywords=kw, direction=t.direction,
                         ledger=ledger, hits=1))
    session.commit()


def store(session: Session, company: Company, bank_ledger: str, st: Statement) -> tuple[int, int]:
    """Save new lines (duplicates from overlapping statements are skipped). Returns (new, duplicate)."""
    known = set(session.scalars(select(BankLine.line_hash).where(BankLine.company_id == company.id,
                                                                 BankLine.bank_ledger == bank_ledger)))
    new = dup = 0
    for t in st.txns:
        h = t.key()
        if h in known:
            dup += 1
            continue
        known.add(h)
        session.add(BankLine(company_id=company.id, bank_ledger=bank_ledger, line_hash=h, date=t.date,
                             narration=t.narration, reference=t.ref, withdrawal=float(t.withdrawal),
                             deposit=float(t.deposit), balance=float(t.balance) if t.balance is not None else 0.0))
        new += 1
    session.commit()
    return new, dup


def txn_of(line: BankLine) -> Txn:
    return Txn(line.date, line.narration, line.reference, Decimal(str(line.withdrawal)).quantize(Q),
               Decimal(str(line.deposit)).quantize(Q), Decimal(str(line.balance)).quantize(Q))


# ------------------------------------------------------------------ match vs categorise
@dataclass
class Match:
    vouchers: list            # VoucherHistory rows
    description: str
    score: float


def match_candidates(session: Session, company_id: str, bank_ledger: str, t: Txn, days: int = 7,
                     max_combo: int = 3) -> list[Match]:
    """Existing Tally vouchers through this bank that explain the line: one voucher with the same amount, or 2-3
    vouchers on nearby dates that add up to it (e.g. one deposit = several receipts)."""
    from itertools import combinations
    d0 = datetime.strptime(t.date, "%Y%m%d")
    lo, hi = (d0 - timedelta(days=days)).strftime("%Y%m%d"), (d0 + timedelta(days=days)).strftime("%Y%m%d")
    want_dr = t.direction == "in"
    claimed = set()
    for ref in session.scalars(select(BankLine.reference).where(BankLine.company_id == company_id,
                                                               BankLine.status == "in_tally")):
        claimed.update(x for x in re.split(r"[ ,]", ref or "") if x.startswith("vch:"))
    pool = []
    for v in _hv(session, company_id, lo, hi):
        amt = sum((Decimal(e["amount"]) for e in v.entries or []
                   if e["ledger"] == bank_ledger and e["dr"] == want_dr), Decimal(0))
        if amt and f"vch:{v.guid[-12:]}" not in claimed:
            pool.append((v, amt))
    out = []
    for v, amt in pool:
        if abs(amt - t.amount) < 1:
            gap = abs((datetime.strptime(v.date, "%Y%m%d") - d0).days)
            out.append(Match([v], f"{v.voucher_type} {v.number} on {v.date[6:8]}-{v.date[4:6]}", 1 - gap / 30))
    if not out and len(pool) <= 40:
        for k in range(2, max_combo + 1):
            for combo in combinations(pool, k):
                if abs(sum((a for _, a in combo), Decimal(0)) - t.amount) < 1:
                    desc = " + ".join(f"{v.voucher_type} {v.number}" for v, _ in combo)
                    out.append(Match([v for v, _ in combo], desc, 0.6 - k / 10))
            if out:
                break
    return sorted(out, key=lambda m: -m.score)[:5]


def mark_matched(session: Session, line: BankLine, match: Match) -> None:
    line.status = "in_tally"
    line.reference = (line.reference + " " if line.reference and not line.reference.startswith("vch:") else "") \
        + ",".join(f"vch:{v.guid[-12:]}" for v in match.vouchers)
    line.reference = line.reference[-120:]
    session.commit()


# ------------------------------------------------------------------ duplicate protection (before anything is posted)
@dataclass
class ImportVerdict:
    txn: Txn
    kind: str          # new | dup_imported | in_tally | possible
    reason: str = ""


def _narr_key(s: str) -> set[str]:
    return set(tokens(s)) | set(re.findall(r"\d{6,}", s or ""))


def classify_import(session: Session, company_id: str, bank_ledger: str, st: Statement,
                    days: int = 3) -> list[ImportVerdict]:
    """Check every statement line from all sides - date, amount, direction, narration, cheque / UTR, running
    balance - against (a) lines imported earlier and (b) vouchers already in Tally for this bank.
    Overlapping statements (books done to 15-10, statement 01-10 to 31-10) only bring in 16-10 onwards."""
    earlier = list(session.scalars(select(BankLine).where(BankLine.company_id == company_id,
                                                          BankLine.bank_ledger == bank_ledger)))
    hashes = {ln.line_hash for ln in earlier}
    by_amt: dict[tuple, list[BankLine]] = {}
    for ln in earlier:
        by_amt.setdefault((ln.date, round(ln.withdrawal, 2), round(ln.deposit, 2)), []).append(ln)
    if st.txns:
        lo = (datetime.strptime(min(t.date for t in st.txns), "%Y%m%d") - timedelta(days=days)).strftime("%Y%m%d")
        hi = (datetime.strptime(max(t.date for t in st.txns), "%Y%m%d") + timedelta(days=days)).strftime("%Y%m%d")
    else:
        lo = hi = ""
    tally = []
    for v in _hv(session, company_id, lo, hi):
        for e in v.entries or []:
            if e["ledger"] == bank_ledger:
                tally.append((v, Decimal(e["amount"]), e["dr"]))
    used: set = set()                       # each Tally voucher explains one line only
    seen_in_file: dict[tuple, int] = {}
    out = []
    for t in st.txns:
        key_amt = (t.date, float(t.withdrawal), float(t.deposit))
        k = seen_in_file.get(key_amt, 0)
        seen_in_file[key_amt] = k + 1
        # (a) imported before: identical line, or same date + amount + direction with matching narration / ref /
        #     balance (wrapped narration or a different export format of the same statement)
        if t.key() in hashes:
            out.append(ImportVerdict(t, "dup_imported", "Same line already imported"))
            continue
        cands = by_amt.get((t.date, round(float(t.withdrawal), 2), round(float(t.deposit), 2)), [])
        hit = None
        for ln in cands:
            same_bal = t.balance is not None and ln.balance and abs(float(t.balance) - ln.balance) < 0.01
            same_ref = t.ref and ln.reference and t.ref.strip() == ln.reference.strip()
            overlap = _narr_key(t.narration) & _narr_key(ln.narration)
            if same_bal or same_ref or len(overlap) >= 2 or t.narration.strip() == ln.narration.strip():
                hit = ln
                break
        if hit is None and len(cands) > k and not t.narration.strip():
            hit = cands[k]
        if hit is not None:
            why = "balance" if t.balance is not None and hit.balance and abs(float(t.balance) - hit.balance) < .01 \
                else "narration / reference"
            out.append(ImportVerdict(t, "dup_imported", f"Already imported ({hit.date[6:8]}-{hit.date[4:6]}, "
                                                        f"same amount and {why})"))
            continue
        # (b) already in Tally
        want_dr = t.direction == "in"
        best, best_score = None, 0
        for i, (v, amt, dr) in enumerate(tally):
            if i in used or dr != want_dr or abs(amt - t.amount) >= 1:
                continue
            gap = abs((datetime.strptime(v.date, "%Y%m%d") - datetime.strptime(t.date, "%Y%m%d")).days)
            score = 3 if gap == 0 else 2 if gap <= 1 else 1
            text = f"{v.narration} {v.reference} {v.number}"
            if t.ref and len(t.ref) >= 4 and t.ref in text:
                score += 4
            score += min(len(_narr_key(t.narration) & _narr_key(text)), 3)
            if score > best_score:
                best, best_score = i, score
        if best is not None and best_score >= 3:
            used.add(best)
            v = tally[best][0]
            out.append(ImportVerdict(t, "in_tally", f"In Tally: {v.voucher_type} {v.number} on "
                                                    f"{v.date[6:8]}-{v.date[4:6]}"))
        elif best is not None:
            v = tally[best][0]
            out.append(ImportVerdict(t, "possible", f"Possibly in Tally: {v.voucher_type} {v.number} on "
                                                    f"{v.date[6:8]}-{v.date[4:6]} (same amount, date "
                                                    f"{abs(int(v.date) - int(t.date))} day(s) apart)"))
        else:
            out.append(ImportVerdict(t, "new"))
    return out


def recheck_new_lines(session: Session, company_id: str, bank_ledger: str, days: int = 3) -> list[tuple]:
    """Lines judged 'new' at import can be entered in Tally afterwards from another statement - a transfer posted
    as Contra from the HDFC statement is the same money as the deposit on the ICICI statement, a card autopay
    posted from the bank is the 'payment received' on the card statement. Re-check every 'new' line of this bank
    against Tally (the app's copy, which includes what the app just posted) and mark it 'in_tally'.
    Each Tally voucher explains one line only: vouchers already accounted for by this bank's posted / in-Tally
    lines are set aside first, so a second line of the same amount is never hidden by the first one's voucher.
    Returns (line, description) for every line marked."""
    lines = list(session.scalars(select(BankLine).where(BankLine.company_id == company_id,
                                                        BankLine.bank_ledger == bank_ledger)))
    pending = [ln for ln in lines if ln.status == "new"]
    if not pending:
        return []
    dates = [datetime.strptime(ln.date, "%Y%m%d") for ln in lines]
    lo = (min(dates) - timedelta(days=days)).strftime("%Y%m%d")
    hi = (max(dates) + timedelta(days=days)).strftime("%Y%m%d")
    tally = []
    for v in _hv(session, company_id, lo, hi):
        for e in v.entries or []:
            if e["ledger"] == bank_ledger:
                tally.append((v, Decimal(e["amount"]), e["dr"]))
    used: set = set()

    def gap(v, ln):
        return abs((datetime.strptime(v.date, "%Y%m%d") - datetime.strptime(ln.date, "%Y%m%d")).days)

    def amount_side(ln):
        return (Decimal(str(ln.deposit)), True) if ln.deposit else (Decimal(str(ln.withdrawal)), False)

    # 1. set aside the vouchers that this bank's posted / matched lines stand for (nearest date first)
    for ln in sorted((x for x in lines if x.status in ("posted", "in_tally")), key=lambda x: x.date):
        amt, dr = amount_side(ln)
        cands = [(gap(v, ln), i) for i, (v, a, d) in enumerate(tally)
                 if i not in used and d == dr and abs(a - amt) < 1 and gap(v, ln) <= days]
        if cands:
            used.add(min(cands)[1])
    # 2. what is left can explain a 'new' line (same scoring as at import: date, reference, narration words)
    marked = []
    for ln in sorted(pending, key=lambda x: x.date):
        amt, dr = amount_side(ln)
        best, best_score = None, 0
        for i, (v, a, d) in enumerate(tally):
            if i in used or d != dr or abs(a - amt) >= 1 or gap(v, ln) > days:
                continue
            g = gap(v, ln)
            score = 3 if g == 0 else 2 if g <= 1 else 1
            text = f"{v.narration} {v.reference} {v.number}"
            if ln.reference and len(ln.reference) >= 4 and ln.reference in text:
                score += 4
            score += min(len(_narr_key(ln.narration) & _narr_key(text)), 3)
            if score > best_score:
                best, best_score = i, score
        if best is not None and best_score >= 3:
            used.add(best)
            v = tally[best][0]
            ln.status = "in_tally"
            desc = f"{v.voucher_type} {v.number} on {v.date[6:8]}-{v.date[4:6]}-{v.date[:4]}"
            marked.append((ln, desc))
    if marked:
        session.commit()
    return marked


def store_classified(session: Session, company: Company, bank_ledger: str, verdicts: list[ImportVerdict],
                     include_possible: bool = True) -> dict:
    """Save only lines that aren't duplicates; lines already in Tally are kept but marked (never posted)."""
    counts = {"new": 0, "dup_imported": 0, "in_tally": 0, "possible": 0}
    known = set(session.scalars(select(BankLine.line_hash).where(BankLine.company_id == company.id,
                                                                 BankLine.bank_ledger == bank_ledger)))
    for vd in verdicts:
        counts[vd.kind] += 1
        if vd.kind == "dup_imported":
            continue
        h = vd.txn.key()
        if h in known:
            continue
        known.add(h)
        t = vd.txn
        status = "in_tally" if vd.kind == "in_tally" or (vd.kind == "possible" and not include_possible) else "new"
        session.add(BankLine(company_id=company.id, bank_ledger=bank_ledger, line_hash=h, date=t.date,
                             narration=t.narration, reference=(t.ref or "")[:120], withdrawal=float(t.withdrawal),
                             deposit=float(t.deposit), balance=float(t.balance) if t.balance is not None else 0.0,
                             status=status))
    session.commit()
    return counts


# ------------------------------------------------------------------ closing balance: statement vs Tally
@dataclass
class BalanceCheck:
    as_on: str
    statement: Decimal | None        # bank's figure (credit balance = money in the account)
    tally: Decimal | None            # books, same convention (Tally Dr balance shown positive)
    pending_lines: list              # statement lines not yet in Tally
    tally_only: list                 # Tally vouchers through this bank not on the statement
    note: str = ""

    @property
    def difference(self) -> Decimal | None:
        if self.statement is None or self.tally is None:
            return None
        return (self.statement - self.tally).quantize(Q)

    @property
    def explained(self) -> Decimal:
        pend = sum((Decimal(str(l.deposit)) - Decimal(str(l.withdrawal)) for l in self.pending_lines), Decimal(0))
        only = sum((amt if dr else -amt for _v, amt, dr in self.tally_only), Decimal(0))
        return (pend - only).quantize(Q)


def _day_closing(day: list) -> Decimal | None:
    """Closing balance of one statement day, worked out from the running-balance chain, not from row order
    (row order in the app changes when lines are posted). The closing line is the one whose balance is not
    the 'balance before' of any other line that day."""
    rows = [l for l in day if l.balance]
    if not rows:
        return None
    r2 = lambda x: Decimal(str(x)).quantize(Q)
    befores = [r2(l.balance) + r2(l.withdrawal) - r2(l.deposit) for l in rows]
    bals = [r2(l.balance) for l in rows]
    ends = [b for b in bals if bals.count(b) > befores.count(b)]
    if len(set(ends)) == 1:
        return ends[0]
    # chain broken (missing / skipped lines): start of the day plus the day's net movement
    starts = [b for b in befores if befores.count(b) > bals.count(b)]
    if len(set(starts)) == 1:
        return starts[0] - sum((r2(l.withdrawal) for l in rows), Decimal(0)) + \
            sum((r2(l.deposit) for l in rows), Decimal(0))
    return bals[-1]


def statement_closing(lines: list[BankLine]) -> tuple[str, Decimal | None]:
    """Last date and closing balance of the imported statement lines."""
    dated = [l for l in lines if l.date]
    if not dated:
        return "", None
    last_date = max(l.date for l in dated)
    return last_date, _day_closing([l for l in dated if l.date == last_date])


def balance_check(session: Session, company_id: str, bank_ledger: str, tally_closing: Decimal | None,
                  as_on: str = "", period_from: str = "") -> BalanceCheck:
    """tally_closing: the bank ledger's closing balance from Tally on `as_on` (Tally sign: negative = Dr)."""
    lines = list(session.scalars(select(BankLine).where(BankLine.company_id == company_id,
                                                        BankLine.bank_ledger == bank_ledger)
                                 .order_by(BankLine.date, BankLine.updated_at)))
    d, closing = statement_closing([l for l in lines if not as_on or l.date <= as_on])
    as_on = as_on or d
    pending = [l for l in lines if l.status == "new" and l.date <= as_on and (not period_from or l.date >= period_from)]
    lo = period_from or (min((l.date for l in lines), default=as_on))
    stmt_keys = [(l.date, round(l.withdrawal, 2), round(l.deposit, 2)) for l in lines if lo <= l.date <= as_on]
    remaining = list(stmt_keys)
    only = []
    for v in _hv(session, company_id, lo, as_on):
        for e in v.entries or []:
            if e["ledger"] != bank_ledger:
                continue
            amt = Decimal(e["amount"])
            vd = datetime.strptime(v.date, "%Y%m%d")
            match = None
            for i, (dt, wd, dp) in enumerate(remaining):
                if abs((datetime.strptime(dt, "%Y%m%d") - vd).days) <= 5 and \
                        abs(Decimal(str(dp if e["dr"] else wd)) - amt) < 1:
                    match = i
                    break
            if match is None:
                only.append((v, amt, e["dr"]))
            else:
                remaining.pop(match)
    books = -tally_closing if tally_closing is not None else None
    note = "" if closing is not None else "The statement has no balance column - closing balance can't be compared"
    return BalanceCheck(as_on, closing, books, pending, only, note)
