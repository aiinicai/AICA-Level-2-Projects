"""Reader for the CDSL Consolidated Account Statement (CAS). Runs on this laptop only.

Reads the PDF by position on the page (not by the order the PDF stores its text),
because CAS pages store some lines out of order.

What it extracts
  - statement period
  - mutual fund holdings per folio: units, NAV, cumulative amount invested (cost), value, gain
  - mutual fund transactions of the period per scheme: opening units, each transaction, closing units
  - demat holdings (shares, ETFs): quantity, price, value
  - month-end portfolio value for the last 12 months, and the asset class split

It never guesses. Anything it cannot place goes to `issues` or `unplaced`.
Money is Decimal, not float.
"""
import re
from decimal import Decimal, InvalidOperation

D = Decimal
NUM = r"-?\d[\d,]*(?:\.\d+)?"
ISIN_RE = re.compile(r"IN[EF][0-9A-Z]{9}|IN[0-9][0-9A-Z]{9}")
DATE_DMY = re.compile(r"^(\d{2})-(\d{2})-(\d{4})\b")
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


class PasswordError(Exception):
    pass


class NeedsPackageError(Exception):
    pass


def num(s):
    try:
        return D(s.replace(",", ""))
    except InvalidOperation:
        return None


# ----------------------------------------------------------------------------- reading by position
def _walk(el):
    from pdfminer.layout import LTTextLine
    if isinstance(el, LTTextLine):
        yield el
        return
    try:
        children = list(el)
    except TypeError:
        return
    for c in children:
        yield from _walk(c)


def _clean(s):
    a = re.sub(r"[^\x00-\x7f]", "", s)
    if len(a.strip()) < 0.5 * len(s.strip()):
        return ""                      # mostly Hindi or garbled: skip
    return re.sub(r"\s+", " ", a).strip()


def _cluster(frags):
    """frags: (y0, y1, x0, text). Returns visual rows, top to bottom, left to right."""
    frags = [f for f in frags if f[3]]
    frags.sort(key=lambda f: -((f[0] + f[1]) / 2))
    rows, cur, cur_y = [], [], None
    for f in frags:
        yc = (f[0] + f[1]) / 2
        if cur_y is None or abs(yc - cur_y) <= 3.0:
            cur.append(f)
            cur_y = yc if cur_y is None else cur_y
        else:
            rows.append(cur)
            cur, cur_y = [f], yc
    if cur:
        rows.append(cur)
    out = []
    for r in rows:
        r = sorted(r, key=lambda f: f[2])
        line = r[0][3]
        for prev, f in zip(r, r[1:]):
            size = f[4] if len(f) > 4 else 0
            if size:                                    # pieces of one word (pypdf) are joined without a space
                gap = f[2] - (prev[2] + len(prev[3]) * size * 0.5)
                line += ("" if gap < 0.15 * size else " ") + f[3]
            else:
                line += " " + f[3]
        out.append(line)
    return out


def _read_pdfminer(path, password):
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LAParams
    pages = []
    for layout in extract_pages(str(path), password=password or "", laparams=LAParams(boxes_flow=None)):
        frags = []
        for ln in _walk(layout):
            t = _clean(ln.get_text())
            if t:
                frags.append((ln.y0, ln.y1, ln.x0, t))
        pages.append(_cluster(frags))
    return pages


def _read_pypdf(path, password):
    """Second reader: pypdf with the position of every text piece (works where pdfminer finds no text)."""
    from pypdf import PdfReader
    r = PdfReader(str(path))
    if r.is_encrypted and not r.decrypt(password or ""):
        raise PasswordError("password did not open the file")
    pages = []
    piece_stats = [0, 0]
    for p in r.pages:
        frags = []

        def visit(text, cm, tm, font_dict, font_size):
            t = _clean(text)
            if not t:
                return
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            frags.append((y, y, x, t, font_size or 0))
            piece_stats[0] += 1
            piece_stats[1] += len(t)
        try:
            p.extract_text(visitor_text=visit)
        except Exception:
            pass
        pages.append(_cluster(frags))
    LAST_READER["pieces"] = tuple(piece_stats)
    return pages


LAST_READER = {"used": None, "rows": {}, "pieces": (0, 0)}


