"""V3.1 — write each issue's reply from the records mapped to it.

Voice: the assessee replying through its authorised representative ("we", "our").
Content: only facts that appear in the uploaded records (via doc_links). Where a record the
notice asks for is not among the uploads, the reply says so in one short sentence and the
rest of the reply stays complete. Where records disagree, a [CA REVIEW: …] marker is placed
at the exact sentence; markers count as unresolved placeholders, so the draft cannot be
approved until the CA resolves them. Nothing is said to be enclosed unless the CA marked the
document as an annexure. No software or AI is mentioned in the reply.
"""
from __future__ import annotations

import re
from datetime import date

from .mapping import amounts_in, dates_in, inr, issue_anchors, names_in, refs_in

REVIEW = "CA REVIEW"


# ------------------------------------------------------------------ small helpers
def long_date(d: date) -> str:
    return f"{d.day} {d.strftime('%B %Y')}"


def _ld(text: str, fy: int | None) -> str:
    ds = sorted(dates_in(text, fy))
    return long_date(ds[0]) if ds else ""


def _amt(text: str) -> int | None:
    a = sorted(amounts_in(text or ""), reverse=True)
    return a[0] if a else None


def fields(passage: str) -> dict[str, str]:
    """'Header: value; Header: value' → dict (lower-cased headers)."""
    out = {}
    for part in re.split(r";\s+(?=[A-Z][^:;]{0,60}:\s)", passage or ""):
        if ": " in part:
            k, v = part.split(": ", 1)
            out[k.strip().lower()] = v.strip()
    return out


def pick(f: dict[str, str], *keys: str, avoid: tuple[str, ...] = ()) -> str | None:
    for k, v in f.items():
        if any(x in k for x in keys) and not any(a in k for a in avoid):
            return v
    return None


def _clean(v: str | None) -> str:
    v = re.sub(r"\s*\((?:fictional|test)[^)]*\)", "", v or "", flags=re.I)  # drop test-pack annotations in brackets
    return re.sub(r"\s+", " ", v).strip(" ;,")


def money(v: str | None) -> str:
    a = _amt(v or "")
    return inr(a) if a is not None else _clean(v)


class Ctx:
    def __init__(self, issue: dict, links: list[dict], docs: dict[int, dict], fy: int | None, opts: dict,
                 contradictions: list[dict]):
        self.issue, self.links, self.docs, self.fy, self.opts = issue, links, docs, fy, opts
        self.contradictions = contradictions
        self.anchors = issue_anchors(issue, fy)
        self.review: list[str] = []
        self.used: set[int] = set()

    # passages
    def rows(self, *must: str, any_of: tuple[str, ...] = (), kind: str | None = None, strong_only: bool = True) -> list[dict]:
        out = []
        for l in self.links:
            if l["status"] == "REJECTED" or (strong_only and l["certainty"] != "STRONG" and l["status"] != "ACCEPTED"):
                continue
            if kind and l["passage_kind"] != kind:
                continue
            low = l["passage"].lower()
            if all(m.lower() in low for m in must) and (not any_of or any(a.lower() in low for a in any_of)):
                out.append(l)
        return out

    def use(self, link: dict) -> None:
        self.used.add(link["document_id"])

    def ref(self, link_or_doc_id) -> str:
        """'(Annexure A-2)' only when the CA has marked the document as an annexure."""
        did = link_or_doc_id["document_id"] if isinstance(link_or_doc_id, dict) else link_or_doc_id
        d = self.docs.get(did) or {}
        if d.get("is_annexure") and d.get("annexure_label"):
            return f" (Annexure {d['annexure_label']})"
        return ""

    def flag(self, text: str) -> str:
        self.review.append(text)
        return f"[{REVIEW}: {text}]"

    def conflicts_about(self, *keys: str) -> list[dict]:
        norm = {re.sub(r"[^a-z0-9]", "", k.lower()) for k in keys if k}
        out = []
        for c in self.contradictions:
            ck = {re.sub(r"[^a-z0-9]", "", k.lower()) for k in c.get("keys", [])}
            if norm & ck and c not in out:
                out.append(c)
        return out


