"""Module E, part 2 - forensic tests that need more than the general ledger:
FA-11 signature integrity (mandate, limits, copy-paste, resemblance to specimen)
FA-12 bank statement: diversion of funds, payments outside the vendor master, insider accounts, unrecorded payments
FA-13 financial statement manipulation indicators (over/understatement, Beneish M-score, cut-off, FS vs GL)
FA-14 inventory: roll-forward, book vs count, dispatched-not-billed, received-not-invoiced.
All tests are indicators for an examiner to follow up; none proves fraud or forgery."""
from __future__ import annotations
import difflib
import re
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from .rules_fa import _d, _ex, _master, _n, _norm, _rows, map_columns_generic, read_table
from .rules_fs import NotRun


def _table(path, spec):
    headers, rows, first = read_table(path)
    m = map_columns_generic(headers, spec)
    out = []
    for i, r in enumerate(rows):
        if not any(x not in (None, "") for x in r):
            continue
        out.append({"row": first + i, **{k: (r[ix] if ix < len(r) else None) for k, ix in m.items()}})
    return out, m, headers


def _close(a, b, r=0.86):
    a, b = _norm(a), _norm(b)
    return bool(a) and bool(b) and (a == b or difflib.SequenceMatcher(None, a, b).ratio() >= r)


def _aed(v):
    return f"{v:,.0f}"


# ===================================================================== FA-11 signatures
MANDATE = {"name": ["name", "signatory"], "role": ["designation", "role", "title"], "single": ["single", "limit"], "joint": ["joint"],
           "specimen": ["specimen", "image"], "from": ["valid from", "from", "effective"], "to": ["valid to", "valid until", "to", "expiry", "ceased"]}
SIGREG = {"doc": ["document", "doc", "reference", "voucher", "cheque"], "date": ["date"], "amount": ["amount", "value"],
          "who": ["claimed signatory", "signatory", "signed by"], "second": ["second", "joint", "co-sign"], "image": ["image", "signature file", "file"]}


def _ink(path, size=(160, 64)):
    """Signature image -> blurred ink map of fixed size, or None when no ink is found."""
    import numpy as np
    from PIL import Image, ImageFilter
    if Path(str(path)).suffix.lower() == ".pdf":  # scanned signature saved as PDF: use page 1
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            im = pdf.pages[0].to_image(resolution=150).original.copy()
    else:
        im = Image.open(str(path))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        im = bg
    a = np.asarray(im.convert("L"), dtype=float)
    ink = a < 140
    if ink.sum() < 30:
        return None
    ys, xs = np.where(ink)
    crop = Image.fromarray((ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1] * 255).astype("uint8"))
    crop = crop.resize(size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(2.5))
    return np.asarray(crop, dtype=float)


def _find(folder, name):
    """File in folder by name, ignoring case (uploads may change the case of extensions)."""
    p = folder / str(name)
    if p.exists():
        return p
    low = str(name).strip().lower()
    return next((q for q in folder.glob("*") if q.name.lower() == low), None)


def _corr(a, b):
    import numpy as np
    a, b = a - a.mean(), b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d else 0.0


