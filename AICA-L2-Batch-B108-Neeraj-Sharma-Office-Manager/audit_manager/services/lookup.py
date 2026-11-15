"""Look-ups that save typing: PAN/state from a GSTIN, city/state from a pincode, and taxpayer details from the
official GST portal (the captcha is always typed by the user; nothing is bypassed)."""
import re
import time

import requests

GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")

STATE_CODES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra", "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
    "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman & Nicobar", "36": "Telangana", "37": "Andhra Pradesh",
    "38": "Ladakh", "97": "Other Territory",
}

# Offline fallback: state from the first digits of a pincode (3-digit entries override 2-digit ones). Approximate at borders.
PIN3 = {"403": "Goa", "605": "Puducherry", "682": "Kerala", "737": "Sikkim", "744": "Andaman & Nicobar", "160": "Chandigarh",
        "194": "Ladakh", "396": "Gujarat", "790": "Arunachal Pradesh", "791": "Arunachal Pradesh", "792": "Arunachal Pradesh",
        "793": "Meghalaya", "794": "Meghalaya", "795": "Manipur", "796": "Mizoram", "797": "Nagaland", "798": "Nagaland",
        "799": "Tripura", "244": "Uttar Pradesh", "246": "Uttarakhand", "247": "Uttarakhand", "248": "Uttarakhand",
        "249": "Uttarakhand", "262": "Uttarakhand", "263": "Uttarakhand", "814": "Jharkhand", "815": "Jharkhand",
        "816": "Jharkhand", "822": "Jharkhand"}
PIN2 = {"11": "Delhi", "12": "Haryana", "13": "Haryana", "14": "Punjab", "15": "Punjab", "16": "Punjab", "17": "Himachal Pradesh",
        "18": "Jammu & Kashmir", "19": "Jammu & Kashmir", **{str(n): "Uttar Pradesh" for n in range(20, 29)},
        **{str(n): "Rajasthan" for n in range(30, 35)}, **{str(n): "Gujarat" for n in range(36, 40)},
        **{str(n): "Maharashtra" for n in range(40, 45)}, **{str(n): "Madhya Pradesh" for n in range(45, 49)},
        "49": "Chhattisgarh", "50": "Telangana", "51": "Andhra Pradesh", "52": "Andhra Pradesh", "53": "Andhra Pradesh",
        **{str(n): "Karnataka" for n in range(56, 60)}, **{str(n): "Tamil Nadu" for n in range(60, 67)},
        "67": "Kerala", "68": "Kerala", "69": "Kerala", **{str(n): "West Bengal" for n in range(70, 75)},
        "75": "Odisha", "76": "Odisha", "77": "Odisha", "78": "Assam", "80": "Bihar", "81": "Bihar", "82": "Bihar",
        "83": "Jharkhand", "84": "Bihar", "85": "Bihar"}


def pan_from_gstin(gstin: str | None) -> str | None:
    g = (gstin or "").strip().upper()
    return g[2:12] if GSTIN_RE.match(g) else None


def state_from_gstin(gstin: str | None) -> str | None:
    return STATE_CODES.get((gstin or "")[:2])


def state_from_pincode(pin: str) -> str | None:
    return PIN3.get(pin[:3]) or PIN2.get(pin[:2])


_pin_cache: dict[str, dict] = {}


def pincode(pin: str) -> dict:
    """{'ok', 'city', 'state', 'source'}: India Post's public pincode service when online, else state only (offline table)."""
    pin = re.sub(r"\D", "", pin or "")
    if len(pin) != 6 or pin[0] == "0":
        return {"ok": False, "message": "A pincode has 6 digits."}
    if pin in _pin_cache:
        return _pin_cache[pin]
    out = None
    try:
        r = requests.get(f"https://api.postalpincode.in/pincode/{pin}", timeout=6)
        data = r.json()
        offices = (data[0] or {}).get("PostOffice") or [] if isinstance(data, list) and data else []
        if offices:
            o = offices[0]
            out = {"ok": True, "city": (o.get("District") or o.get("Block") or "").strip(), "state": (o.get("State") or "").strip(),
                   "source": "India Post"}
            _pin_cache[pin] = out
    except Exception:  # offline, slow or changed service: fall back quietly
        out = None
    if out is None:
        state = state_from_pincode(pin)
        out = {"ok": bool(state), "city": "", "state": state or "", "source": "offline"}
    return out


# ------------------------------------------------------------------ GST portal (captcha typed by the user)
BASE = "https://services.gst.gov.in"
SEARCH_PAGE, CAPTCHA_URL, DETAILS_URL = BASE + "/services/searchtp", BASE + "/services/captcha", BASE + "/services/api/search/taxpayerDetails"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
           "Accept-Language": "en-US,en;q=0.9"}
_sessions: dict[int, tuple[requests.Session, float]] = {}