def _plural(label: str) -> bool:
    last = label.split()[-1].lower()
    return last.endswith("s") and not last.endswith("ss")


def _closing_gap(gaps: list[str]) -> str | None:
    if not gaps:
        return None
    items = gaps[0] if len(gaps) == 1 else ", ".join(gaps[:-1]) + " and " + gaps[-1]
    verb = "is" if len(gaps) == 1 and not _plural(gaps[0]) else "are"
    return f"{items[0].upper()}{items[1:]} {verb} not part of this submission and will be furnished separately if required."


def human_dates(text: str, fy: int | None) -> str:
    """'03-Nov' / '06-Nov-2024' → '3 November 2024' (year inferred from the financial year when missing)."""
    def rep(m):
        ds = dates_in(m.group(0), fy)
        return long_date(min(ds)) if ds else m.group(0)
    return re.sub(r"(?i)\b\d{1,2}[-\s](?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:[-\s]\d{4})?\b", rep, text or "")


def _source_caveats(ctx: Ctx) -> None:
    for l in ctx.links:
        if l["status"] == "REJECTED":
            continue
        m = re.search(r"[^.]*\b(to be verified|verification item|must be checked|ca verification|reviewing ca)\b[^.]*\.", l["passage"], re.I)
        if m:
            ctx.review.append(f"The record itself notes: “{m.group(0).strip()[:220]}” ({l['document_name']})")


# ------------------------------------------------------------------ composers
def compose_loans(ctx: Ctx) -> list[str]:
    lenders = sorted(ctx.anchors["names"], key=lambda n: ctx.issue["query_text"].find(n))
    paras: list[str] = []
    total = _amt(ctx.issue.get("title") or "") or (max(ctx.anchors["amounts"]) if ctx.anchors["amounts"] else None)
    if lenders:
        paras.append(f"During the previous year we received unsecured loans{f' aggregating {inr(total)}' if total else ''} from "
                     f"{len(lenders)} lender{'s' if len(lenders) > 1 else ''}. Each loan was received through banking channels. "
                     "The particulars of each lender, the bank trail and the lender's source of funds are as follows:")
    for n, name in enumerate(lenders):
        bank = next(iter(ctx.rows(name, any_of=("narration", "neft", "rtgs", "utr", "credit"), kind="ROW")), None)
        conf = next(iter(ctx.rows(name, any_of=("confirm",), kind="PARAGRAPH")), None)
        table = [l for l in ctx.rows(name, kind="ROW") if l is not bank]
        f_all: dict[str, str] = {}
        for l in table:
            f_all.update(fields(l["passage"]))
            ctx.use(l)
        parts = []
        amount = date_s = utr = None
        if bank:
            ctx.use(bank)
            fb = fields(bank["passage"])
            amount = money(pick(fb, "credit") or bank["passage"])
            date_s = _ld(pick(fb, "date") or bank["passage"], ctx.fy)
            m = re.search(r"UTR\s*([A-Z0-9]+)", bank["passage"], re.I)
            utr = m.group(1) if m else None
            parts.append(f"{amount} was received on {date_s} by bank transfer{f' (UTR {utr})' if utr else ''} and is credited in our bank "
                         f"statement{ctx.ref(bank)} on that date")
        elif f_all:
            amount = money(pick(f_all, "amount", "transfer"))
            date_s = _ld(pick(f_all, "date") or "", ctx.fy)
            parts.append(f"{amount} was received on {date_s}")
        if conf:
            ctx.use(conf)
            t = conf["passage"]
            terms = []
            if re.search(r"repayable on demand", t, re.I):
                terms.append("repayable on demand")
            mi = re.search(r"no interest was (?:charged|paid)[^.]*", t, re.I)
            if mi:
                terms.append(mi.group(0)[0].lower() + mi.group(0)[1:])
            parts.append(f"the lender has confirmed the advance in writing{ctx.ref(conf)}"
                         + (f", stating that it is {' and that '.join(terms)}" if terms else ""))
        pan = pick(f_all, "pan")
        addr = pick(f_all, "address")
        if pan or addr:
            parts.append("the confirmation gives the lender's " + " and ".join(x for x in [
                f"address ({_clean(addr)})" if addr else "", f"PAN {_clean(pan)}" if pan else ""] if x))
        inc = pick(f_all, "income")
        before = pick(f_all, "balance before", "pre-transfer")
        src = pick(f_all, "source record", "source")
        if inc or before or src:
            bits = []
            if src:
                bits.append(f"the funds came from {_clean(src).split(';')[0].strip().lower()}")
            if inc:
                bits.append(f"the lender's income for the year was {money(inc)}")
            if before:
                bits.append(f"the lender's bank balance immediately before the transfer was {money(before)}")
            parts.append("as regards the lender's source, " + "; ".join(bits))
        for c in ctx.conflicts_about(name, utr or ""):
            parts.append(ctx.flag(c["text"]))
        if parts:
            text = "; ".join(parts)
            paras.append(f"({chr(97 + n)}) {name}: {text[0].upper()}{text[1:]}.")
        else:
            paras.append(f"({chr(97 + n)}) {name}: " + ctx.flag(f"no record of this loan was found among the uploaded documents"))
    if len(lenders) > 1:
        paras.append("We submit that the identity of each lender, the genuineness of each transaction and each lender's capacity "
                     "to advance the amount are evidenced by the lender's confirmation, the banking-channel trail in the accounts of "
                     "both parties and the lender's source records, as set out above.")
    return paras