def fa11_signatures(c):
    folder, mpath = c.x.get("signatures"), c.x.get("mandate")
    if not folder and not mpath:
        raise NotRun("Signature register / folder and authorised-signatory mandate not supplied")
    P, out = c.p, []
    mand = []
    if mpath:
        mand, _, _ = _table(mpath, MANDATE)
    reg = []
    folder = Path(folder) if folder else None
    if folder:
        tabs = [p for p in sorted(folder.glob("*")) if p.suffix.lower() in (".xlsx", ".xls", ".csv")]
        regfile = next((p for p in tabs if "regist" in p.name.lower()), None) or (tabs[0] if len(tabs) == 1 else None)
        if not regfile:
            raise NotRun("No signature register found: put one Excel/CSV register (ideally named *register*) with the signature images")
        reg, _, _ = _table(regfile, SIGREG)
    spec = {}
    for m in mand:
        if m.get("specimen") and folder and _find(folder, m["specimen"]):
            spec[_norm(m["name"])] = _find(folder, m["specimen"])
    # a. authority
    for r in reg:
        who = r.get("who")
        mm = next((m for m in mand if _close(m.get("name"), who)), None) if mand else None
        dt = _d(r.get("date"))
        if mand and not mm:
            out.append(_ex("FA-11", "Document signed by a person who is not an authorised signatory", "High", f"{r.get('doc')}: '{who}' is not on the mandate (register row {r['row']})", "Signature register", "authorised signatory", str(who)))
            continue
        if mm and dt:
            vf, vt = _d(mm.get("from")), _d(mm.get("to"))
            if (vf and dt < vf) or (vt and dt > vt):
                span = f"{vf:%d-%b-%Y}" if vf else "start not stated"
                span += f" to {vt:%d-%b-%Y}" if vt else " to open"
                out.append(_ex("FA-11", "Signatory's authority had not started or had ended on the document date", "High",
                               f"{r.get('doc')} dated {dt:%d-%b-%Y} signed by {who}; authority valid {span}", "Signature register", "within validity", f"{dt:%d-%b-%Y}"))
        if mm and _n(mm.get("single")) and _n(r.get("amount")) > _n(mm.get("single")) and not r.get("second"):
            out.append(_ex("FA-11", "Amount above the signatory's single-signature limit with no second signature", "High",
                           f"{r.get('doc')}: AED {_aed(_n(r['amount']))} signed by {who} alone; single limit AED {_aed(_n(mm['single']))}", "Signature register", f"<= {_aed(_n(mm['single']))} or joint", _aed(_n(r["amount"]))))
    # b. images
    ink = {}
    for r in reg:
        f = r.get("image")
        if f and folder and _find(folder, f):
            try:
                ink[r["row"]] = _ink(_find(folder, f))
            except Exception:  # unreadable or corrupt image: leave unscreened rather than abort
                ink[r["row"]] = None
    byp = defaultdict(list)
    for r in reg:
        if ink.get(r["row"]) is not None:
            byp[_norm(r.get("who"))].append(r)
    sim_min, same_min = P["sig_similarity_min"], P["sig_identical_min"]
    for who, lst in byp.items():
        sp = _ink(spec[who]) if who in spec else None
        pairs = []
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                if _corr(ink[lst[i]["row"]], ink[lst[j]["row"]]) >= same_min:
                    pairs.append((lst[i], lst[j]))
        if sp is not None:
            for r in lst:
                if _corr(ink[r["row"]], sp) >= same_min:
                    pairs.append((r, {"doc": "the specimen card", "row": 0}))
        if pairs:
            det = "; ".join(f"{a.get('doc')} = {b.get('doc')}" for a, b in pairs[:4])
            out.append(_ex("FA-11", "Identical signature image on different documents (copy-pasted or stamped, not hand-signed)", "High",
                           f"{lst[0].get('who')}: {len(pairs)} pair(s): {det}. A hand-written signature is never pixel-identical twice.", "Signature images", "natural variation", f"{len(pairs)} identical pair(s)"))
        if sp is not None:
            for r in lst:
                s = _corr(ink[r["row"]], sp)
                if s < sim_min:
                    out.append(_ex("FA-11", "Signature does not resemble the specimen on the mandate: possible forgery (examiner to confirm)", "High",
                                   f"{r.get('doc')} dated {(_d(r.get('date')) or _d('2000-01-01')):%d-%b-%Y}, AED {_aed(_n(r.get('amount')))}: similarity {s:.2f} to the specimen of {r.get('who')} (threshold {sim_min:.2f}). Screening only: a handwriting examiner must confirm.",
                                   "Signature images", f">= {sim_min:.2f}", f"{s:.2f}"))
    if not reg:
        raise NotRun("The signature register is empty")
    return out


# ===================================================================== FA-12 bank
BANK = {"date": ["value date", "txn date", "transaction date", "date"], "desc": ["narration", "description", "details", "particulars"],
        "party": ["beneficiary name", "beneficiary", "payee", "counterparty", "name"], "iban": ["beneficiary iban", "beneficiary account", "iban", "account"],
        "debit": ["debit", "withdrawal"], "credit": ["credit", "deposit"], "bal": ["balance"], "signer": ["signed by", "authorised by", "approved by", "initiated by"]}


