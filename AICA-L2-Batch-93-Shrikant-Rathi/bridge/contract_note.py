"""
Contract-note reader: turns a broker's PDF contract note into proposed equity transactions for review.

Nothing here saves anything. The bridge returns the preview; a person checks it, and the confirmed trades go through
ledger.add_txns, which validates every row again (security master, valuation date, no oversell) and audits the import.

Broker layouts differ, so the parser does not rely on column positions. It uses checks that hold on any note:
  * a trade line carries a quantity and a rate whose product is printed on the SAME line (gross value or net total);
    a line where no such pair exists is never read as a trade;
  * the security is identified by ISIN where printed, otherwise by name against the security master;
  * the note's own arithmetic is reconciled: buys - sells + charges must equal the net amount printed on the note.
Anything that fails a check is shown to the user as an issue, never silently corrected.

Cost basis: brokerage, exchange and SEBI fees, stamp duty and GST are incidental to the trade and are allocated to
purchase cost / deducted from sale value in proportion to trade value. Securities Transaction Tax is NOT allocated:
it is not deductible in computing capital gains (s. 48, Income-tax Act 1961; confirm the corresponding provision of
the Income-tax Act 2025 before relying on it).
"""
import hashlib
import io
import re
from datetime import date, datetime

MAX_BYTES = 10 * 1024 * 1024
ISIN_RE = re.compile(r"\bIN[A-Z0-9]{9}\d\b")
NUM_RE = re.compile(r"\(?-?(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?\)?")
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
DATE_PAT = r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4}|\d{1,2}[\s\-/]?[A-Za-z]{3}[A-Za-z]*[\s\-/,]*\d{4}|\d{4}-\d{2}-\d{2})"
SIDE_WORDS = {"BUY": "Buy", "BOUGHT": "Buy", "PURCHASE": "Buy", "B": "Buy", "SELL": "Sell", "SOLD": "Sell", "SALE": "Sell", "S": "Sell"}
SIDE_RE = re.compile(r"(?<![A-Za-z])(BUY|BOUGHT|PURCHASE|SELL|SOLD|SALE|Buy|Bought|Purchase|Sell|Sold|Sale|B|S)(?![A-Za-z])")
NAME_STOP = {"NSE", "BSE", "EQ", "BE", "CM", "NORMAL", "CASH", "DELIVERY", "INTRADAY", "EQUITY", "SHARES", "SERIES", "RS", "INR", "NA"}
CHARGE_LABELS = [  # (key, pattern); GST lines are summed (CGST + SGST or IGST), the others take the first line found
    ("stt", re.compile(r"securities\s+transaction\s+tax|\bstt\b", re.I)),
    ("brokerage", re.compile(r"brokerage", re.I)),
    ("exchange", re.compile(r"exchange\s+(?:transaction|txn|turnover)|transaction\s+charges|clearing\s+charges", re.I)),
    ("sebi", re.compile(r"sebi", re.I)),
    ("stamp", re.compile(r"stamp", re.I)),
    ("gst", re.compile(r"\b(?:c|s|i|u)?gst\b|service\s+tax", re.I)),
]
NET_RE = re.compile(r"net\s+amount|net\s+(?:receivable|payable)|amount\s+(?:payable|receivable)|net\s+obligation", re.I)


class ContractNoteError(ValueError):
    """The file cannot be read as a contract note; shown to the user as-is."""


def _num(tok):
    neg = tok.startswith("(") and tok.endswith(")") or tok.startswith("-")
    v = float(tok.strip("()").replace(",", "").lstrip("-"))
    return -v if neg else v


def _parse_date(s):
    s = " ".join(s.replace(",", " ").split())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%d %B %Y", "%d/%b/%Y", "%d%b%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


PASSWORD_HINT = "Enter its password (brokers usually use the PAN in capitals, sometimes with the date of birth)."


def read_text(data, password="", what="contract note", hint=PASSWORD_HINT, err=None):
    """Plain text of every page, one string per page. Raises ContractNoteError (or `err`) with a user-facing reason."""
    try:
        return _read_text(data, password, what, hint)
    except ContractNoteError as e:
        if err is None:
            raise
        raise err(str(e)) from None


def _read_text(data, password, what, hint):
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
    if len(data) > MAX_BYTES:
        raise ContractNoteError(f"The file is larger than 10 MB; a {what} is normally well under that.")
    if not data.lstrip()[:5] == b"%PDF-":
        raise ContractNoteError("This is not a PDF file.")
    try:
        r = PdfReader(io.BytesIO(data))
        if r.is_encrypted:
            if not password:
                raise ContractNoteError(f"This {what} is password-protected. {hint}")
            if not r.decrypt(password):
                raise ContractNoteError(f"The password is not correct for this {what}.")
        pages = []
        for p in r.pages:
            try:
                t = p.extract_text(extraction_mode="layout")
            except Exception:  # noqa: BLE001 - fall back to the plain extractor on odd pages
                t = p.extract_text()
            pages.append(t or "")
    except ContractNoteError:
        raise
    except (PdfReadError, ValueError, KeyError) as e:
        raise ContractNoteError(f"The PDF could not be read ({e}).") from None
    if not "".join(pages).strip():
        raise ContractNoteError(f"No text was found in the PDF. It is probably a scanned image; get the electronic {what} instead.")
    return pages