class LookupError_(Exception):
    pass


def _session(user_id: int, fresh: bool = False) -> requests.Session:
    for k in [k for k, (_, t) in _sessions.items() if time.time() - t > 900]:
        _sessions.pop(k, None)
    if fresh or user_id not in _sessions:
        s = requests.Session()
        s.headers.update(HEADERS)
        _sessions[user_id] = (s, time.time())
    return _sessions[user_id][0]


def gst_captcha(user_id: int) -> tuple[bytes, str]:
    """A fresh captcha image from the GST portal for this user. Returns (bytes, mime)."""
    s = _session(user_id, fresh=True)
    try:
        s.get(SEARCH_PAGE, timeout=20)
        r = s.get(CAPTCHA_URL, params={"rnd": time.time()}, headers={"Referer": SEARCH_PAGE}, timeout=20)
        r.raise_for_status()
    except requests.RequestException:
        raise LookupError_("Could not reach the GST portal. Check the internet connection and try again.")
    if not r.content:
        raise LookupError_("The GST portal did not send a captcha. Try again.")
    return r.content, r.headers.get("Content-Type", "image/png").split(";")[0]


def parse_taxpayer(gstin: str, data: dict) -> dict:
    pradr = data.get("pradr") or {}
    addr = pradr.get("addr") if isinstance(pradr, dict) and isinstance(pradr.get("addr"), dict) else {}
    full = str(pradr.get("adr") or "").strip() if isinstance(pradr, dict) else ""
    if not full and addr:
        full = ", ".join(str(addr.get(k) or "").strip() for k in ("bno", "flno", "bnm", "st", "loc", "dst", "stcd", "pncd") if str(addr.get(k) or "").strip())
    pin = str(addr.get("pncd") or "").strip()
    if not re.fullmatch(r"\d{6}", pin):
        m = re.findall(r"\b[1-9]\d{5}\b", full)
        pin = m[-1] if m else ""
    state = str(addr.get("stcd") or "").strip() or state_from_gstin(gstin) or ""
    city = str(addr.get("dst") or addr.get("loc") or "").strip()
    street = full
    for tail in (pin, state, city):  # keep the address line short: city/state/pincode have their own boxes
        if tail:
            street = re.sub(r"[,\s]*" + re.escape(tail) + r"[,\s]*$", "", street, flags=re.I)
    legal, trade = str(data.get("lgnm") or "").strip(), str(data.get("tradeNam") or "").strip()
    return {"ok": True, "gstin": gstin, "pan": gstin[2:12], "name": trade or legal, "legal_name": legal, "trade_name": trade,
            "status": str(data.get("sts") or ""), "constitution": str(data.get("ctb") or ""), "registered_on": str(data.get("rgdt") or ""),
            "address": street.strip(" ,"), "city": city.title() if city.isupper() else city, "state": state, "pincode": pin}


def gst_details(user_id: int, gstin: str, captcha: str) -> dict:
    gstin = (gstin or "").strip().upper()
    if not GSTIN_RE.match(gstin):
        return {"ok": False, "message": "That GSTIN is not in a valid format."}
    if user_id not in _sessions:
        return {"ok": False, "captcha": True, "message": "The captcha expired. A new one has been loaded."}
    try:
        r = _sessions[user_id][0].post(DETAILS_URL, json={"gstin": gstin, "captcha": (captcha or "").strip()},
                                       headers={"Referer": SEARCH_PAGE, "Content-Type": "application/json"}, timeout=25)
        data = r.json()
    except requests.RequestException:
        return {"ok": False, "captcha": True, "message": "Could not reach the GST portal. Try again."}
    except ValueError:
        return {"ok": False, "captcha": True, "message": "The GST portal sent an unexpected reply. Try again."}
    _sessions.pop(user_id, None)  # a captcha works once
    if not isinstance(data, dict):
        return {"ok": False, "captcha": True, "message": "The GST portal sent an unexpected reply. Try again."}
    code, message = str(data.get("errorCode") or ""), str(data.get("message") or "")
    if code or (message and not data.get("lgnm") and not data.get("tradeNam")):
        low = message.lower()
        wrong = code == "SWEB_9000" or any(w in low for w in ("captcha", "letters shown", "characters shown", "enter valid"))
        return {"ok": False, "captcha": wrong, "message": "Wrong captcha. Type the new one." if wrong else (message or code or "No record found.")}
    return parse_taxpayer(gstin, data)


# ------------------------------------------------------------------ GST filing history (public "Search Taxpayer" page, captcha typed by the user)
RETURNS_URL = BASE + "/services/api/search/taxpayerReturnDetails"
_MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
                                       "november", "december"], start=1)}


