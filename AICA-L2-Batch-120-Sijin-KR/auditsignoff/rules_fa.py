"""Module E - Forensic analytics and evidence integrity: GL tests, master-data matching, document authenticity, chain of custody.
Every finding carries row/file references so the exception can be traced and defended. Analytics point to items to examine; they do not prove fraud."""
from __future__ import annotations
import csv
import hashlib
import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from .models import Finding, Result
from .rules_fs import NotRun

SYN = {
    "date": ["posting date", "transaction date", "voucher date", "doc date", "document date", "date", "entry date"],
    "created": ["created on", "created date", "entry time", "system date", "created at", "posted on", "creation date", "entered on"],
    "voucher": ["voucher no", "voucher", "journal no", "journal", "entry no", "doc no", "document no", "jv no", "jv", "reference", "ref no", "ref"],
    "account": ["account name", "gl account", "account code", "account", "ledger"],
    "desc": ["description", "narration", "memo", "particulars", "details", "text", "remarks"],
    "debit": ["debit", "dr"],
    "credit": ["credit", "cr"],
    "amount": ["amount", "value", "net amount"],
    "user": ["posted by", "created by", "entered by", "prepared by", "user id", "user"],
    "party": ["vendor", "supplier", "customer", "payee", "party", "name"],
    "approver": ["approved by", "authorised by", "authorized by", "approver"],
}


def _d(v):
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d-%b-%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(v).strip(), f)
        except (ValueError, TypeError):
            pass
    return None