def _trade_from_line(line):
    """(side, qty, rate, value, gross_rate, isin, name) if the line is a self-consistent trade line, else None."""
    m = SIDE_RE.search(line)
    if not m:
        return None
    isin_m = ISIN_RE.search(line)
    work = ISIN_RE.sub(" ", line)
    work = TIME_RE.sub(" ", work)
    work = re.sub(DATE_PAT, " ", work)
    toks = [t for t in NUM_RE.findall(work)]
    nums = []
    for t in toks:
        digits = t.strip("()-").replace(",", "")
        if "." not in digits and "," not in t and len(digits) >= 8:  # order / trade numbers, not amounts
            continue
        try:
            nums.append((_num(t), "." in digits))
        except ValueError:
            continue
    vals = [abs(v) for v, _ in nums]

    def search(allow_decimal_qty):
        # q x r = v with all three printed on the line. Share quantities are printed without decimals and rates with
        # them, which is what tells "20 x 2,950.00" from "2,950 x 20" (same product, so reconciliation cannot).
        best = None
        for qi, (q, qdec) in enumerate(nums):
            q = abs(q)
            if q <= 0 or q != int(q) or q > 5e7 or (qdec and not allow_decimal_qty):
                continue
            for ri, r in enumerate(vals):
                if ri == qi or r <= 0:
                    continue
                for vi, v in enumerate(vals):
                    if vi in (qi, ri) or v < r:
                        continue
                    if abs(q * r - v) <= max(0.02, 0.0005 * v) and (best is None or (not nums[ri][1], v) < (not nums[best[3]][1], best[2])):
                        best = (q, r, v, ri)  # prefer a rate printed with decimals, then the smaller (gross) value
        return best

    best, qty_doubt = search(False), False
    if not best:
        best, qty_doubt = search(True), True
    if not best:
        return None
    q, r, v, _ = best
    side = SIDE_WORDS[m.group(1).upper()]
    # all rates on the line that also reproduce a printed value: gross and net rate may both be there
    rates = sorted({x for x in vals if x > 0 and x != q and any(abs(q * x - y) <= max(0.02, 0.0005 * y) for y in vals if y != x)})
    gross = r
    if len(rates) >= 2:
        gross = min(rates) if side == "Buy" else max(rates)
    else:  # net rate only: look for a per-unit brokerage b with r = g + b (buy) or r = g - b (sell) printed on the line
        for b in vals:
            if 0 < b < r * 0.05:
                g = r - b if side == "Buy" else r + b
                if any(abs(g - x) <= 0.011 for x in vals):
                    gross = next(x for x in vals if abs(g - x) <= 0.011)
                    break
    name_part = SIDE_RE.sub(" ", ISIN_RE.sub(" ", TIME_RE.sub(" ", line)))
    name_part = NUM_RE.sub(" ", re.sub(DATE_PAT, " ", name_part))
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z&.\-']*", name_part) if w.upper().strip(".") not in NAME_STOP]
    name = " ".join(words).strip(" -.")
    return {"side": side, "qty": int(q), "rate": round(gross, 4), "printed_rate": round(r, 4), "value": round(q * gross, 2),
            "isin": isin_m.group(0) if isin_m else None, "name": name, "qty_doubt": qty_doubt}


def _norm(s):
    s = re.sub(r"[^A-Z0-9 ]", " ", (s or "").upper().replace("&", " AND "))
    return " ".join(w for w in s.split() if w not in {"LTD", "LIMITED", "THE", "EQ", "EQUITY", "SHARES", "CO", "COMPANY", "INDIA", "IND"})


def match_company(trade, companies):
    if trade["isin"]:
        c = next((c for c in companies if c.get("isin") == trade["isin"]), None)
        if c:
            return c["code"], "ISIN"
    n = _norm(trade["name"])
    if not n:
        return None, None
    for c in companies:
        if n == _norm(c["name"]) or n == c["code"].upper():
            return c["code"], "name"
    hits = [c for c in companies if _norm(c["name"]) and (n.startswith(_norm(c["name"]) + " ") or _norm(c["name"]).startswith(n + " "))]
    if len(hits) == 1:
        return hits[0]["code"], "name (partial)"
    return None, None


RATE_TOLERANCE = 0.25  # a rate more than 25% from the surrounding month-end prices is flagged for review