def read_rows(path, password="", force=None):
    """Returns a list of pages; each page is a list of text rows, top to bottom.
    Tries pdfminer and pypdf and keeps the one that found more rows (force = 'pdfminer' or 'pypdf')."""
    try:
        from pdfminer.pdfdocument import PDFPasswordIncorrect
    except ImportError:
        raise NeedsPackageError("pdfminer.six")
    results = {}
    errors = []
    for name, fn in (("pdfminer", _read_pdfminer), ("pypdf", _read_pypdf)):
        if force and force != name:
            continue
        try:
            results[name] = fn(path, password)
        except (PDFPasswordIncorrect, PasswordError):
            raise PasswordError("password did not open the file")
        except Exception as e:
            if "cryptography" in str(e).lower():
                raise NeedsPackageError("cryptography")
            errors.append(f"{name}: {type(e).__name__}")
    if not results:
        raise RuntimeError("no reader could open the file: " + "; ".join(errors))
    counts = {k: sum(len(p) for p in v) for k, v in results.items()}
    best = max(counts, key=counts.get)
    LAST_READER["used"], LAST_READER["rows"] = best, counts
    return results[best]


# ----------------------------------------------------------------------------- parsing
TAIL6 = re.compile(rf"({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$")
BAL = r"(?:\d[\d,]*\.\d+|--)"
DEMAT_TAIL = re.compile(rf"({BAL}(?:\s+{BAL}){{4}})\s+(\d[\d,]*\.\d+)\s+(\d[\d,]*\.\d+)\s*$")
TAIL7 = re.compile(rf"(?<![\w/.-])({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$")