def _n(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    try:
        s = str(v).replace(",", "").replace("AED", "").strip()
        neg = s.startswith("(") and s.endswith(")")
        x = float(s.strip("()"))
        return -x if neg else x
    except (ValueError, TypeError):
        return 0.0


def read_table(path):
    """-> (headers, rows list[dict-like list]) from xlsx/xls/csv."""
    from .legacy import ensure_modern
    path = ensure_modern(path)
    if Path(path).suffix.lower() == ".csv":
        with open(str(path), newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.reader(fh))
    else:
        import openpyxl
        wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
        try:
            rows = [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
        finally:
            wb.close()
    for i, r in enumerate(rows[:30]):
        if sum(1 for c in r if c not in (None, "")) >= 3 and all(not isinstance(c, (int, float)) for c in r if c not in (None, "")):
            return [str(c).strip() if c is not None else "" for c in r], rows[i + 1:], i + 2
    raise ValueError("No header row found")


def map_columns(headers):
    low = [h.lower() for h in headers]
    m = {}
    for k, names in SYN.items():
        for nm in names:
            hit = next((i for i, h in enumerate(low) if h == nm), None)
            if hit is None:
                hit = next((i for i, h in enumerate(low) if nm in h and len(nm) > 3 and i not in m.values()), None)
            if hit is not None and hit not in m.values():
                m[k] = hit
                break
    return m


class GL:
    def __init__(self, path):
        headers, rows, first = read_table(path)
        self.map = map_columns(headers)
        if "date" not in self.map or not ({"amount"} <= set(self.map) or {"debit", "credit"} <= set(self.map)):
            raise ValueError("GL needs a Date column and either Amount or Debit/Credit columns. Found: " + ", ".join(headers))
        g = lambda r, k: r[self.map[k]] if k in self.map and self.map[k] < len(r) else None
        self.rows = []
        for i, r in enumerate(rows):
            d = _d(g(r, "date"))
            if d is None:
                continue
            dr, cr = _n(g(r, "debit")), _n(g(r, "credit"))
            amt = _n(g(r, "amount")) if "amount" in self.map else dr - cr
            self.rows.append({"row": first + i, "date": d, "created": _d(g(r, "created")), "voucher": str(g(r, "voucher") or "").strip(),
                              "account": str(g(r, "account") or "").strip(), "desc": str(g(r, "desc") or "").strip(),
                              "debit": dr, "credit": cr, "amount": amt, "user": str(g(r, "user") or "").strip(),
                              "party": str(g(r, "party") or "").strip(), "approver": str(g(r, "approver") or "").strip()})


def _ex(cid, title, sev, detail, loc, exp="", found=""):
    return Finding(cid, title, sev, detail, loc, str(exp), str(found))


def _rows(rs, k=6):
    return ", ".join(str(r["row"]) for r in rs[:k]) + (f" (+{len(rs) - k} more)" if len(rs) > k else "")


class FACtx:
    def __init__(self, gl, params, period=None, scope_years=None, vendors=None, employees=None, related=None, register=None, evidence_dir=None, extra=None):
        self.gl, self.P, self.p = gl, params, params["forensic"]
        self.period = period                  # (start, end) datetimes
        self.scope_years = scope_years or []
        self.vendors, self.employees, self.related = vendors, employees, related or []
        self.register, self.evidence_dir = register, evidence_dir
        self.x = extra or {}              # bank, mandate, signatures, fs_data, stock, holidays


# ------------------------------------------------------------------ FA-01 scope
def fa01_scope(c: FACtx):
    if not c.gl:
        raise NotRun("General ledger / transaction file not supplied")
    ys = Counter(r["date"].year for r in c.gl.rows)
    out = []
    if c.scope_years:
        extra = {y: n for y, n in ys.items() if y not in c.scope_years}
        miss = [y for y in c.scope_years if y not in ys]
        if extra:
            out.append(_ex("FA-01", "Transactions fall outside the years in the signed scope", "Medium", ", ".join(f"{y}: {n} lines" for y, n in sorted(extra.items())), "GL", str(c.scope_years), str(sorted(ys))))
        if miss:
            out.append(_ex("FA-01", "A year in the signed scope has no transactions in the data supplied", "High", f"Missing years: {miss}", "GL", str(c.scope_years), str(sorted(ys))))
    months = sorted({(r["date"].year, r["date"].month) for r in c.gl.rows})
    if months:
        a, z = months[0], months[-1]
        full = [(y, m) for y in range(a[0], z[0] + 1) for m in range(1, 13) if (y, m) >= a and (y, m) <= z]
        gap = [f"{y}-{m:02d}" for y, m in full if (y, m) not in months]
        if gap:
            out.append(_ex("FA-01", "Months with no postings inside the GL range: possible incomplete extract", "Medium", ", ".join(gap[:12]), "GL", "continuous months", f"{len(gap)} empty"))
    return out


# ------------------------------------------------------------------ FA-05 GL analytics
def _benford(vals, min_items, alert):
    d1 = [int(str(abs(v)).lstrip("0.").replace(".", "")[0]) for v in vals if abs(v) >= 10]
    if len(d1) < min_items:
        return None
    cnt = Counter(d1)
    mad = sum(abs(cnt.get(d, 0) / len(d1) - math.log10(1 + 1 / d)) for d in range(1, 10)) / 9
    worst = max(range(1, 10), key=lambda d: abs(cnt.get(d, 0) / len(d1) - math.log10(1 + 1 / d)))
    return mad, worst, cnt.get(worst, 0) / len(d1), math.log10(1 + 1 / worst), len(d1)


def fa05_gl(c: FACtx):
    if not c.gl:
        raise NotRun("General ledger / transaction file not supplied")
    P, rows, out = c.p, c.gl.rows, []
    amt = lambda r: abs(r["amount"]) if r["amount"] else max(r["debit"], r["credit"])
    big = [r for r in rows if amt(r) >= P["round_min_amount"]]
    rnd = [r for r in big if amt(r) % 1000 == 0]
    if big and len(rnd) / len(big) > P["round_share_alert"] and len(rnd) >= 5:
        out.append(_ex("FA-05", "High share of round-thousand amounts", "Medium", f"{len(rnd)} of {len(big)} lines >= {P['round_min_amount']:,} ({len(rnd) / len(big):.0%}); rows {_rows(rnd)}", "GL", f"<{P['round_share_alert']:.0%}", f"{len(rnd) / len(big):.0%}"))
    we = [r for r in rows if r["date"].weekday() in P["weekend_days"] and amt(r) >= P["round_min_amount"]]
    hol = {str(h)[:10] for h in list(c.P.get("holidays") or []) + list(c.x.get("holidays") or [])}
    we += [r for r in rows if r["date"].strftime("%Y-%m-%d") in hol and r not in we and amt(r) >= P["round_min_amount"]]
    if we:
        out.append(_ex("FA-05", "Material postings on weekends / public holidays", "Medium", f"{len(we)} lines; rows {_rows(we)}", "GL", "business days", f"{len(we)} lines"))
    night = [r for r in rows if r["created"] and (r["created"].hour, r["created"].minute) != (0, 0) and (r["created"].hour >= P["night_hours"][0] or r["created"].hour < P["night_hours"][1]) and amt(r) >= P["round_min_amount"]]
    if night:
        out.append(_ex("FA-05", "Material entries created at night (outside working hours)", "Medium", f"{len(night)} lines; rows {_rows(night)}", "GL", f"{P['night_hours'][1]:02d}:00-{P['night_hours'][0]:02d}:00 only", f"{len(night)} lines"))
    if c.period:
        post = [r for r in rows if r["date"] > c.period[1]]
        back = [r for r in rows if r["created"] and r["date"] <= c.period[1] < r["created"]]
        if back:
            out.append(_ex("FA-05", "Entries dated inside the period but created after period end (backdated / post-close)", "High", f"{len(back)} lines; rows {_rows(back)}", "GL", f"created <= {c.period[1]:%d-%b-%Y}", f"{len(back)} later"))
        if post:
            out.append(_ex("FA-05", "Entries dated after the period end are in the extract", "Low", f"{len(post)} lines; rows {_rows(post)}", "GL"))
    seen, dups = defaultdict(list), []
    for r in rows:
        k = (r["date"].date(), r["account"], round(r["amount"] or (r["debit"] - r["credit"]), 2), r["party"], r["desc"].lower())
        if round(abs(r["amount"] or r["debit"] or r["credit"]), 2) > 0:
            seen[k].append(r)
    for k, lst in seen.items():
        if len(lst) > 1:
            dups.append(lst)
    if dups:
        out.append(_ex("FA-05", "Possible duplicate postings (same date, account, party, amount and narration)", "High", f"{len(dups)} sets; e.g. rows {_rows([r for d in dups[:3] for r in d])}", "GL", "unique", f"{len(dups)} sets"))
    by_v = defaultdict(list)
    for r in rows:
        if r["voucher"]:
            by_v[r["voucher"]].append(r)
    unb = [(v, sum(x["debit"] - x["credit"] for x in lst)) for v, lst in by_v.items() if c.gl.map.get("debit") is not None and abs(sum(x["debit"] - x["credit"] for x in lst)) > 1]
    if unb:
        out.append(_ex("FA-05", "Vouchers that do not balance", "High", "; ".join(f"{v}: {d:,.0f}" for v, d in unb[:6]), "GL", "Dr = Cr", f"{len(unb)} unbalanced"))
    nums = sorted({int(m.group(1)) for v in by_v if (m := re.search(r"(\d+)\s*$", v))})
    if len(nums) > 20:
        miss = [n for n in range(nums[0], nums[-1]) if n not in set(nums)]
        if miss and len(miss) / (nums[-1] - nums[0] + 1) < 0.5:
            out.append(_ex("FA-05", "Gaps in the voucher number sequence", "Medium", f"{len(miss)} missing numbers, e.g. {miss[:8]}", "GL", "continuous", f"{len(miss)} gaps"))
    users = Counter(r["user"] for r in rows if r["user"])
    if users:
        u, n = users.most_common(1)[0]
        if len(users) > 1 and n / sum(users.values()) > P["user_concentration_alert"] and sum(users.values()) > 50:
            out.append(_ex("FA-05", "One user posts most of the entries (concentration)", "Medium", f"{u}: {n} of {sum(users.values())} ({n / sum(users.values()):.0%})", "GL", f"<{P['user_concentration_alert']:.0%}", f"{n / sum(users.values()):.0%}"))
    sa = [r for r in rows if r["user"] and r["approver"] and r["user"].lower() == r["approver"].lower()]
    if sa:
        out.append(_ex("FA-05", "Same person prepared and approved the entry", "High", f"{len(sa)} lines; rows {_rows(sa)}", "GL", "segregation", f"{len(sa)} lines"))
    pct = P["just_below_pct"]
    uniq = {(r["voucher"] or r["row"], round(amt(r), 2)): r for r in rows if amt(r)}.values()      # one line per voucher amount
    for lim in P["approval_limits"]:
        below = [r for r in uniq if lim * (1 - pct) <= amt(r) < lim]
        above = [r for r in uniq if lim <= amt(r) < lim * (1 + pct)]
        if len(below) >= 5 and len(below) >= 2 * max(len(above), 1):
            out.append(_ex("FA-05", f"Amounts clustered just below the {lim:,} approval limit (possible splitting)", "High",
                           f"{len(below)} items within {pct:.0%} below vs {len(above)} within {pct:.0%} above; rows {_rows(below)}", "GL", "no cluster", f"{len(below)} vs {len(above)}"))
    b = _benford([amt(r) for r in rows if amt(r)], P["benford_min_items"], P["benford_mad_alert"])
    if b and b[0] > P["benford_mad_alert"]:
        out.append(_ex("FA-05", "First-digit distribution departs from Benford's law", "Medium", f"MAD {b[0]:.4f} (> {P['benford_mad_alert']}); digit {b[1]} is {b[2]:.1%} vs expected {b[3]:.1%} over {b[4]} items. Indicator only: not proof.", "GL", f"MAD <= {P['benford_mad_alert']}", f"{b[0]:.4f}"))
    return out


# ------------------------------------------------------------------ FA-06 master data
def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _master(path):
    headers, rows, first = read_table(path)
    low = [h.lower() for h in headers]
    find = lambda *keys: next((i for i, h in enumerate(low) if any(k in h for k in keys)), None)
    ix = {"name": find("name", "vendor", "employee"), "bank": find("iban", "bank account", "account no", "account number", "bank"),
          "addr": find("address", "location"), "phone": find("phone", "mobile", "tel", "contact"), "trn": find("trn", "tax reg", "vat no", "tax id"),
          "created": find("created", "date")}
    out = []
    for i, r in enumerate(rows):
        g = lambda k: (r[ix[k]] if ix[k] is not None and ix[k] < len(r) else None)
        if g("name"):
            out.append({"row": first + i, **{k: g(k) for k in ix}})
    return out


def fa06_master(c: FACtx):
    if not c.vendors:
        raise NotRun("Vendor master not supplied")
    V, E, out = _master(c.vendors), (_master(c.employees) if c.employees else []), []
    for key, label in (("bank", "bank account / IBAN"), ("addr", "address"), ("phone", "phone number"), ("trn", "TRN")):
        vi = defaultdict(list)
        for v in V:
            if _norm(v[key]) and len(_norm(v[key])) > 4:
                vi[_norm(v[key])].append(v)
        for k, lst in vi.items():
            if len(lst) > 1 and len({_norm(x["name"]) for x in lst}) > 1:
                out.append(_ex("FA-06", f"Different vendors share the same {label}", "High", "; ".join(f"{x['name']} (row {x['row']})" for x in lst[:4]), "Vendor master", "unique", str(len(lst))))
        for e in E:
            ek = _norm(e[key])
            if ek and len(ek) > 4 and ek in vi:
                out.append(_ex("FA-06", f"Vendor and employee share the same {label}", "High", f"employee {e['name']} (row {e['row']}) = vendor {vi[ek][0]['name']} (row {vi[ek][0]['row']})", "Vendor vs employee master", "no overlap", "match"))
    names = [(v, _norm(v["name"])) for v in V]
    import difflib
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i][1], names[j][1]
            if a != b and len(a) > 6 and difflib.SequenceMatcher(None, a, b).ratio() > 0.92:
                out.append(_ex("FA-06", "Near-duplicate vendor names", "Medium", f"'{names[i][0]['name']}' (row {names[i][0]['row']}) ~ '{names[j][0]['name']}' (row {names[j][0]['row']})", "Vendor master", "single record", "2 records"))
                break
    pobox = [v for v in V if re.search(r"p\.?\s*o\.?\s*box", str(v["addr"] or ""), re.I) and not v["phone"]]
    if len(pobox) >= 3:
        out.append(_ex("FA-06", "Several vendors have only a PO Box and no phone number", "Low", "; ".join(x["name"] for x in pobox[:5]), "Vendor master"))
    return out[:15]


# ------------------------------------------------------------------ FA-07 related party / unusual
def fa07_related(c: FACtx):
    if not c.gl:
        raise NotRun("General ledger / transaction file not supplied")
    out, P = [], c.p
    import difflib
    for name in c.related:
        n = _norm(name)
        if len(n) < 5:
            continue
        hit = [r for r in c.gl.rows if (_norm(r["party"]) and difflib.SequenceMatcher(None, n, _norm(r["party"])).ratio() > 0.88) or n in _norm(r["desc"])]
        if hit:
            tot = sum(abs(r["amount"] or max(r["debit"], r["credit"])) for r in hit)
            out.append(_ex("FA-07", f"Transactions with related party '{name}'", "Medium", f"{len(hit)} lines, total {tot:,.0f}; rows {_rows(hit)}. Confirm disclosure (IAS 24) and arm's length terms.", "GL", "disclosed", f"{len(hit)} lines"))
    kw = re.compile("|".join(re.escape(k) for k in P["keywords"]), re.I)
    hits = [r for r in c.gl.rows if kw.search(r["desc"]) and abs(r["amount"] or max(r["debit"], r["credit"])) >= P["round_min_amount"]]
    if len(hits) >= 3:
        words = Counter(m.group(0).lower() for r in hits for m in [kw.search(r["desc"])] if m)
        out.append(_ex("FA-07", "Material entries with high-risk narration keywords", "Low", f"{len(hits)} lines ({', '.join(f'{w} x{n}' for w, n in words.most_common(4))}); rows {_rows(hits)}", "GL"))
    return out


# ------------------------------------------------------------------ FA-03 / FA-08 evidence
REG_COLS = {"item": ["item", "ref", "id", "no"], "desc": ["description", "document", "particulars"], "source": ["source", "obtained from", "received from"],
            "date": ["date received", "received on", "date", "received"], "by": ["received by", "collected by", "obtained by"],
            "custodian": ["custodian", "held by", "stored"], "hash": ["sha", "hash", "checksum"]}


def _register(path):
    headers, rows, first = read_table(path)
    m = map_columns_generic(headers, REG_COLS)
    return headers, rows, first, m


def map_columns_generic(headers, spec):
    low = [h.lower() for h in headers]
    m = {}
    for k, names in spec.items():
        for nm in names:
            i = next((i for i, h in enumerate(low) if nm in h and i not in m.values()), None)
            if i is not None:
                m[k] = i
                break
    return m


def fa03_register(c: FACtx):
    if not c.register:
        raise NotRun("Evidence / confirmation register not supplied")
    headers, rows, first, m = _register(c.register)
    out = []
    need = [k for k in ("item", "desc", "source", "date", "by") if k not in m]
    if need:
        out.append(_ex("FA-03", "Register is missing required columns", "High", ", ".join(need), "Register", "Item, Description, Source, Date received, Received by", ", ".join(headers)))
    live = [(first + i, r) for i, r in enumerate(rows) if any(x not in (None, "") for x in r)]
    for k, label in (("source", "source"), ("date", "date received"), ("by", "received by")):
        if k in m:
            blank = [rn for rn, r in live if not (r[m[k]] not in (None, "") if m[k] < len(r) else False)]
            if blank:
                out.append(_ex("FA-03", f"Register entries with no {label}", "Medium", f"{len(blank)} rows: {blank[:10]}", "Register", "complete", f"{len(blank)} blank"))
    if "date" in m:
        yrs = Counter(_d(r[m["date"]]).year for _, r in live if m["date"] < len(r) and _d(r[m["date"]]))
        if c.scope_years:
            gap = [y for y in c.scope_years if y not in yrs]
            if gap:
                out.append(_ex("FA-03", "No evidence logged for these scope years", "High", str(gap), "Register", str(c.scope_years), str(sorted(yrs))))
    return out


def _sha(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while b := fh.read(chunk):
            h.update(b)
    return h.hexdigest()


def fa08_custody(c: FACtx):
    if not c.register and not c.evidence_dir:
        raise NotRun("Evidence register and evidence folder not supplied")
    out = []
    files = {p.name: p for p in Path(c.evidence_dir).rglob("*") if p.is_file()} if c.evidence_dir else {}
    if c.register:
        headers, rows, first, m = _register(c.register)
        logged = set()
        for i, r in enumerate(rows):
            if not any(x not in (None, "") for x in r):
                continue
            desc = str(r[m["desc"]]).strip() if "desc" in m and m["desc"] < len(r) and r[m["desc"]] else ""
            hv = str(r[m["hash"]]).strip().lower() if "hash" in m and m["hash"] < len(r) and r[m["hash"]] else ""
            fn = next((n for n in files if desc and (n.lower() in desc.lower() or Path(n).stem.lower() in desc.lower())), None)
            if fn:
                logged.add(fn)
                if hv and hv != _sha(files[fn]):
                    out.append(_ex("FA-08", "File hash differs from the hash recorded in the register (file changed since logging)", "High", f"{fn} (register row {first + i})", "Register vs file", hv[:16] + "...", _sha(files[fn])[:16] + "..."))
            if "hash" in m and not hv:
                out.append(_ex("FA-08", "Evidence item logged without a hash", "Medium", f"register row {first + i}", "Register", "SHA-256", "blank"))
            if "custodian" not in m:
                break
        unlogged = [n for n in files if n not in logged]
        if files and unlogged:
            out.append(_ex("FA-08", "Files in the evidence folder are not in the register", "Medium", ", ".join(unlogged[:8]) + (" ..." if len(unlogged) > 8 else ""), "Evidence folder", "all logged", f"{len(unlogged)} unlogged"))
    elif files:
        out.append(_ex("FA-08", "Evidence folder supplied without a register", "Medium", f"{len(files)} files cannot be tied to a custody log", "Evidence folder"))
    return out[:15]


# ------------------------------------------------------------------ FA-04 document authenticity
def _meta(path):
    ext = Path(path).suffix.lower()
    m = {"created": None, "modified": None, "producer": "", "author": "", "last_by": "", "fonts": 0, "pages": 0, "image_only": False}
    try:
        if ext == ".pdf":
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                md = pdf.metadata or {}
                m.update(producer=" ".join(str(md.get(k, "")) for k in ("Producer", "Creator")), author=str(md.get("Author", "")))
                m["created"], m["modified"] = _pdfdate(md.get("CreationDate")), _pdfdate(md.get("ModDate"))
                fonts, chars = set(), 0
                for pg in pdf.pages[:20]:
                    fonts |= {ch["fontname"].split("+")[-1] for ch in pg.chars}
                    chars += len(pg.chars)
                m.update(fonts=len(fonts), pages=len(pdf.pages), image_only=(chars == 0 and len(pdf.pages) > 0))
        elif ext in (".docx", ".docm"):
            import docx
            cp = docx.Document(str(path)).core_properties
            m.update(created=cp.created, modified=cp.modified, author=cp.author or "", last_by=cp.last_modified_by or "")
        elif ext in (".xlsx", ".xlsm"):
            import openpyxl
            _wbk = openpyxl.load_workbook(str(path), read_only=True)
            pr = _wbk.properties
            _wbk.close()
            m.update(created=pr.created, modified=pr.modified, author=pr.creator or "", last_by=pr.lastModifiedBy or "")
        elif ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff"):
            from PIL import Image
            ex = Image.open(str(path)).getexif()
            m["producer"] = str(ex.get(305, ""))
            m["created"] = _d(str(ex.get(36867) or ex.get(306) or "").replace(":", "-", 2)) if (ex.get(36867) or ex.get(306)) else None
            m["exif"] = bool(ex)
    except Exception as e:
        m["error"] = str(e)
    return m


def _pdfdate(s):
    mm = re.match(r"D?:?(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?", str(s or ""))
    return datetime(*[int(x) if x else 0 for x in mm.groups()[:3]], *[int(x) if x else 0 for x in mm.groups()[3:]]) if mm else None


def fa04_authenticity(c: FACtx):
    if not c.evidence_dir:
        raise NotRun("Evidence folder not supplied")
    files = [p for p in Path(c.evidence_dir).rglob("*") if p.is_file() and p.suffix.lower() in (".pdf", ".docx", ".docm", ".xlsx", ".xlsm", ".jpg", ".jpeg", ".png", ".tif", ".tiff")]
    if not files:
        raise NotRun("No documents found in the evidence folder")
    P, out = c.p, []
    for p in files:
        m = _meta(p)
        rel = str(p.relative_to(c.evidence_dir))
        prod = (m["producer"] or "").lower()
        bad = next((s for s in P["suspect_producers"] if s in prod), None)
        if bad:
            out.append(_ex("FA-04", f"Created/edited with {bad.title()}: editing or conversion software", "High", f"{rel}: producer '{m['producer'].strip()}'", rel, "original system export", m["producer"].strip()))
        if m["created"] and m["modified"]:
            cr, mo = m["created"].replace(tzinfo=None), m["modified"].replace(tzinfo=None)
            if mo < cr:
                out.append(_ex("FA-04", "Modified date earlier than created date", "Medium", f"{rel}: created {cr:%d-%b-%Y %H:%M}, modified {mo:%d-%b-%Y %H:%M}", rel))
            elif (mo - cr).days > P["modified_after_created_days"] and Path(p).suffix.lower() == ".pdf":
                out.append(_ex("FA-04", "PDF modified long after creation (re-saved after issue)", "Medium", f"{rel}: created {cr:%d-%b-%Y}, modified {mo:%d-%b-%Y}", rel))
        if m["last_by"] and m["author"] and m["last_by"].strip().lower() != m["author"].strip().lower():
            out.append(_ex("FA-04", "Last modified by a different user than the author", "Low", f"{rel}: author '{m['author']}', last modified by '{m['last_by']}'", rel))
        if m["fonts"] and m["fonts"] > 4:
            out.append(_ex("FA-04", "Many different fonts in one PDF (possible pasted/edited text)", "Medium", f"{rel}: {m['fonts']} fonts", rel, "<=4", str(m["fonts"])))
        if m["image_only"]:
            out.append(_ex("FA-04", "Image-only PDF: no text layer to verify against the source", "Low", rel, rel))
        if Path(p).suffix.lower() in (".jpg", ".jpeg") and m.get("exif") is False:
            out.append(_ex("FA-04", "Photo has no EXIF data (stripped or re-saved)", "Low", rel, rel))
    return out[:20]


REGISTRY = {"FA-01": fa01_scope, "FA-03": fa03_register, "FA-04": fa04_authenticity, "FA-05": fa05_gl, "FA-06": fa06_master, "FA-07": fa07_related, "FA-08": fa08_custody}


def run_fa(params, gl_path=None, period_end=None, scope_years=None, vendors=None, employees=None, related=None, register=None, evidence_dir=None, **extra):
    gl = GL(gl_path) if gl_path else None
    period = None
    if period_end:
        pe = _d(period_end) or period_end
        period = (None, pe.replace(hour=23, minute=59, second=59))
    c = FACtx(gl, params, period, scope_years, vendors, employees, related, register, evidence_dir, {k: v for k, v in extra.items() if v})
    from .rules_fa2 import FA2_REGISTRY
    results = []
    for cid, fn in {**REGISTRY, **FA2_REGISTRY}.items():
        try:
            f = fn(c)
            results.append(Result(cid, "EXC" if f else "PASS", f))
        except NotRun as e:
            results.append(Result(cid, "NOTRUN", [], str(e)))
        except Exception as e:                       # one test must not stop the others
            results.append(Result(cid, "NOTRUN", [], f"Test could not run on this file: {type(e).__name__}: {str(e)[:120]}"))
    results += _assisted(c, results)
    results.sort(key=lambda r: int(r.check_id.split("-")[1]))
    return results, c


def _assisted(c, results):
    """FA-02, FA-09, FA-10 (judgement): the engine lists what it did so the reviewer can judge scope and wording."""
    from .models import Finding
    ran = [r.check_id for r in results if r.status in ("PASS", "EXC")]
    exc = [f"{r.check_id} ({len(r.findings)})" for r in results if r.status == "EXC"]
    skipped = [f"{r.check_id}: {r.note}" for r in results if r.status == "NOTRUN"]
    rows = f"{len(c.gl.rows):,} GL lines" if getattr(c, "gl", None) else "no GL"
    wp = []
    for k in ("vendors", "employees", "related", "register", "evidence_dir"):
        wp.append(f"{k}: {'supplied' if getattr(c, k, None) else 'not supplied'}")
    for k in ("bank", "mandate", "signatures", "fs_data", "stock", "holidays"):
        wp.append(f"{k}: {'supplied' if c.x.get(k) else 'not supplied'}")
    mk = lambda cid, title, det: Result(cid, "REVIEW", [Finding(cid, title, "Info", det, "Forensic paper", "", "")], "Assisted: evidence extracted, reviewer to confirm")
    return [
        mk("FA-02", "Test plan vs fraud types", f"Tests run on {rows}: {ran}. Exceptions: {exc or 'none'}. Not run: {skipped[:4] or 'none'}. Map each fraud type in the proposal (asset misappropriation, corruption, financial statement fraud) to a test above; add manual procedures for gaps."),
        mk("FA-09", "Working-paper completeness", "; ".join(wp) + ". The JSON audit trail holds SHA-256 of every input. Confirm scope, population completeness (GL to TB), sampling basis and evidence chain for the case type."),
        mk("FA-10", "Facts vs opinion", "Findings in this paper are indicators (statistical/rule-based), not proof. Check the final report separates facts (documents, amounts, dates) from opinion and avoids conclusions on intent."),
    ]