def parse(data, password="", companies=(), as_on=None, priced=None, ref_prices=None):
    """Preview of the contract note. `priced(code)` says whether a company can be valued; `as_on` is the valuation date;
    `ref_prices(code, iso_date)` returns the month-end closes either side of the date, for the rate plausibility check."""
    pages = read_text(data, password)
    text = "\n".join(pages)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    warnings = []

    td = None
    m = re.search(r"trade\s*date\s*[:\-]?\s*" + DATE_PAT, text, re.I)
    if m:
        td = _parse_date(m.group(1))
    if not td:
        warnings.append("Trade date not found on the note; enter it before recording.")
    m = re.search(r"contract\s*note\s*(?:no|number)\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]{2,40})", text, re.I)
    note_no = m.group(1) if m else None

    fills, charges, net_amount, gst = [], {}, None, 0.0
    gst_seen = False
    for ln in lines:
        t = _trade_from_line(ln)
        if t:
            fills.append(t)
            continue
        nums = [abs(_num(x)) for x in NUM_RE.findall(TIME_RE.sub(" ", re.sub(DATE_PAT, " ", ln))) if x.strip("()-")]
        if not nums:
            continue
        if NET_RE.search(ln) and net_amount is None:
            net_amount = nums[-1]
            continue
        for key, pat in CHARGE_LABELS:
            if pat.search(ln):
                if key == "gst":
                    gst += nums[-1]; gst_seen = True
                elif key not in charges:
                    charges[key] = nums[-1]
                break
    if gst_seen:
        charges["gst"] = round(gst, 2)
    if not fills:
        raise ContractNoteError("No trades were recognised. The layout of this broker's note is not supported yet; enter the trades by hand, and share a sample (with personal details removed) so it can be added.")

    # one proposed transaction per security and side (fills at different prices are averaged, weighted by quantity)
    groups = {}
    for f in fills:
        k = (f["isin"] or _norm(f["name"]), f["side"])
        g = groups.setdefault(k, {"side": f["side"], "isin": f["isin"], "name": f["name"], "qty": 0, "value": 0.0, "fills": 0, "qty_doubt": False})
        g["qty"] += f["qty"]; g["value"] += f["value"]; g["fills"] += 1; g["qty_doubt"] |= f["qty_doubt"]
    trades = list(groups.values())

    buys = sum(t["value"] for t in trades if t["side"] == "Buy")
    sells = sum(t["value"] for t in trades if t["side"] == "Sell")
    all_charges = sum(charges.values())
    alloc_pool = all_charges - charges.get("stt", 0.0)
    turnover = buys + sells
    expected = abs(buys - sells + all_charges)
    recon = {"buys": round(buys, 2), "sells": round(sells, 2), "charges": round(all_charges, 2), "expected_net": round(expected, 2),
             "stated_net": net_amount, "difference": None, "status": "not found"}
    if net_amount is not None:
        diff = round(net_amount - expected, 2)
        recon.update(difference=diff, status="reconciled" if abs(diff) <= 1.0 else "difference")
        if recon["status"] == "difference":
            warnings.append(f"The note does not reconcile: trades and charges give Rs {expected:,.2f} but the note states Rs {net_amount:,.2f}. Check every row before recording.")
    else:
        warnings.append("Net amount not found on the note, so the trades could not be reconciled to it.")
    if not charges:
        warnings.append("No charges were found; prices will be the exchange rates only.")

    for t in trades:
        t["rate"] = round(t["value"] / t["qty"], 4)
        share = alloc_pool * t["value"] / turnover if turnover else 0.0
        t["charges"] = round(share, 2)
        t["price_with_charges"] = round((t["value"] + share if t["side"] == "Buy" else t["value"] - share) / t["qty"], 4)
        t["value"] = round(t["value"], 2)
        code, basis = match_company(t, companies)
        t["instrument"], t["match"] = code, basis
        issues = []
        if not code:
            issues.append("Company not identified; choose it from the list (add it first with '+ Fetch any company' if it is missing).")
        elif priced and not priced(code):
            issues.append(f"{code} has no price on the valuation date, so it cannot be recorded yet.")
        if t.pop("qty_doubt"):
            issues.append("The quantity was printed with decimals, so quantity and rate may be swapped; check both.")
        if code and td and ref_prices:
            refs = [p for p in ref_prices(code, td.isoformat()) if p]
            if refs and all(abs(t["rate"] / p - 1) > RATE_TOLERANCE for p in refs):
                near = min(refs, key=lambda p: abs(t["rate"] / p - 1))
                issues.append(f"Rate Rs {t['rate']:,.2f} is {abs(t['rate'] / near - 1):.0%} away from the month-end price Rs {near:,.2f}; "
                              "check the quantity, the rate and the company (a split or bonus also causes this).")
            t["ref_price"] = refs[0] if refs else None
        if td and as_on and td.isoformat() > as_on:
            issues.append(f"Trade date is after the valuation date {as_on}; refresh the data first.")
        t["issues"] = issues

    return {"sha256": hashlib.sha256(data).hexdigest(), "pages": len(pages), "contract_note_no": note_no,
            "trade_date": td.isoformat() if td else None, "trades": trades, "charges": {k: round(v, 2) for k, v in charges.items()},
            "reconciliation": recon, "warnings": warnings}