def parse(pages):
    out = {
        "period": None, "months": [], "asset_split": [],
        "mf_holdings": [], "mf_total": None, "mf_totals": [], "tables": 0,
        "mf_txn": {}, "demat": [], "demat_total": None,
        "issues": [], "unplaced": {"mf_holdings": [], "demat": [], "mf_txn": []},
        "rows_seen": sum(len(p) for p in pages),
    }
    sec = None
    pend_isins, pend_names = [], []           # for holdings tables: ISIN or name rows waiting for their numbers
    cur = None                                 # current scheme (ISIN) in the transaction section
    pend_tx = None
    pre_rows = []                              # rows before an "ISIN :" line: scheme name candidates
    last_isin, last_name = None, ""
    period_from = None
    partial, fix_idx = None, None             # ISIN split over two rows in the folio table
    month_rows_done = False
    in_asset = False

    for pi, page in enumerate(pages, 1):
        for R in page:
            # ---- period
            if pi <= 2 and not out["period"]:
                m = re.search(r"PERIOD FROM\s+(\d{2}-\d{2}-\d{4})(?:\s+TO\s+(\d{2}-\d{2}-\d{4}))?", R, re.I)
                if m:
                    period_from = m.group(1)
                    if m.group(2):
                        out["period"] = (period_from, m.group(2))
                m2 = re.match(r"^TO\s+(\d{2}-\d{2}-\d{4})", R, re.I)
                if m2 and period_from and not out["period"]:
                    out["period"] = (period_from, m2.group(1))

            # ---- month table and asset split
            mm = re.match(rf"^({'|'.join(MONTHS)})\s+(\d{{4}})\s+({NUM})(?:\s+({NUM})\s+({NUM}))?$", R)
            if mm and len(out["months"]) < 12:
                out["months"].append({"month": f"{mm.group(1)} {mm.group(2)}", "value": num(mm.group(3)),
                                      "change": num(mm.group(4)) if mm.group(4) else None})
                if len(out["months"]) == 12:
                    month_rows_done, in_asset = True, True
                continue
            if in_asset:
                if R.startswith("Total"):
                    in_asset = False
                else:
                    ma = re.match(r"^([A-Za-z][A-Za-z ./&()-]*?)\s+(\d[\d,]*\.\d{2})\s+(\d+\.\d{2})$", R)
                    if ma:
                        out["asset_split"].append({"class": ma.group(1), "value": num(ma.group(2))})
                        continue

            # ---- section switches
            if re.match(r"^Scheme Name\b.*Folio No", R):
                sec, pend_isins, pend_names = "mfh", [], []
                partial, fix_idx = None, None
                if out["tables"] == 0 or len(out["mf_totals"]) >= out["tables"]:     # the header repeats on every page; a new table starts after a Grand Total
                    out["tables"] += 1
                continue
            if re.search(r"Grand Total", R) and sec == "mfh":
                n = re.findall(NUM, R)
                if len(n) >= 2:
                    out["mf_totals"].append({"cost": num(n[-2]), "value": num(n[-1]), "table": out["tables"]})
                    out["mf_total"] = {"cost": sum((x["cost"] for x in out["mf_totals"]), D(0)),
                                       "value": sum((x["value"] for x in out["mf_totals"]), D(0))}
                sec = None
                continue
            if "Market Price" in R and out["demat_total"] is None:
                sec, pend_isins = "dem", []
                continue
            mp = re.search(r"Portfolio Value\W*(\d[\d,]*\.\d+)\s+as on\s+(\S+)", R)
            if mp and sec == "dem":
                out["demat_total"] = {"value": num(mp.group(1)), "as_on": mp.group(2)}
                out["demat_isins_left"] = len(pend_isins)
                sec = None
                continue

            # ---- mutual fund transactions of the period
            mi = re.search(r"ISIN\s*:\s*(IN[EF][0-9A-Z]{9}|IN[0-9][0-9A-Z]{9})", R)
            if mi:
                last_isin, last_name = mi.group(1), " ".join(pre_rows[-4:]).strip()
                pre_rows = []
                if out["demat_total"] is not None or sec == "mftx":      # account-detail pages also carry "ISIN :" rows
                    sec, pend_tx = "mftx", None
                    cur = _new_block(out["mf_txn"], last_isin, last_name)
                continue
            if sec != "mftx" and last_isin and re.match(r"^Opening Balance\b", R):
                sec, pend_tx = "mftx", None
                cur = _new_block(out["mf_txn"], last_isin, last_name)
            if sec == "mftx":
                mo = re.match(rf"^Opening Balance\s+({NUM})", R)
                mc = re.match(rf"^Closing Balance\s+({NUM})", R)
                if mo and cur is not None:
                    cur["opening"] = num(mo.group(1)); continue
                if mc and cur is not None:
                    cur["closing"] = num(mc.group(1)); pend_tx = None; continue
                md = DATE_DMY.match(R)
                if md and cur is not None:
                    pend_tx = {"date": md.group(0), "desc": R[md.end():].strip(), "amount": None, "nav": None, "units": None}
                    cur["txns"].append(pend_tx)
                    _fill_tx(pend_tx, R[md.end():])
                    continue
                if re.match(r"^(STT|Page)\b", R):
                    continue
                if pend_tx is not None and pend_tx["units"] is None:
                    if not _fill_tx(pend_tx, R):
                        pend_tx["desc"] = (pend_tx["desc"] + " " + R).strip()
                    continue
                pre_rows.append(R)
                pre_rows = pre_rows[-8:]
                continue
            else:
                pre_rows.append(R)
                pre_rows = pre_rows[-8:]

            # ---- mutual fund holdings table
            if sec == "mfh":
                t = TAIL6.search(R)
                if t and re.search(r"\d", R[:t.start()]):
                    prefix = R[:t.start()].strip()
                    toks = prefix.split()
                    folio_tok = toks[-1] if toks else ""
                    isin = None
                    mi2 = ISIN_RE.search(prefix)
                    if mi2:
                        isin = mi2.group(0)
                        if folio_tok.startswith(isin):          # ISIN and folio written together
                            folio_tok = folio_tok[len(isin):]
                    elif pend_isins:
                        isin = pend_isins.pop(0)
                    name_part = prefix[:mi2.start()].strip() if mi2 else " ".join(toks[:-1])
                    partial_saved = partial
                    if isin is None and partial:
                        fix_idx = len(out["mf_holdings"])
                    else:
                        fix_idx = None
                    partial = None
                    out["mf_holdings"].append({
                        "isin": isin, "folio": folio_tok, "name": " ".join(pend_names + [name_part]).strip(),
                        "table": out["tables"], "_partial": partial_saved, "units": num(t.group(1)), "nav": num(t.group(2)), "cost": num(t.group(3)),
                        "value": num(t.group(4)), "gain": num(t.group(5)), "gain_pct": num(t.group(6)),
                    })
                    pend_names = []
                else:
                    mi3 = ISIN_RE.search(R)
                    last_tok = R.split()[-1] if R.split() else ""
                    if fix_idx is not None and re.fullmatch(r"[A-Z0-9]{1,9}", last_tok) and re.search(r"\d", last_tok) \
                            and len(out["mf_holdings"][fix_idx]["_partial"]) + len(last_tok) == 12:
                        out["mf_holdings"][fix_idx]["isin"] = out["mf_holdings"][fix_idx].pop("_partial") + last_tok
                        fix_idx = None
                        if len(R.split()) == 1:
                            continue
                    elif re.fullmatch(r"IN[A-Z0-9]{2,9}", last_tok) and re.search(r"\d", last_tok):
                        partial = last_tok
                        if len(R.split()) == 1:
                            continue
                    if mi3:
                        pend_isins.append(mi3.group(0))
                    pend_names.append(R)
                    pend_names = pend_names[-5:]
                    if not re.match(r"^(Closing|Cumulative|Amount|Invested|Valuation|NAV|\(Units\)|Xxx|Unrealised)", R):
                        out["unplaced"]["mf_holdings"].append(R)
                continue

            # ---- demat holdings
            if sec == "dem":
                t = DEMAT_TAIL.search(R)
                mi4 = ISIN_RE.search(R)
                if t:
                    prefix = R[:t.start()].strip()
                    isin = None
                    if mi4 and mi4.start() < t.start():
                        isin = mi4.group(0)
                    elif pend_isins:
                        isin = pend_isins.pop(0)
                    price, value = num(t.group(2)), num(t.group(3))
                    bals = [num(x) for x in t.group(1).split() if x != "--"]
                    qty = next((q for q in bals if abs(q * price - value) <= max(D("1"), value * D("0.005"))),
                               bals[0] if bals else D(0))
                    out["demat"].append({"isin": isin, "name": prefix, "qty": qty, "price": price, "value": value})
                else:
                    if mi4:
                        pend_isins.append(mi4.group(0))
                continue
    return out