def _bank(path):
    rows, m, h = _table(path, BANK)
    if not {"date", "debit"} <= set(m):
        raise ValueError("Bank statement needs Date and Debit columns. Found: " + ", ".join(h))
    out = []
    for r in rows:
        d = _d(r.get("date"))
        if d:
            out.append({"row": r["row"], "date": d, "desc": str(r.get("desc") or ""), "party": str(r.get("party") or "").strip(), "iban": _norm(r.get("iban")),
                        "debit": _n(r.get("debit")), "credit": _n(r.get("credit")), "bal": r.get("bal"), "signer": str(r.get("signer") or "").strip()})
    return out


def fa12_bank(c):
    if not c.x.get("bank"):
        raise NotRun("Bank statement not supplied")
    P, out = c.p, []
    B = _bank(c.x["bank"])
    V = _master(c.vendors) if c.vendors else []
    E = _master(c.employees) if c.employees else []
    ex = re.compile("|".join(re.escape(k) for k in P["bank_exempt_keywords"]), re.I)
    mat = P["bank_material"]
    pays = [b for b in B if b["debit"] > 0 and not ex.search(b["desc"] + " " + b["party"])]
    vib = {_norm(v["bank"]): v for v in V if _norm(v["bank"])}
    eib = {_norm(e["bank"]): e for e in E if _norm(e["bank"])}
    # a/f. outside the vendor master, or vendor paid to a different account than the master holds
    if V:
        unk, diff = defaultdict(list), []
        for b in pays:
            if not b["iban"] or b["iban"] in vib or b["iban"] in eib:
                continue
            v = next((v for v in V if _close(v["name"], b["party"])), None)
            (diff.append((b, v)) if v else unk[b["iban"]].append(b))
        for b, v in diff:
            out.append(_ex("FA-12", "Payment to a vendor's name but into an account that is not the one in the vendor master (bank-detail diversion)", "High",
                           f"{b['date']:%d-%b-%Y} AED {_aed(b['debit'])} to '{b['party']}', account {b['iban'][-8:]} vs master {_norm(v['bank'])[-8:]} (statement row {b['row']})", "Bank statement", "master IBAN", b["iban"][-8:]))
        for k, lst in unk.items():
            tot = sum(x["debit"] for x in lst)
            if tot >= mat:
                out.append(_ex("FA-12", "Payments to an account that is in neither the vendor master nor the employee master", "High",
                               f"{lst[0]['party'] or 'unnamed'} (account ...{k[-8:]}): {len(lst)} payment(s), AED {_aed(tot)}; statement rows {_rows(lst)}", "Bank statement", "approved beneficiary", f"AED {_aed(tot)}"))
    # b. insider accounts
    for k, lst in {k: [b for b in pays if b["iban"] == k] for k in {b["iban"] for b in pays if b["iban"]}}.items():
        if k in eib:
            out.append(_ex("FA-12", "Payments into an employee's bank account recorded as other payments (not payroll)", "High",
                           f"{eib[k]['name']} (employee master row {eib[k]['row']}): {len(lst)} payment(s), AED {_aed(sum(x['debit'] for x in lst))}; rows {_rows(lst)}", "Bank vs employee master", "payroll only", "other payments"))
    for name in c.related:
        hit = [b for b in pays if _close(name, b["party"], 0.8) or _norm(name) in _norm(b["desc"])]
        if hit:
            out.append(_ex("FA-12", f"Payments to a person of interest: {name}", "High", f"{len(hit)} payment(s), AED {_aed(sum(x['debit'] for x in hit))}; rows {_rows(hit)}", "Bank statement", "none / disclosed", f"{len(hit)} payment(s)"))
    # c. sweep to one account
    for b in B:
        pre = _n(b["bal"]) + b["debit"] - b["credit"] if b["bal"] not in (None, "") else None
        if pre and pre > mat and b["debit"] >= pre * P["bank_sweep_share"] and (pre - b["debit"]) <= pre * P["bank_sweep_left_share"] and b["iban"] and b["iban"] not in vib:
            out.append(_ex("FA-12", "Account swept: a single transfer took most of the balance to an unapproved account", "High",
                           f"{b['date']:%d-%b-%Y} AED {_aed(b['debit'])} of AED {_aed(pre)} to '{b['party'] or 'unnamed'}' (...{b['iban'][-8:]}); balance left AED {_aed(pre - b['debit'])}; row {b['row']}", "Bank statement", f"< {P['bank_sweep_share']:.0%} of balance", f"{b['debit'] / pre:.0%}"))
    # d. pass-through (money in, same money out to a third account within days)
    for cr in [b for b in B if b["credit"] >= mat]:
        for db in B:
            if db["debit"] > 0 and 0 <= (db["date"] - cr["date"]).days <= P["bank_passthrough_days"] and db["debit"] >= cr["credit"] * P["bank_passthrough_share"] \
                    and db["debit"] <= cr["credit"] * 1.02 and db["iban"] and db["iban"] not in vib:
                out.append(_ex("FA-12", "Pass-through: a receipt was paid out almost in full to an unapproved account within days", "Medium",
                               f"Credit AED {_aed(cr['credit'])} on {cr['date']:%d-%b-%Y} (row {cr['row']}) -> debit AED {_aed(db['debit'])} on {db['date']:%d-%b-%Y} to '{db['party']}' (row {db['row']})", "Bank statement", "no pass-through", "same-week out"))
                break
    # g. payments not in the GL
    if c.gl:
        glb = [(r["date"], r["credit"]) for r in c.gl.rows if re.search(r"bank|cash at bank", r["account"], re.I) and r["credit"] > 0]
        used = set()
        miss = []
        for b in sorted(pays, key=lambda x: -x["debit"]):
            k = next((i for i, (d, a) in enumerate(glb) if i not in used and abs(a - b["debit"]) < 1 and abs((d - b["date"]).days) <= 7), None)
            if k is None:
                miss.append(b)
            else:
                used.add(k)
        big = [b for b in miss if b["debit"] >= mat]
        if big:
            out.append(_ex("FA-12", "Bank payments with no matching credit to the bank account in the GL (unrecorded or hidden)", "High",
                           f"{len(big)} payment(s), AED {_aed(sum(x['debit'] for x in big))}, e.g. {big[0]['date']:%d-%b-%Y} AED {_aed(big[0]['debit'])} to '{big[0]['party']}'; statement rows {_rows(big)}", "Bank statement vs GL", "all payments recorded", f"{len(big)} unmatched"))
    # h. cash
    cash = [b for b in B if b["debit"] >= mat and re.search(r"cash withdrawal|atm|self cheque|bearer", b["desc"], re.I)]
    if cash:
        out.append(_ex("FA-12", "Large cash or bearer withdrawals", "Medium", f"{len(cash)} item(s), AED {_aed(sum(x['debit'] for x in cash))}; rows {_rows(cash)}", "Bank statement"))
    return out[:20]