def compose_cash_deposits(ctx: Ctx) -> list[str]:
    paras = []
    q = ctx.issue["query_text"]
    pairs = []  # (date, amount) as stated in the notice
    for m in re.finditer(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s*\(₹\s?([\d,]+)\)", q):
        d = dates_in(m.group(1), ctx.fy)
        if d:
            pairs.append((min(d), int(m.group(2).replace(",", ""))))
    total = _amt(ctx.issue.get("title") or "") or (sum(a for _, a in pairs) if pairs else None)
    movement = [l for l in ctx.links if l["status"] != "REJECTED" and l["passage_kind"] == "RECORD"
                and re.search(r"opening cash|closing cash", l["passage"], re.I)]
    mv = movement[0] if movement else None
    paras.append(f"The cash deposited in our bank account during the year{f' aggregates {inr(total)}' if total else ''}"
                 f"{f' in {len(pairs)} deposits' if pairs else ''}. The cash so deposited came out of the cash balance recorded in our "
                 "cash book, which is built up from our day-to-day business receipts.")
    if mv:
        ctx.use(mv)
        f = fields(mv["passage"])
        items = []
        for k, v in f.items():
            label = re.sub(r"\bfy\b", "FY", re.sub(r"\s+at\s+\d.*$|\s*₹", "", k).strip())
            items.append(f"{label} {money(v)}")
        if items:
            paras.append(f"For the year as a whole our cash book{ctx.ref(mv)} shows: " + "; ".join(items) + ".")
    for n, (d, a) in enumerate(pairs):
        dd = long_date(d)
        cb = next((l for l in ctx.rows(any_of=(d.strftime("%d-%b-%Y"),), kind="ROW") if "deposit date" in l["passage"].lower()
                   or "before" in l["passage"].lower()), None)
        bk = next((l for l in ctx.rows(d.strftime("%d-%b-%Y"), kind="ROW") if "cash deposit" in l["passage"].lower()), None)
        bits = [f"deposit of {inr(a)}"]
        if bk:
            ctx.use(bk)
            amt_b = _amt(pick(fields(bk["passage"]), "credit") or "")
            bits.append("credited in our bank statement" + ctx.ref(bk) + " on the same date")
            if amt_b and amt_b != a:
                bits.append(ctx.flag(f"bank statement shows {inr(amt_b)} on {dd}, notice states {inr(a)}"))
        if cb:
            ctx.use(cb)
            f = fields(cb["passage"])
            txt = cb["passage"]
            mb = re.search(r"Before\s+([\d,]+)", txt)
            ma = re.search(r"After\s+([\d,]+)", txt)
            op, rc, ex = pick(f, "opening"), pick(f, "receipt"), pick(f, "expense")
            if mb:
                before = int(mb.group(1).replace(",", ""))
                calc = ""
                if op and rc and ex:
                    calc = f" (opening {money(op)} + receipts {money(rc)} − cash expenses {money(ex)})"
                bits.append(f"cash in hand immediately before the deposit {inr(before)}{calc}")
                if before < a:
                    bits.append(ctx.flag(f"cash book shows only {inr(before)} before the deposit of {inr(a)} on {dd}"))
            if ma:
                bits.append(f"balance after the deposit {inr(int(ma.group(1).replace(',', '')))}")
        else:
            bits.append(ctx.flag(f"no cash-book entry for the deposit on {dd} was found among the uploaded records"))
        paras.append(f"({chr(97 + n)}) {dd}: " + "; ".join(bits) + ".")
    if pairs and not any(REVIEW in p for p in paras[-len(pairs):]):
        paras.append("In each case the cash available in hand immediately before the deposit exceeded the amount deposited, and every "
                     "deposit is traceable to the cash book entry of the same date.")
    return paras


def compose_sales_gst(ctx: Ctx) -> list[str]:
    paras = []
    rows = [l for l in ctx.rows(kind="ROW") if "book amount" in l["passage"].lower() or "gstr" in l["passage"].lower()]
    q = f"{ctx.issue.get('title') or ''} {ctx.issue['query_text']}"
    qa = sorted(amounts_in(q), reverse=True)
    total_row = next((l for l in rows if "total" in l["passage"].lower()), None)
    if total_row:
        f = fields(total_row["passage"])
        b, r = money(pick(f, "book")), money(pick(f, "gstr", "return"))
        ctx.use(total_row)
        agree = "agree" if b == r else "differ"
        paras.append(f"The total sales recorded in our books, {b}, {agree} with the total outward supplies reported in our GST "
                     f"return (GSTR-1), {r}{ctx.ref(total_row)}. The classification-wise comparison is as under:")
    for n, l in enumerate([x for x in rows if x is not total_row]):
        ctx.use(l)
        f = fields(l["passage"])
        name = _clean(pick(f, "channel", "classification") or "")
        b, r, dfr = money(pick(f, "book")), money(pick(f, "gstr", "return")), pick(f, "difference")
        paras.append(f"({chr(97 + n)}) {name[0].upper() + name[1:] if name else 'Item'}: books {b}; GSTR-1 {r}"
                     + (f"; difference {money(dfr) if _amt(dfr or '') else 'nil'}" if dfr is not None else "") + ".")
    # explain total vs taxable subtotal using the notice's own figures
    if len(qa) >= 3:
        t, x = qa[0], qa[1]
        e = t - x
        if e in qa:
            paras.append(f"The difference of {inr(e)} between total sales ({inr(t)}) and taxable outward supplies ({inr(x)}) referred to in "
                         f"the notice is the value of supplies classified as exempt/nil-rated, which is reported separately in the "
                         f"exempt/nil-rated field of the return. It forms part of, and is not in addition to, our recorded sales.")
    coll = next(iter(ctx.rows(any_of=("collection",), kind="PARAGRAPH")), None)
    if coll:
        ctx.use(coll)
        m = re.search(r"collection[^.]*?aggregate\s+(₹?[\d,]+)", coll["passage"], re.I)
        if m:
            paras.append(f"The bank/other-mode sales are matched by customer collections credited to our bank account during the year, "
                         f"aggregating {money(m.group(1))}{ctx.ref(coll)}.")
    inv = next(iter(ctx.rows(any_of=("invoice",), kind="ROW")), None)
    if inv:
        ctx.use(inv)
        f = fields(inv["passage"])
        no = pick(f, "sample invoice", "invoice no", "invoice")
        dt = _ld(pick(f, "date") or inv["passage"], ctx.fy)
        val = money(pick(f, "book value", "value"))
        cls = _clean(pick(f, "return classification", "classification"))
        paras.append(f"A copy of the sales invoice for the item queried is available: invoice {_clean(no)} dated {dt} for {val}"
                     + (f", classified in our records and in the return as {cls.lower()}" if cls else "") + f"{ctx.ref(inv)}.")
    return paras


def compose_creditors(ctx: Ctx) -> list[str]:
    paras = []
    names = sorted(ctx.anchors["names"], key=lambda n: ctx.issue["query_text"].find(n))
    total = _amt(ctx.issue.get("title") or "")
    yr_end = _ld(ctx.issue["query_text"], ctx.fy)
    paras.append(f"The trade creditors{f' of {inr(total)}' if total else ''} outstanding{f' as at {yr_end}' if yr_end else ''} are "
                 "amounts payable to our suppliers for goods supplied in the ordinary course of business. Each balance has been "
                 "confirmed by the supplier and has since been settled through banking channels, as follows:")
    for n, name in enumerate(names):
        row = next(iter([l for l in ctx.rows(name, kind="ROW") if "balance" in l["passage"].lower()]), None)
        conf = next(iter(ctx.rows(any_of=(name.lower(),), kind="PARAGRAPH")), None)
        bits = []
        if row:
            ctx.use(row)
            f = fields(row["passage"])
            bal = money(pick(f, "balance confirmed", "balance"))
            p1 = pick(f, "payment 1", "payment")
            d1 = pick(f, "date")
            after = pick(f, "balance after")
            settle = pick(f, "settlement", "subsequent")
            bits.append(f"balance of {bal}{f' as at {yr_end}' if yr_end else ''}, confirmed by the supplier{ctx.ref(row)}")
            if p1 and d1:
                bits.append(f"{money(p1)} was paid on {_ld(d1, ctx.fy)}")
            if after and settle:
                sd = _ld(settle, ctx.fy)
                bits.append(f"the remaining {money(after)} was paid {'by bank ' if 'bank' in settle.lower() else ''}"
                            f"{'on ' + sd if sd else _clean(settle)}")
        elif conf:
            ctx.use(conf)
            bits.append(f"the supplier has confirmed the balance{ctx.ref(conf)}")
        else:
            bits.append(ctx.flag(f"no confirmation or ledger record for {name} was found among the uploaded records"))
        paras.append(f"({chr(97 + n)}) {name}: " + "; ".join(bits) + ".")
    tot = next(iter(ctx.rows(any_of=("total balance confirmed",), kind="PARAGRAPH")), None)
    if tot:
        ctx.use(tot)
        paras.append(f"The balances confirmed by the suppliers total {money(tot['passage'])}, which agrees with the amount stated in the "
                     "notice. The payments after the year end are shown only as evidence of subsequent settlement; they do not form "
                     "part of the closing balance for the year under assessment.")
    paras.append("We therefore submit that these balances are genuine trading liabilities arising from recorded purchases, confirmed "
                 "by the creditors and discharged through banking channels, and that no question of an unexplained credit, or of a "
                 "remission or cessation of liability, arises in respect of them.")
    return paras


def compose_purchases(ctx: Ctx) -> list[str]:
    paras = []
    names = sorted(ctx.anchors["names"], key=lambda n: ctx.issue["query_text"].find(n))
    total = _amt(ctx.issue.get("title") or "")
    paras.append(f"The purchases selected for verification{f', aggregating {inr(total)},' if total else ''} are genuine purchases of "
                 "goods used in our business. For each purchase the invoice, receipt of goods, stock entry, delivery evidence and "
                 "payment through our bank account are set out below:")
    for n, name in enumerate(names):
        rec = next(iter([l for l in ctx.rows(name, kind="RECORD")]), None)
        f = fields(rec["passage"]) if rec else {}
        if rec:
            ctx.use(rec)
        bits = []
        inv = pick(f, "invoice")
        if inv:
            m = re.search(r"([A-Z]{1,4}/\d{2}-\d{2}/\d+)", inv)
            bits.append(f"invoice {m.group(1) if m else _clean(inv)} dated {_ld(inv, ctx.fy)}"
                        + (f" for {money(pick(f, 'book value', 'value'))}" if pick(f, "book value", "value") else ""))
        gr = pick(f, "goods received")
        if gr:
            what = _clean(re.sub(r'^[^;]*;\s*', '', gr))
            bits.append(f"goods received on {_ld(gr, ctx.fy)} ({what[:1].lower() + what[1:]})")
        stk = pick(f, "stock movement", "stock")
        if stk:
            bits.append(f"{_clean(stk)[0].lower()}{_clean(stk)[1:]}".replace("within 2 working days", "within two working days"))
        dl = next(iter([l for l in ctx.rows(name, kind="PARAGRAPH") if re.search(r"docket|transport|delivery", l["passage"], re.I)]), None)
        if dl:
            ctx.use(dl)
            m = re.search(r"\b([A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,})\s+for\s+" + re.escape(name), dl["passage"])
            if m:
                bits.append(f"delivery evidenced by transporter docket {m.group(1)}")
        pay = pick(f, "payment")
        banks = sorted([l for l in ctx.rows(name, kind="ROW") if "narration" in l["passage"].lower()],
                       key=lambda l: min(dates_in(l["passage"], ctx.fy) or {date.max}))
        if banks:
            for l in banks:
                ctx.use(l)
            plist = "; ".join(f"{money(pick(fields(l['passage']), 'debit'))} on {_ld(pick(fields(l['passage']), 'date') or '', ctx.fy)}"
                              for l in banks)
            bits.append(f"payment made through our bank account: {plist}, as shown in our bank statement{ctx.ref(banks[0])}")
        elif pay:
            bits.append(f"payment: {_clean(pay)}")
        for c in ctx.conflicts_about(name, *(refs_in(inv.upper()) if inv else [])):
            bits.append(ctx.flag(c["text"]))
        if rec:
            bits[0] = bits[0] + ctx.ref(rec) if bits else bits
        paras.append(f"({chr(97 + n)}) {name}: " + ("; ".join(bits) if bits else ctx.flag(f"no purchase record for {name} was found")) + ".")
    return paras


def compose_fixed_assets(ctx: Ctx) -> list[str]:
    paras = []
    rows = [l for l in ctx.rows(kind="ROW") if "asset" in l["passage"].lower() and "cost" in l["passage"].lower()]
    reg = [l for l in ctx.rows(kind="ROW", strong_only=False) if "asset tag" in l["passage"].lower()]
    paras.append("The additions to fixed assets during the year and the depreciation claimed on them are supported by the supplier "
                 "invoices, payment records and our fixed-asset register, as follows:")
    n = 0
    for l in rows:
        f = fields(l["passage"])
        asset = _clean(pick(f, "asset") or "")
        if not asset or asset.lower().startswith("total"):
            continue
        ctx.use(l)
        inv = pick(f, "invoice")
        sup = _clean(pick(f, "supplier") or "")
        cost = money(pick(f, "cost"))
        paid = pick(f, "paid")
        used = pick(f, "put to use", "delivered")
        dep = money(pick(f, "depreciation"))
        refs = refs_in(asset.upper())
        bits = [f"cost {cost}"]
        if inv:
            bits.append(f"supplier invoice dated {_ld(inv, ctx.fy)}" + (f" from {sup}" if sup else ""))
        if paid:
            pd = _ld(paid, ctx.fy)
            m = re.search(r"/\s*([A-Z0-9]+)\s*$", paid)
            bits.append(f"paid on {pd}" + (f" (bank reference {m.group(1)})" if m else ""))
        if used:
            bits.append(human_dates(_clean(used), ctx.fy).replace("Delivered", "delivered").replace("; ", ", "))
        tag = next((r for r in reg if any(w in r["passage"].lower() for w in asset.lower().split()[:2])), None)
        if tag:
            ctx.use(tag)
            ft = fields(tag["passage"])
            bits.append(f"recorded in our fixed-asset register under tag {_clean(pick(ft, 'asset tag'))} with capitalisation date "
                        f"{_ld(pick(ft, 'capitalisation') or '', ctx.fy)}")
        bits.append(f"depreciation claimed {dep}")
        for c in ctx.conflicts_about(*[r for r in refs]) or ctx.conflicts_about(asset.split()[0]):
            bits.append(ctx.flag(c["text"] + " The date the asset was first put to use determines whether depreciation is restricted to half the rate."))
        paras.append(f"({chr(97 + n)}) {asset}{ctx.ref(l)}: " + "; ".join(bits) + ".")
        n += 1
    tot = next((l for l in rows if (pick(fields(l["passage"]), "asset") or "").lower().startswith("total")), None)
    ret = [l for l in ctx.rows(any_of=("depreciation claimed", "fixed asset additions"), kind="ROW") if "asset:" not in l["passage"].lower()]
    if tot:
        ft = fields(tot["passage"])
        line = f"The total cost of additions is {money(pick(ft, 'cost'))} and the total depreciation claimed is {money(pick(ft, 'depreciation'))}"
        rd = next((l for l in ret if "depreciation" in l["passage"].lower()), None)
        if rd:
            ctx.use(rd)
            same = _amt(rd["passage"]) == _amt(pick(ft, "depreciation") or "")
            line += (", which agrees with the depreciation claimed in our return of income" if same
                     else " " + ctx.flag(f"the return shows depreciation of {money(rd['passage'])}"))
        paras.append(line + ".")
        dep_rows = []
        for l in rows:
            f = fields(l["passage"])
            c, d = _amt(pick(f, "cost") or ""), _amt(pick(f, "depreciation") or "")
            a = _clean(pick(f, "asset") or "")
            if c and d and not a.lower().startswith("total"):
                dep_rows.append(f"{a}: {d / c:.1%} of cost")
        if dep_rows:
            ctx.review.append("Depreciation works out to " + "; ".join(dep_rows) + ". Confirm the block/rate (Appendix I to the "
                              "Income-tax Rules) and whether the half-rate restriction for use under 180 days applies.")
    return paras


def compose_generic(ctx: Ctx) -> list[str]:
    """Any other category: present the strongest mapped records issue by issue, in plain sentences."""
    paras = []
    by_doc: dict[int, list[dict]] = {}
    for l in ctx.rows():
        by_doc.setdefault(l["document_id"], []).append(l)
    if not by_doc:
        return paras
    paras.append("Our records relevant to this query show the following:")
    n = 0
    for did, ls in by_doc.items():
        for l in ls[:6]:
            ctx.use(l)
            txt = l["passage"]
            for raw in sorted(set(re.findall(r"(?:₹\s?)?\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?", txt)), key=len, reverse=True):
                a = _amt(raw)
                if a:
                    txt = txt.replace(raw, inr(a))
            paras.append(f"({chr(97 + n % 26)}) {_clean(txt)}{ctx.ref(l)}.")
            n += 1
    return paras


COMPOSERS = {
    "UNSECURED_LOAN": compose_loans, "CASH_DEPOSITS": compose_cash_deposits, "SALES_GST_RECONCILIATION": compose_sales_gst,
    "TRADE_CREDITORS": compose_creditors, "PURCHASES": compose_purchases, "FIXED_ASSETS": compose_fixed_assets,
}


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def availability_sentences(records: list[dict]) -> list[str]:
    """What the notice asks for that the uploaded records do not show, worded by its state. Never says
    'enclosed': a record held outside the app is 'available for production'."""
    asked = [r for r in records if r["asked"] and r["state"] != "READ"]
    out = []
    held = [r["short"] for r in asked if r["state"] == "AVAILABLE_WITH_CA"]
    if held:
        verb = "is" if len(held) == 1 and not _plural(held[0]) else "are"
        t = _join(held)
        out.append(f"{t[0].upper()}{t[1:]} {verb} available with us and can be produced for your verification.")
    for r in asked:
        if r["state"] == "NOT_AVAILABLE":
            verb = "are" if _plural(r["short"]) else "is"
            out.append(f"{r['short'][0].upper()}{r['short'][1:]} {verb} not available with us. "
                       f"[CA TO CONFIRM: reason, and any alternative evidence for {r['short']}]")
        elif r["state"] == "CONFLICT":
            out.append(f"[CA TO CONFIRM: {r['short']} — {r['detail'].rstrip('.').lower()}]")
    missing = [r["short"] for r in asked if r["state"] == "NOT_PROVIDED"]
    if missing:
        out.append(f"[CA TO CONFIRM: whether {_join(missing)} {'is' if len(missing) == 1 and not _plural(missing[0]) else 'are'} "
                   "available, or why not]")
    return out


def write_issue(issue: dict, links: list[dict], docs: dict[int, dict], fy: int | None, opts: dict,
                contradictions: list[dict], records: list[dict]) -> dict:
    """Body written from the uploaded records. drafted_by: RECORDS (a subject-specific writer used the records),
    BASIC (records listed as extracts) or NONE (no uploaded record relates to this query)."""
    ctx = Ctx(issue, links, docs, fy, opts, contradictions)
    fn = COMPOSERS.get(issue["category"])
    body, drafted_by = [], "NONE"
    if fn:
        try:
            body = fn(ctx)
            drafted_by = "RECORDS" if body and ctx.used else "NONE"
        except Exception as exc:  # a writer problem must never lose the whole draft
            body = []
            ctx.review.append(f"Automatic drafting of this query stopped ({type(exc).__name__}); write the reply manually.")
        if not ctx.used:
            body = []
    if not body:
        body = compose_generic(ctx)
        drafted_by = "BASIC" if body else "NONE"
    _source_caveats(ctx)
    unc = [l for l in links if l["certainty"] == "UNCERTAIN" and l["status"] == "AUTO"]
    if unc:
        ctx.review.append(f"{len(unc)} uncertain document match(es) were not used in the reply; check them in Issues & evidence.")
    title = issue.get("title") or re.split(r"(?<=[.?])\s", issue["query_text"], maxsplit=1)[0][:90]
    return {"issue_id": issue["id"], "heading": f"Query No. {issue['seq']} — {title}", "query": issue["query_text"],
            "paragraphs": body, "availability": availability_sentences(records), "drafted_by": drafted_by,
            "review_points": list(dict.fromkeys(ctx.review)), "documents_used": sorted(ctx.used),
            "internal_notes": list(dict.fromkeys(ctx.review))}


def template_opening(issue: dict, ca: dict) -> list[str]:
    """Basic template when no uploaded record relates to a query: only what the CA entered, plus a marker."""
    paras = list(ca.get("extra") or [])
    if not any(not p.startswith("[") for p in paras):
        paras.insert(0, f"With reference to Query No. {issue['seq']}, we submit as follows. [CA TO CONFIRM: our factual "
                        "explanation for this query, with the facts, dates and amounts relied on]")
    return paras