def _new_block(store, isin, name):
    """One block per 'ISIN :' row. The same scheme in two folios gives two blocks: ISIN, ISIN#2 ..."""
    key, n = isin, 1
    while key in store:
        n += 1
        key = f"{isin}#{n}"
    store[key] = {"name": name, "opening": None, "closing": None, "txns": []}
    return store[key]


def _fill_tx(tx, text):
    """Last 7 numbers of a transaction row: amount, price, price, units, then three more."""
    m = TAIL7.search(text)
    if m:
        tx["amount"], tx["nav"], tx["units"] = num(m.group(1)), num(m.group(2)), num(m.group(4))
        return True
    return False


# ----------------------------------------------------------------------------- checks
def run_checks(d):
    """Returns a list of (name, status, detail). Status: PASS, FAIL or INFO."""
    res = []
    q = D("0.01")

    h = d["mf_holdings"]
    t = d["mf_total"]
    if t is None:
        res.append(("MF holdings total found in statement", "FAIL", "Grand Total row not found"))
    else:
        parts, ok_all = [], True
        for gt in d["mf_totals"]:
            rows = [x for x in h if x.get("table") == gt["table"]]
            sc, sv = sum((x["cost"] for x in rows), D(0)), sum((x["value"] for x in rows), D(0))
            ok = abs(sc - gt["cost"]) <= 1 and abs(sv - gt["value"]) <= 1
            ok_all &= ok
            parts.append(f"table {gt['table']}: {len(rows)} rows, difference cost {sc - gt['cost']:.2f}, value {sv - gt['value']:.2f}")
        ok_all &= len(d["mf_totals"]) == d["tables"] and sum(1 for x in h) == sum(1 for x in h if x.get("table") in {g["table"] for g in d["mf_totals"]})
        res.append(("Each folio table: sum of rows equals its Grand Total (cost and value)", "PASS" if ok_all else "FAIL", "; ".join(parts)))
    bad = [x for x in h if abs(x["units"] * x["nav"] - x["value"]) > max(D(1), x["value"] * D("0.005"))]
    res.append(("Folio rows: units x NAV = value (within 0.5%)", "PASS" if not bad else "FAIL",
                f"{len(h) - len(bad)} of {len(h)} rows agree"))
    noisin = [x for x in h if not x["isin"]]
    res.append(("Folio rows with ISIN found", "PASS" if not noisin else "FAIL", f"{len(h) - len(noisin)} of {len(h)}"))

    tx = d["mf_txn"]
    bad_t, incomplete = [], 0
    pos_bad = []
    for pos, (isin, b) in enumerate(tx.items(), 1):
        if b["opening"] is None or b["closing"] is None:
            incomplete += 1
            continue
        if any(x["units"] is None for x in b["txns"]):
            bad_t.append(isin); pos_bad.append((pos, "unit not read"))
            continue
        gap = b["opening"] + sum((x["units"] for x in b["txns"]), D(0)) - b["closing"]
        if abs(gap) > D("0.001"):
            bad_t.append(isin); pos_bad.append((pos, f"gap {gap}, {len(b['txns'])} txn"))
    res.append(("Transactions: opening units + transactions = closing units, each block",
                "PASS" if not bad_t and not incomplete else "FAIL",
                f"{len(tx) - len(bad_t) - incomplete} of {len(tx)} blocks agree; {incomplete} without opening or closing"
                + (f"; failing blocks (position, gap) {pos_bad[:15]}" if pos_bad else "")))

    hold_units, hold_n, blk_units, blk_n = {}, {}, {}, {}
    for x in h:
        if x["isin"]:
            hold_units[x["isin"]] = hold_units.get(x["isin"], D(0)) + x["units"]
            hold_n[x["isin"]] = hold_n.get(x["isin"], 0) + 1
    for k, b in tx.items():
        base = k.split("#")[0]
        if b["closing"] is not None:
            blk_units[base] = blk_units.get(base, D(0)) + b["closing"]
            blk_n[base] = blk_n.get(base, 0) + 1
    comparable = [i for i in blk_units if i in hold_units and blk_n[i] == hold_n[i]]
    diff = [i for i in comparable if abs(hold_units[i] - blk_units[i]) > D("0.001")]
    skipped = [i for i in blk_units if i in hold_units and blk_n[i] != hold_n[i]]
    res.append(("Closing units in transactions = units in holdings table", "PASS" if not diff else "FAIL",
                f"{len(comparable) - len(diff)} of {len(comparable)} schemes agree; {len(skipped)} not compared (folio with no transaction in the period)"))

    dm = d["demat"]
    if d["demat_total"] is None:
        res.append(("Demat Portfolio Value found", "FAIL", "row not found"))
    else:
        sv = sum((x["value"] for x in dm), D(0))
        res.append(("Sum of demat rows equals statement Portfolio Value",
                    "PASS" if abs(sv - d["demat_total"]["value"]) <= 1 else "FAIL",
                    f"difference {sv - d['demat_total']['value']:.2f}"))
    baddm = [x for x in dm if x["qty"] is None or abs(x["qty"] * x["price"] - x["value"]) > max(D(1), x["value"] * D("0.005"))]
    res.append(("Demat rows: quantity x price = value (within 0.5%)", "PASS" if not baddm else "FAIL",
                f"{len(dm) - len(baddm)} of {len(dm)} rows agree"))

    if d["months"] and t and d["demat_total"]:  # noqa
        total = t["value"] + d["demat_total"]["value"]
        last = d["months"][-1]["value"]
        res.append(("Latest month value (12-month table) vs MF + demat totals", "INFO",
                    f"difference {total - last:.2f} (joint-holder folios or other holdings can explain a gap)"))
    nd = [x for x in dm if not x["isin"]]
    res.append(("Demat rows with ISIN found", "PASS" if not nd and not d.get("demat_isins_left") else "FAIL",
                f"{len(dm) - len(nd)} of {len(dm)} rows; {d.get('demat_isins_left', 0)} ISIN rows left unmatched"))
    res.append(("Month table rows found", "PASS" if len(d["months"]) == 12 else "FAIL", f"{len(d['months'])} of 12"))
    return res
