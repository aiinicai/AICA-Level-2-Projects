"""Parse TallyPrime XML responses into plain dicts."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

import xml.etree.ElementTree as etree

# Tally sometimes emits control-char references (&#4;) that are illegal in XML 1.0
_CHAR_REF = re.compile(rb"&#(x[0-9a-fA-F]+|[0-9]+);")
_BAD_CHARS = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _drop_control_ref(m: re.Match) -> bytes:
    v = m.group(1)
    n = int(v[1:], 16) if v[:1] in (b"x", b"X") else int(v)
    return b"" if n < 32 and n not in (9, 10, 13) else m.group(0)


# Tally emits namespaced names (<UDF:GSTREGDETAILS.LIST>, xmlns:UDF=...) often without declaring
# them. Flatten every prefix (UDF:X -> UDF_X) in tag and attribute names so any parser accepts it.
_PREFIXED_TAG = re.compile(rb"(</?)([A-Za-z_][\w.\-]*):([A-Za-z_][\w.\-]*)")
_PREFIXED_ATTR = re.compile(rb"(\s)([A-Za-z_][\w.\-]*):([A-Za-z_][\w.\-]*)(\s*=)")


def clean(raw: bytes) -> bytes:
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        raw = raw.decode("utf-16").encode("utf-8")
    else:
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            # Tally can emit Windows-1252 bytes (en dash, Rs symbol, non-breaking space) in a "UTF-8" reply
            raw = raw.decode("cp1252", errors="replace").encode("utf-8")
    raw = _BAD_CHARS.sub(b"", _CHAR_REF.sub(_drop_control_ref, raw))
    raw = _PREFIXED_TAG.sub(rb"\1\2_\3", raw)
    return _PREFIXED_ATTR.sub(rb"\1\2_\3\4", raw)


def parse_root(raw: bytes) -> etree.Element:
    """stdlib parser (pyexpat ships signed with Python, so Smart App Control allows it)."""
    data = clean(raw)
    data = re.sub(rb"<\?xml[^>]*\?>", b"", data, count=1)   # encoding already normalised to UTF-8
    return etree.fromstring(data)


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def element_to_dict(el) -> dict:
    """Flat dict of simple children (+ NAME attribute). Nested .LIST children kept as lists of dicts."""
    out: dict = {}
    if el.get("NAME"):
        out["NAME"] = el.get("NAME")
    for ch in el:
        tag = ch.tag if isinstance(ch.tag, str) else ""
        if not tag:
            continue
        if tag.endswith(".LIST"):
            out.setdefault(tag, []).append(element_to_dict(ch))
        elif len(ch) == 0:
            if tag == "NAME" and "NAME" in out:
                continue
            out[tag] = _text(ch)
        else:  # e.g. LANGUAGENAME.LIST handled above; other nested blocks
            out[tag] = element_to_dict(ch)
    return out


def find_deep(d, key: str) -> str:
    """First non-empty value for key anywhere in a nested dict/list structure."""
    if isinstance(d, dict):
        v = d.get(key)
        if isinstance(v, str) and v:
            return v
        for val in d.values():
            r = find_deep(val, key)
            if r:
                return r
    elif isinstance(d, list):
        for item in d:
            r = find_deep(item, key)
            if r:
                return r
    return ""


_BARE_AMP = re.compile(rb"&(?!(?:[A-Za-z][A-Za-z0-9]*|#[0-9]+|#x[0-9A-Fa-f]+);)")
_LT_IN_TEXT = re.compile(rb"<(?=[\s\d=<>&\-.,;:)(])")
LAST_SKIPPED: list[int] = [0]


def _repair(data: bytes) -> bytes:
    """Fix what Tally sometimes leaves unescaped in narrations / names: bare '&' and stray '<'."""
    data = _BARE_AMP.sub(b"&amp;", data)
    return _LT_IN_TEXT.sub(b"&lt;", data)


def parse_collection(raw: bytes, tag: str) -> list[dict]:
    """Parse a collection; if the whole reply is malformed, repair it, and as a last resort parse
    record by record, skipping only the broken ones (count kept in LAST_SKIPPED[0])."""
    LAST_SKIPPED[0] = 0
    data = clean(raw)
    data = re.sub(rb"<\?xml[^>]*\?>", b"", data, count=1)
    for attempt in (data, _repair(data)):
        try:
            return [element_to_dict(e) for e in etree.fromstring(attempt).iter(tag)]
        except etree.ParseError:
            continue
    out, skipped = [], 0
    t = tag.encode()
    for m in re.finditer(rb"<" + t + rb"[\s>].*?</" + t + rb">", _repair(data), re.S):
        try:
            out.append(element_to_dict(etree.fromstring(m.group(0))))
        except etree.ParseError:
            skipped += 1
    if not out and skipped == 0:
        raise ValueError("Tally's reply could not be read at all")
    LAST_SKIPPED[0] = skipped
    return out


_NUM = re.compile(r"-?\s*[0-9][0-9,]*(?:\.[0-9]+)?")


def _num(t: str) -> Decimal | None:
    """First number in t, keeping a leading minus even if a currency symbol sits between ('-$ 5', '-₹ 5', '-? 5')."""
    neg = t.strip().startswith("-")
    m = _NUM.search(t)
    if not m:
        return None
    try:
        v = Decimal(m.group(0).replace(",", "").replace(" ", "").lstrip("-"))
    except InvalidOperation:
        return None
    return -v if neg or m.group(0).startswith("-") else v


def amount(s: str) -> Decimal:
    """Tally amounts, returned as a signed Decimal in rupees (Tally sign):
    '-1180.00', '1,180.00 Dr', '₹ 1180.00', and foreign-currency amounts such as
    '-$ 50000.00 @ ₹ 90.5291/$ = -₹ 4526455.00' (the rupee figure after '=' is used; the ₹ often
    arrives as '?'). Without '=' the rupee value is forex quantity x rate."""
    if not s:
        return Decimal(0)
    t = s.strip()
    sign = 1
    if t.endswith(" Dr"):
        t, sign = t[:-3], -1
    elif t.endswith(" Cr"):
        t = t[:-3]
    if "=" in t:
        v = _num(t.rsplit("=", 1)[1])
    elif "@" in t:
        qty, rate = t.split("@", 1)
        q, r = _num(qty), _num(rate.split("/")[0])
        v = (q * abs(r)).quantize(Decimal("0.01")) if q is not None and r is not None else q
    else:
        v = _num(t)
    return (v if v is not None else Decimal(0)) * sign


_FX = re.compile(r"^\s*(-?)\s*([^\d\s\-][^\d\s]*)?\s*(-?[0-9][0-9,]*(?:\.[0-9]+)?)\s*@\s*[^\d\s]*\s*"
                 r"([0-9][0-9,]*(?:\.[0-9]+)?)?\s*/\s*([^\s=]+)?")


def forex(s: str) -> dict | None:
    """'-$ 50000.00 @ ₹ 90.5291/$ = -₹ 4526455.00' -> {'fc': Decimal('-50000.00'), 'rate': Decimal('90.5291'),
    'cur': '$', 'inr': Decimal('-4526455.00')}; None for a plain rupee amount."""
    if not s or "@" not in s:
        return None
    m = _FX.match(s.split("=")[0])
    if not m:
        return None
    neg, sym, qty, rate, unit = m.groups()
    try:
        fc = Decimal(qty.replace(",", ""))
        fc = -abs(fc) if neg or qty.startswith("-") else fc
        r = Decimal(rate.replace(",", "")) if rate else Decimal(0)
    except InvalidOperation:
        return None
    return {"fc": fc, "rate": r, "cur": (sym or unit or "").strip(), "inr": amount(s)}


_GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_GSTIN_RE = re.compile(rb"\b(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b")


def gstin_valid(g: str) -> bool:
    """Format + check digit (mod-36, alternating weights 1,2)."""
    g = (g or "").strip().upper()
    if not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", g):
        return False
    total = 0
    for i, ch in enumerate(g[:14]):
        prod = _GSTIN_CHARS.index(ch) * (1 if i % 2 == 0 else 2)
        total += prod // 36 + prod % 36
    return _GSTIN_CHARS[(36 - total % 36) % 36] == g[14]


def scan_gstins(raw: bytes) -> list[str]:
    """Every valid GSTIN anywhere in a response, in order, de-duplicated."""
    seen: list[str] = []
    for m in _GSTIN_RE.finditer(raw.upper()):
        g = m.group(1).decode()
        if gstin_valid(g) and g not in seen:
            seen.append(g)
    return seen


def parse_companies(raw: bytes) -> list[dict]:
    out = []
    for c in parse_collection(raw, "COMPANY"):
        out.append({
            "name": c.get("NAME", ""),
            "guid": c.get("GUID", ""),
            "formal_name": c.get("BASICCOMPANYFORMALNAME", ""),
            "books_from": c.get("BOOKSFROM", ""),
            "state": c.get("STATENAME", "") or find_deep(c, "STATE"),
            "gstin": c.get("GSTREGISTRATIONNUMBER", "") or find_deep(c, "GSTIN"),
            "pan": c.get("INCOMETAXNUMBER", ""),
        })
    return [c for c in out if c["name"]]


def parse_masters(raw: bytes, kind: str) -> list[dict]:
    tag = {"ledger": "LEDGER", "group": "GROUP", "stock_item": "STOCKITEM", "unit": "UNIT",
           "godown": "GODOWN", "voucher_type": "VOUCHERTYPE"}[kind]
    out = []
    for d in parse_collection(raw, tag):
        if not d.get("NAME"):
            continue
        rec = {"name": d["NAME"], "guid": d.get("GUID", ""), "parent": d.get("PARENT", ""), "data": d}
        if kind == "ledger":
            rec["data"] = {**d, "_gstin": d.get("PARTYGSTIN") or find_deep(d.get("LEDGSTREGDETAILS.LIST", []), "GSTIN")}
        if kind == "stock_item":
            rec["data"] = {**d, "_hsn": find_deep(d, "HSNCODE") or find_deep(d, "HSN")}
        out.append(rec)
    return out


def parse_vouchers(raw: bytes) -> list[dict]:
    out = []
    for v in parse_collection(raw, "VOUCHER"):
        entries = []
        # Invoice-view vouchers can carry the same entries in both lists (seen on USD export sales): use
        # ALLLEDGERENTRIES when it has entries, LEDGERENTRIES only otherwise - never both.
        has_all = any(isinstance(e, dict) and e.get("LEDGERNAME") for e in v.get("ALLLEDGERENTRIES.LIST", []))
        for key in (("ALLLEDGERENTRIES.LIST",) if has_all else ("LEDGERENTRIES.LIST",)):
            for e in v.get(key, []):
                name = e.get("LEDGERNAME", "")
                if not name:
                    continue
                amt = amount(e.get("AMOUNT", ""))
                dr = e.get("ISDEEMEDPOSITIVE", "").lower() == "yes" if e.get("ISDEEMEDPOSITIVE") else amt < 0
                ent = {"ledger": name, "amount": str(abs(amt)), "dr": dr}
                fx = forex(e.get("AMOUNT", ""))
                if fx and fx["fc"]:
                    ent["fc"] = str(abs(fx["fc"]))
                    ent["rate"] = str(fx["rate"])
                    ent["cur"] = fx["cur"]
                bills = [{"name": b.get("NAME", ""), "type": b.get("BILLTYPE", ""),
                          "amount": str(amount(b.get("AMOUNT", "")))}
                         for b in (e.get("BILLALLOCATIONS.LIST") or []) if isinstance(b, dict)]
                if bills:
                    ent["bills"] = bills
                entries.append(ent)
        # item invoices: the purchase / sales ledger sits inside each stock line's accounting allocation
        for key in ("ALLINVENTORYENTRIES.LIST", "INVENTORYENTRIES.LIST"):
            for it in v.get(key, []) or []:
                if not isinstance(it, dict):
                    continue
                for a in it.get("ACCOUNTINGALLOCATIONS.LIST", []) or []:
                    if not isinstance(a, dict) or not a.get("LEDGERNAME"):
                        continue
                    amt = amount(a.get("AMOUNT", ""))
                    dr = a.get("ISDEEMEDPOSITIVE", "").lower() == "yes" if a.get("ISDEEMEDPOSITIVE") else amt < 0
                    same = next((x for x in entries if x["ledger"] == a["LEDGERNAME"] and x["dr"] == dr
                                 and x.get("_inv")), None)
                    if same:
                        same["amount"] = str(Decimal(same["amount"]) + abs(amt))
                    else:
                        entries.append({"ledger": a["LEDGERNAME"], "amount": str(abs(amt)), "dr": dr, "_inv": True})
            if any(isinstance(it, dict) for it in v.get(key, []) or []):
                break
        for x in entries:
            x.pop("_inv", None)
        out.append({
            "guid": v.get("GUID", ""), "masterid": v.get("MASTERID", ""), "date": v.get("DATE", ""),
            "voucher_type": v.get("VOUCHERTYPENAME", ""), "number": v.get("VOUCHERNUMBER", ""),
            "party": v.get("PARTYLEDGERNAME", ""), "narration": v.get("NARRATION", ""),
            "reference": v.get("REFERENCE", ""),
            "entries": entries,
        })
    return out


def parse_import_response(raw: bytes) -> dict:
    """<RESPONSE><CREATED>1</CREATED><ALTERED>0</ALTERED><ERRORS>0</ERRORS><LASTVCHID>123</LASTVCHID>..."""
    root = parse_root(raw)
    get = lambda t: _text(root.find(f".//{t}"))
    errors = [(_text(e)) for e in root.iter("LINEERROR")]
    return {
        "created": int(get("CREATED") or 0), "altered": int(get("ALTERED") or 0),
        "errors": int(get("ERRORS") or 0), "exceptions": int(get("EXCEPTIONS") or 0),
        "last_vch_id": get("LASTVCHID"), "last_mid": get("LASTMID"), "line_errors": errors,
    }


def parse_tb_report(raw: bytes) -> list[tuple]:
    """Tally's Trial Balance report export: DSPACCNAME / DSPACCINFO pairs -> [(name, dr, cr)] (positive amounts)."""
    data = clean(raw)
    data = re.sub(rb"<\?xml[^>]*\?>", b"", data, count=1)
    try:
        root = etree.fromstring(data if data.strip().startswith(b"<ENVELOPE") else b"<ENVELOPE>" + data + b"</ENVELOPE>")
    except etree.ParseError:
        root = etree.fromstring(b"<ENVELOPE>" + _repair(data) + b"</ENVELOPE>")
    out, name = [], None
    for el in root.iter():
        if el.tag == "DSPDISPNAME":
            name = (el.text or "").strip()
        elif el.tag == "DSPACCINFO" and name is not None:
            dr = amount(el.findtext(".//DSPCLDRAMTA") or "")
            cr = amount(el.findtext(".//DSPCLCRAMTA") or "")
            out.append((name, abs(dr), abs(cr)))
            name = None
    return out