# ===================================================================== FA-13 financial statements
FSK = [("rev", r"^(total )?(revenue|sales|turnover)"), ("cogs", r"cost of (sales|goods|revenue)|^cogs"), ("sga", r"selling|general and admin|administrative|operating expenses|sg&a"),
       ("dep", r"depreciation"), ("cfo", r"operating activities|cash (flow )?from operat|operating cash"), ("ni", r"net (profit|income)|profit (for|after)|profit/\(loss\)"),
       ("rec", r"receivable|debtors"), ("inv", r"inventor|^stock"), ("pay", r"payable|creditors"), ("ca", r"total current assets"), ("cl", r"total current liabilities"),
       ("ta", r"^total assets"), ("ppe", r"property|plant|fixed assets|ppe"), ("ltd", r"long[- ]term (debt|borrowing|loan)|non-current liabilities|term loan"), ("cash", r"cash and (bank|cash)|^cash")]
FSLBL = {"rev": "Revenue", "cogs": "Cost of sales", "inv": "Inventory", "rec": "Receivables", "pay": "Payables", "ni": "Net profit", "cfo": "Operating cash flow", "ta": "Total assets"}


def _fsdata(path):
    headers, rows, first = read_table(path)
    out = {}
    for r in rows:
        if not r or r[0] in (None, ""):
            continue
        nums = [x for x in r[1:] if isinstance(x, (int, float)) and not isinstance(x, bool)]
        if len(nums) < 2:
            continue
        lab = str(r[0]).strip().lower()
        for k, rx in FSK:
            if k not in out and re.search(rx, lab):
                out[k] = (float(nums[0]), float(nums[1]))
                break
    return out