def _flatten(node):
    if isinstance(node, dict):
        if any(k in node for k in ("rtntype", "rtnType")):
            yield node
        else:
            for v in node.values():
                yield from _flatten(v)
    elif isinstance(node, list):
        for v in node:
            yield from _flatten(v)


def parse_filings(data) -> list[dict]:
    """Portal reply -> [{'type','year','month','filed','arn','status'}]. Handles both 'fy + taxp' and 'ret_prd' (MMYYYY) styles."""
    from datetime import datetime

    out = []
    for row in _flatten(data):
        rtype = str(row.get("rtntype") or row.get("rtnType") or "").strip()
        year = month = None
        prd = str(row.get("ret_prd") or "").strip()
        if prd.isdigit() and len(prd) in (5, 6):
            prd = prd.zfill(6)
            month, year = int(prd[:2]), int(prd[2:])
        else:
            name = str(row.get("taxp") or "").strip().lower()
            fy = str(row.get("fy") or "").strip()
            m = _MONTHS.get(name)
            if m is None and name[:3]:
                m = next((i for k, i in _MONTHS.items() if k[:3] == name[-3:] or k[:3] == name[:3]), None) if name != "annual" else 3
            starts = re.findall(r"\d{4}", fy)
            if m and starts:
                month, year = m, int(starts[0]) + (1 if m <= 3 else 0)
        filed = None
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                filed = datetime.strptime(str(row.get("dof") or "").strip(), fmt).date()
                break
            except ValueError:
                pass
        if rtype and year and month and 1 <= month <= 12:
            out.append({"type": rtype, "year": year, "month": month, "filed": filed, "arn": str(row.get("arn") or "").strip(),
                        "status": str(row.get("status") or "").strip()})
    return out


def gst_filing_history(user_id: int, gstin: str, captcha: str) -> dict:
    """Validate the captcha with the normal search, then read the return-filing table shown on the same portal page."""
    first = gst_details_keep_session(user_id, gstin, captcha)
    if not first.get("ok"):
        return first
    s = first.pop("_session")
    try:
        r = s.post(RETURNS_URL, json={"gstin": first["gstin"]}, headers={"Referer": SEARCH_PAGE, "Content-Type": "application/json"}, timeout=25)
        data = r.json()
    except (requests.RequestException, ValueError):
        return {"ok": False, "captcha": True, "message": "The GST portal did not return the filing table. Try again in a minute."}
    finally:
        _sessions.pop(user_id, None)
    rows = parse_filings(data)
    if not rows:
        return {"ok": False, "captcha": True, "message": "The GST portal returned no filing history for this GSTIN."}
    return {"ok": True, "gstin": first["gstin"], "rows": rows, "status": first.get("status", "")}


def gst_details_keep_session(user_id: int, gstin: str, captcha: str) -> dict:
    kept = _sessions.get(user_id)
    out = gst_details(user_id, gstin, captcha)
    if out.get("ok") and kept:
        out["_session"] = kept[0]
    elif out.get("ok"):
        return {"ok": False, "captcha": True, "message": "The captcha expired. A new one has been loaded."}
    return out


def save_filings(client, rows: list[dict]) -> dict:
    """Write portal rows into the GST tracker as Filed. Existing rows are updated, never duplicated."""
    from ..models import GstReturn, GstReturnType, db
    from . import compliance as comp

    types = {re.sub(r"[^A-Z0-9]", "", t.name.upper()): t for t in GstReturnType.query.all()}
    result = {"created": 0, "updated": 0, "skipped": 0, "unknown_types": set()}
    for row in rows:
        state = row["status"].lower()
        if (state and not state.startswith("filed")) or (not state and not row["filed"]):  # "Not Filed", "To Be Filed" are not filings
            result["skipped"] += 1
            continue
        rt = types.get(re.sub(r"[^A-Z0-9]", "", row["type"].upper()))
        if rt is None:
            result["unknown_types"].add(row["type"])
            result["skipped"] += 1
            continue
        y, m = row["year"], row["month"]
        if rt.frequency == "monthly":
            period = f"{y}-{m:02d}"
        elif rt.frequency == "quarterly":
            period = f"{y}-Q{(m - 1) // 3 + 1}"
        else:
            start = y if m >= 4 else y - 1
            period = f"{start}-{str(start + 1)[2:]}"
        obj = GstReturn.query.filter_by(client_id=client.id, return_type_id=rt.id, period=period).first()
        if obj is None:
            obj = GstReturn(client_id=client.id, return_type_id=rt.id, period=period, assigned_to_id=client.assigned_to_id,
                            due_date=comp.gst_due_date(rt, period))
            db.session.add(obj)
            result["created"] += 1
        else:
            result["updated"] += 1
        obj.status, obj.filed_date, obj.arn = "filed", row["filed"] or obj.filed_date, row["arn"] or obj.arn
    result["unknown_types"] = sorted(result["unknown_types"])
    return result