def fa13_fs(c):
    if not c.x.get("fs_data"):
        raise NotRun("Financial statement data (current and prior year) not supplied")
    P, out = c.p, []
    d = _fsdata(c.x["fs_data"])
    if len(d) < 4 or "rev" not in d:
        raise NotRun(f"Financial statement data has too few recognisable lines (found: {', '.join(d) or 'none'})")
    g = lambda k: d.get(k)
    rev, cogs = g("rev"), g("cogs")
    pc = lambda t: (t[0] / t[1] - 1) if t and t[1] else None
    if g("rec") and rev[0] and rev[1]:
        rg, cg = pc(rev), pc(g("rec"))
        dso = [g("rec")[i] / rev[i] * 365 for i in (0, 1)]
        if cg is not None and rg is not None and cg - rg > P["fs_gap_pp"]:
            out.append(_ex("FA-13", "Receivables grew much faster than revenue: possible overstated revenue (fictitious or premature sales)", "High",
                           f"Revenue {rg:+.0%}, receivables {cg:+.0%}; days sales outstanding {dso[1]:.0f} -> {dso[0]:.0f}", "Financial statements", f"gap <= {P['fs_gap_pp']:.0%}", f"{cg - rg:+.0%}"))
    if cogs and rev[0] and rev[1]:
        gm = [1 - cogs[i] / rev[i] for i in (0, 1)]
        if abs(gm[0] - gm[1]) > P["fs_margin_pp"]:
            out.append(_ex("FA-13", "Gross margin moved sharply without a commercial reason" + (": revenue overstated or cost of sales understated" if gm[0] > gm[1] else ": possible cost overstatement / revenue held back"),
                           "Medium" if gm[0] < gm[1] else "High", f"Gross margin {gm[1]:.1%} -> {gm[0]:.1%}", "Financial statements", f"change <= {P['fs_margin_pp']:.0%} pts", f"{(gm[0] - gm[1]) * 100:+.1f} pts"))
    if g("ni") and g("cfo") and g("ta") and g("ta")[0]:
        acc = (g("ni")[0] - g("cfo")[0]) / g("ta")[0]
        if acc > P["fs_accruals"]:
            out.append(_ex("FA-13", "Profit is not backed by operating cash flow (high accruals): possible overstated profit", "High",
                           f"Net profit {_aed(g('ni')[0])}, operating cash flow {_aed(g('cfo')[0])}; accruals {acc:.0%} of total assets", "Financial statements", f"<= {P['fs_accruals']:.0%}", f"{acc:.0%}"))
    if g("inv") and cogs and cogs[0] and cogs[1]:
        di = [g("inv")[i] / cogs[i] * 365 for i in (0, 1)]
        if di[0] - di[1] > P["fs_dso_days"]:
            out.append(_ex("FA-13", "Inventory days rose sharply: possible overstated closing stock (obsolete, fictitious or not counted)", "High",
                           f"Inventory {_aed(g('inv')[0])} vs {_aed(g('inv')[1])}; days {di[1]:.0f} -> {di[0]:.0f}", "Financial statements", f"rise <= {P['fs_dso_days']} days", f"{di[0] - di[1]:+.0f} days"))
    if g("pay") and cogs and cogs[0] and cogs[1]:
        dp = [g("pay")[i] / cogs[i] * 365 for i in (0, 1)]
        if dp[1] - dp[0] > P["fs_dso_days"]:
            out.append(_ex("FA-13", "Payable days fell sharply while costs did not: possible unrecorded liabilities / understated expenses", "Medium",
                           f"Payables {_aed(g('pay')[0])} vs {_aed(g('pay')[1])}; days {dp[1]:.0f} -> {dp[0]:.0f}", "Financial statements", f"fall <= {P['fs_dso_days']} days", f"{dp[0] - dp[1]:+.0f} days"))
    if g("sga") and rev[0] and rev[1]:
        s = [g("sga")[i] / rev[i] for i in (0, 1)]
        if s[1] - s[0] > P["fs_sga_pp"]:
            out.append(_ex("FA-13", "Operating expenses fell as a share of revenue: possible understated expenses (costs deferred or capitalised)", "Medium",
                           f"Opex / revenue {s[1]:.1%} -> {s[0]:.1%}", "Financial statements", f"fall <= {P['fs_sga_pp']:.0%} pts", f"{(s[0] - s[1]) * 100:+.1f} pts"))
    need = ("rev", "cogs", "rec", "ca", "ppe", "ta", "dep", "sga", "ni", "cfo", "cl", "ltd")
    if all(k in d for k in need):
        idx = lambda f: f(0) / f(1) if f(1) else 1
        dsri = idx(lambda i: g("rec")[i] / rev[i])
        gmi = (1 - cogs[1] / rev[1]) / (1 - cogs[0] / rev[0])
        aqi = idx(lambda i: 1 - (g("ca")[i] + g("ppe")[i]) / g("ta")[i])
        sgi = rev[0] / rev[1]
        depi = idx(lambda i: g("dep")[i] / (g("dep")[i] + g("ppe")[i]))
        sgai = idx(lambda i: g("sga")[i] / rev[i])
        tata = (g("ni")[0] - g("cfo")[0]) / g("ta")[0]
        lvgi = idx(lambda i: (g("cl")[i] + g("ltd")[i]) / g("ta")[i])
        m = -4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi
        if m > P["beneish_threshold"]:
            out.append(_ex("FA-13", "Beneish M-score above the manipulation threshold", "Medium",
                           f"M = {m:.2f} (> {P['beneish_threshold']}); DSRI {dsri:.2f}, GMI {gmi:.2f}, AQI {aqi:.2f}, SGI {sgi:.2f}, DEPI {depi:.2f}, SGAI {sgai:.2f}, TATA {tata:.3f}, LVGI {lvgi:.2f}. Statistical indicator only.",
                           "Financial statements", f"<= {P['beneish_threshold']}", f"{m:.2f}"))
    if c.gl:
        glrev = sum(r["credit"] - r["debit"] for r in c.gl.rows if re.search(r"revenue|sales", r["account"], re.I))
        if glrev and rev[0] and abs(glrev - rev[0]) / rev[0] > P["fs_gl_tol"]:
            out.append(_ex("FA-13", "Revenue in the financial statements does not agree to the general ledger", "High",
                           f"FS revenue {_aed(rev[0])}, GL revenue {_aed(glrev)}, difference {_aed(rev[0] - glrev)} ({(rev[0] - glrev) / rev[0]:+.1%})", "FS vs GL", f"within {P['fs_gl_tol']:.0%}", f"{(rev[0] - glrev) / rev[0]:+.1%}"))
        if c.period:
            pe = c.period[1]
            late = [r for r in c.gl.rows if re.search(r"revenue|sales", r["account"], re.I) and r["credit"] >= P["cutoff_min_amount"] and 0 <= (pe - r["date"]).days < P["cutoff_days"]]
            rev_back = [r for r in c.gl.rows if re.search(r"revenue|sales", r["account"], re.I) and r["debit"] >= P["cutoff_min_amount"] and 0 < (r["date"] - pe).days <= P["cutoff_reversal_days"]]
            if late and rev_back:
                out.append(_ex("FA-13", "Large revenue booked in the last days of the year and reversed after year-end (window dressing / cut-off)", "High",
                               f"{len(late)} credit(s) AED {_aed(sum(r['credit'] for r in late))} in the last {P['cutoff_days']} days (rows {_rows(late)}); {len(rev_back)} reversal(s) AED {_aed(sum(r['debit'] for r in rev_back))} after year-end (rows {_rows(rev_back)})",
                               "GL", "no reversal", f"{len(rev_back)} reversal(s)"))
    stock = c.x.get("stock")
    if stock and g("inv"):
        try:
            rows, m, _ = _table(stock, STOCK)
            bv = sum(_n(r.get("book")) * _n(r.get("cost")) for r in rows)
            if bv and abs(bv - g("inv")[0]) / g("inv")[0] > P["fs_gl_tol"]:
                out.append(_ex("FA-13", "Inventory in the financial statements does not agree to the stock register", "High",
                               f"FS {_aed(g('inv')[0])}, stock register {_aed(bv)}, difference {_aed(g('inv')[0] - bv)}", "FS vs stock register", f"within {P['fs_gl_tol']:.0%}", _aed(bv)))
        except Exception:
            pass
    return out


# ===================================================================== FA-14 inventory
STOCK = {"item": ["item", "sku", "product", "material"], "loc": ["location", "warehouse", "store"], "open": ["opening"], "grn": ["grn", "received", "purchases qty", "purchased"],
         "issue": ["issued", "dispatched", "delivered", "sales qty"], "adj": ["adjust"], "book": ["closing book", "book"], "count": ["physical", "count"], "cost": ["unit cost", "cost"],
         "invsold": ["invoiced sales", "sales invoiced", "billed"], "invbought": ["invoiced purchases", "purchase invoiced", "purchase invoice", "supplier invoiced"]}


def fa14_inventory(c):
    if not c.x.get("stock"):
        raise NotRun("Stock register not supplied")
    P, out = c.p, []
    rows, m, h = _table(c.x["stock"], STOCK)
    if not {"item", "book", "count"} <= set(m):
        raise ValueError("Stock register needs Item, Closing book qty and Physical count qty columns. Found: " + ", ".join(h))
    val = lambda r, k: _n(r.get(k))
    tot_book = sum(val(r, "book") * val(r, "cost") for r in rows)
    rf = [r for r in rows if {"open", "grn", "issue"} <= set(m) and abs(val(r, "open") + val(r, "grn") - val(r, "issue") + val(r, "adj") - val(r, "book")) > 0.5]
    if rf:
        out.append(_ex("FA-14", "Stock roll-forward does not agree: opening + received - issued + adjustments differs from closing book", "High",
                       "; ".join(f"{r['item']} (row {r['row']}): expected {val(r, 'open') + val(r, 'grn') - val(r, 'issue') + val(r, 'adj'):,.0f}, book {val(r, 'book'):,.0f}" for r in rf[:5]), "Stock register", "ties", f"{len(rf)} item(s)"))
    short = [(r, (val(r, "book") - val(r, "count")) * val(r, "cost")) for r in rows if val(r, "book") - val(r, "count") > 0]
    sv = sum(v for _, v in short)
    if short and sv >= P["stock_min_value"] and sv >= tot_book * P["stock_tolerance_pct"]:
        top = sorted(short, key=lambda x: -x[1])[:4]
        out.append(_ex("FA-14", "Physical stock is short of book stock: goods missing, diverted or sold without record", "High",
                       f"Shortage AED {_aed(sv)} ({sv / tot_book:.1%} of book value) across {len(short)} item(s); largest: " + "; ".join(f"{r['item']} AED {_aed(v)}" for r, v in top), "Stock register", f"< {P['stock_tolerance_pct']:.0%}", f"{sv / tot_book:.1%}"))
    surp = [(r, (val(r, "count") - val(r, "book")) * val(r, "cost")) for r in rows if val(r, "count") - val(r, "book") > 0]
    uv = sum(v for _, v in surp)
    if surp and uv >= P["stock_min_value"] and uv >= tot_book * P["stock_tolerance_pct"]:
        out.append(_ex("FA-14", "Physical stock exceeds book stock: purchases not recorded (liability and cost understated)", "Medium",
                       f"Surplus AED {_aed(uv)} across {len(surp)} item(s); " + "; ".join(f"{r['item']} AED {_aed(v)}" for r, v in sorted(surp, key=lambda x: -x[1])[:3]), "Stock register", "ties to count", f"AED {_aed(uv)}"))
    neg = [r for r in rows if val(r, "book") < 0]
    if neg:
        out.append(_ex("FA-14", "Negative book stock: sales or issues recorded with no recorded purchase", "High", "; ".join(f"{r['item']} ({val(r, 'book'):,.0f})" for r in neg[:5]), "Stock register", ">= 0", f"{len(neg)} item(s)"))
    if "invsold" in m:
        nb = [(r, (val(r, "issue") - val(r, "invsold")) * val(r, "cost")) for r in rows if val(r, "issue") - val(r, "invsold") > 0.5]
        nv = sum(v for _, v in nb)
        if nb and nv >= P["stock_min_value"]:
            out.append(_ex("FA-14", "Goods dispatched but not invoiced: stock left the warehouse with no sale recorded (diversion / unbilled sales)", "High",
                           f"AED {_aed(nv)} at cost across {len(nb)} item(s); " + "; ".join(f"{r['item']} AED {_aed(v)}" for r, v in sorted(nb, key=lambda x: -x[1])[:4]), "Stock register", "issues = invoiced sales", f"AED {_aed(nv)}"))
    if "invbought" in m:
        un = [(r, (val(r, "grn") - val(r, "invbought")) * val(r, "cost")) for r in rows if val(r, "grn") - val(r, "invbought") > 0.5]
        fi = [(r, (val(r, "invbought") - val(r, "grn")) * val(r, "cost")) for r in rows if val(r, "invbought") - val(r, "grn") > 0.5]
        if un and sum(v for _, v in un) >= P["stock_min_value"]:
            out.append(_ex("FA-14", "Goods received but supplier invoice not booked (unrecorded liability)", "Medium", f"AED {_aed(sum(v for _, v in un))} across {len(un)} item(s)", "Stock register", "GRN = invoice", f"{len(un)} item(s)"))
        if fi and sum(v for _, v in fi) >= P["stock_min_value"]:
            out.append(_ex("FA-14", "Supplier invoiced for goods never received (possible fictitious purchase)", "High",
                           f"AED {_aed(sum(v for _, v in fi))} across {len(fi)} item(s); " + "; ".join(f"{r['item']} AED {_aed(v)}" for r, v in sorted(fi, key=lambda x: -x[1])[:3]), "Stock register", "invoice <= GRN", f"{len(fi)} item(s)"))
    big_adj = [r for r in rows if "adj" in m and val(r, "adj") < 0 and abs(val(r, "adj")) >= max(val(r, "open"), 1) * P["stock_adj_pct"] and abs(val(r, "adj")) * val(r, "cost") >= P["stock_min_value"]]
    if big_adj:
        out.append(_ex("FA-14", "Large negative stock adjustments (write-offs) on single items", "Medium", "; ".join(f"{r['item']} {val(r, 'adj'):,.0f} units" for r in big_adj[:5]), "Stock register", f"< {P['stock_adj_pct']:.0%} of opening", f"{len(big_adj)} item(s)"))
    odd = re.compile("|".join(re.escape(k) for k in P["stock_odd_locations"]), re.I)
    ol = [r for r in rows if odd.search(str(r.get("loc") or "")) and val(r, "book") * val(r, "cost") >= P["stock_min_value"]]
    if ol:
        out.append(_ex("FA-14", "Stock held at unusual locations (third party, personal, unknown)", "Medium", "; ".join(f"{r['item']} at {r['loc']} AED {_aed(val(r, 'book') * val(r, 'cost'))}" for r in ol[:4]), "Stock register", "company premises", f"{len(ol)} item(s)"))
    return out


FA2_REGISTRY = {"FA-11": fa11_signatures, "FA-12": fa12_bank, "FA-13": fa13_fs, "FA-14": fa14_inventory}
