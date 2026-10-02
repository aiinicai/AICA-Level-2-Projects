"""
Mutual-fund CAS reader: turns a CAMS / KFintech Consolidated Account Statement (detailed, PDF) into proposed
mutual-fund transactions for review. Nothing here saves anything; confirmed rows go through ledger.add_txns.

A detailed CAS checks itself, and every check is applied rather than trusted:
  * each transaction line prints amount, units, NAV and the unit balance after it: units x NAV must equal the
    amount, and previous balance + units must equal the printed balance (a misread line breaks the chain);
  * each folio prints its opening and closing unit balance: the chain must end on the closing balance;
  * the scheme is identified by its ISIN against the AMFI Growth-option ISINs of the schemes the app tracks, so the
    plan (Direct / Regular) is exact and an IDCW option is never taken for the Growth option;
  * every NAV is compared with the scheme's month-end NAVs either side of the date.
Stamp duty is part of the purchase cost and is added to it (the recorded price is amount incl. stamp duty / units);
STT and TDS on redemptions are not deducted (STT is not deductible for capital gains).
"""
import hashlib
import re
from datetime import datetime

from contract_note import NUM_RE, ContractNoteError, _num, read_text

DATE_RE = re.compile(r"^(\d{2}-[A-Za-z]{3}-\d{4})\b")
ISIN_RE = re.compile(r"\bINF[A-Z0-9]{8}\d\b")
PERIOD_RE = re.compile(r"(\d{2}-[A-Za-z]{3}-\d{4})\s+(?:To|to|-)\s+(\d{2}-[A-Za-z]{3}-\d{4})")
FOLIO_RE = re.compile(r"Folio\s*No\.?\s*[:\-]?\s*([0-9][0-9A-Za-z]*(?:\s*/\s*[0-9A-Za-z]+)?)", re.I)
OPEN_RE = re.compile(r"Opening\s+Unit\s+Balance\s*[:\-]?\s*(\(?-?[\d,]+\.?\d*\)?)", re.I)
CLOSE_RE = re.compile(r"Closing\s+Unit\s+Balance\s*[:\-]?\s*(\(?-?[\d,]+\.?\d*\)?)", re.I)
CHARGE_RE = re.compile(r"stamp\s+duty|\bstt\b|securities\s+transaction\s+tax|\btds\b", re.I)
NAV_TOLERANCE = 0.25
PASSWORD_HINT = "Enter the password you chose when requesting the CAS from CAMS or KFintech (NSDL/CDSL statements use the PAN in capitals)."

SELL_WORDS = re.compile(r"redemption|redeem|switch[\s\-]*out|stp[\s\-]*out|swp|systematic\s+withdrawal|transfer[\s\-]*out|lateral\s+shift\s+out", re.I)
SIP_WORDS = re.compile(r"systematic\s+investment|\bsip\b", re.I)
BUY_WORDS = re.compile(r"purchase|switch[\s\-]*in|stp[\s\-]*in|systematic\s+transfer|reinvest|additional|transfer[\s\-]*in|lateral\s+shift\s+in", re.I)


class CasError(ContractNoteError):
    """The file cannot be read as a CAS; shown to the user as-is."""


def _d(s):
    return datetime.strptime(s, "%d-%b-%Y").date().isoformat()


def _nums(s):
    return [_num(x) for x in NUM_RE.findall(s) if x.strip("()-")]


def _scheme_index(schemes):
    idx = {}
    for s in schemes:
        if s.get("isin_direct"):
            idx[s["isin_direct"]] = (s["scheme_id"], "Direct")
        if s.get("isin_regular"):
            idx[s["isin_regular"]] = (s["scheme_id"], "Regular")
    return idx


def _classify(desc, units):
    if SELL_WORDS.search(desc):
        return "Sell", None
    if SIP_WORDS.search(desc):
        return "SIP", None
    if BUY_WORDS.search(desc):
        return "Purchase", None
    return ("Sell" if units < 0 else "Purchase"), "Transaction type not recognised from the description; inferred from the sign of the units."


def parse(data, password="", schemes=(), as_on=None, ref_navs=None):
    """Preview of a detailed CAS. `ref_navs(scheme_id, plan, iso_date)` -> month-end NAVs either side of the date."""
    text = "\n".join(read_text(data, password, what="CAS statement", hint=PASSWORD_HINT, err=CasError))
    lines = [" ".join(ln.split()) for ln in text.splitlines() if ln.strip()]
    idx = _scheme_index(schemes)
    warnings = []
    m = PERIOD_RE.search(text)
    period = (_d(m.group(1)), _d(m.group(2))) if m else (None, None)
    if not re.search(r"consolidated\s+account\s+statement|\bCAS\b", text, re.I):
        warnings.append("The file does not call itself a Consolidated Account Statement; check that it is one.")

    folios, cur, folio_no, prev_line = [], None, None, ""
    for ln in lines:
        fm = FOLIO_RE.search(ln)
        if fm:
            folio_no = " ".join(fm.group(1).split())
        im = ISIN_RE.search(ln)
        if im and not DATE_RE.match(ln):
            name = re.split(r"\(?\s*Advisor|ISIN|Registrar", ln[:im.start()], flags=re.I)[0].strip(" -:(")
            if len(name) < 8:  # CAMS prints the scheme name on the line above the ISIN line
                name = re.split(r"\(?\s*Advisor|Registrar", prev_line, flags=re.I)[0].strip(" -:(")
            name = re.sub(r"^[A-Z0-9]{2,10}-", "", name).strip()
            sid, plan = idx.get(im.group(0), (None, None))
            cur = {"folio": folio_no, "isin": im.group(0), "name": name, "scheme_id": sid, "plan": plan, "opening": None, "closing": None,
                   "txns": [], "issues": []}
            folios.append(cur)
            prev_line = ln
            continue
        prev_line = ln
        if cur is None:
            continue
        om = OPEN_RE.search(ln)
        if om:
            cur["opening"] = abs(_num(om.group(1)))
            continue
        cm = CLOSE_RE.search(ln)
        if cm:
            cur["closing"] = _num(cm.group(1))
            continue
        dm = DATE_RE.match(ln)
        if not dm:
            continue
        rest = ln[dm.end():]
        nums = _nums(rest)
        spans = [m.start() for m in NUM_RE.finditer(rest) if m.group(0).strip("()-")]
        # the description is the text before the trailing figures (amount, units, NAV, balance); numbers inside it stay
        desc = rest[:spans[-4]] if len(spans) >= 4 else NUM_RE.sub(" ", rest)
        desc = " ".join(re.sub(r"[*]+", " ", desc).split())
        if CHARGE_RE.search(rest) and len(nums) <= 1:
            kind = "stamp" if re.search(r"stamp", rest, re.I) else "tax"
            if cur["txns"] and cur["txns"][-1]["date"] == _d(dm.group(1)) and nums:
                cur["txns"][-1]["charges"][kind] = round(cur["txns"][-1]["charges"].get(kind, 0) + abs(nums[0]), 2)
            continue
        if len(nums) < 4:
            if nums:
                cur["issues"].append(f"{dm.group(1)} '{desc[:60]}' has no units and NAV on the line; not imported (bonus, merger or a note line?).")
            continue
        amount, units, nav, balance = nums[-4:]
        typ, why = _classify(desc, units)
        issues = [why] if why else []
        if typ == "Sell" and units > 0 or typ != "Sell" and units < 0:
            issues.append("The description and the sign of the units disagree.")
        if nav <= 0 or abs(abs(units) * nav - abs(amount)) > 0.0006 * nav + 0.02:
            issues.append(f"Units x NAV ({abs(units) * nav:,.2f}) does not equal the amount ({abs(amount):,.2f}).")
        cur["txns"].append({"date": _d(dm.group(1)), "description": desc[:90], "txn_type": typ, "amount": round(abs(amount), 2),
                            "units": round(abs(units), 3), "signed_units": units, "nav": nav, "balance": balance, "charges": {}, "issues": issues})

    if not folios:
        raise CasError("No mutual-fund folios were found. This does not look like a CAMS or KFintech CAS; for an NSDL/CDSL statement, "
                       "request the CAS from CAMS or KFintech instead (it lists every transaction).")
    if not any(f["txns"] for f in folios):
        raise CasError("The statement lists holdings but no transactions: it is a summary CAS. Request the DETAILED statement "
                       "(transactions for the period) from CAMS or KFintech.")

    n_ok = 0
    for f in folios:
        bal = f["opening"] or 0.0
        chain_ok = True
        for t in f["txns"]:
            bal = round(bal + t["signed_units"], 3)
            if abs(bal - t["balance"]) > 0.002:
                t["issues"].append(f"Unit balance does not follow: expected {bal:,.3f}, statement shows {t['balance']:,.3f}.")
                chain_ok = False
                bal = t["balance"]
        if f["closing"] is not None and abs(bal - f["closing"]) > 0.002:
            f["issues"].append(f"Transactions end at {bal:,.3f} units but the closing balance is {f['closing']:,.3f}.")
            chain_ok = False
        if f["closing"] is None:
            f["issues"].append("Closing unit balance not found; the folio could not be reconciled.")
            chain_ok = False
        f["reconciled"] = chain_ok
        n_ok += chain_ok
        if f["opening"]:
            f["issues"].append(f"Opening balance {f['opening']:,.3f} units: purchases before {period[0] or 'the statement period'} are not in this "
                               "statement. Record them first (or use a CAS from inception), or sales may exceed the units held and cost will be incomplete.")
        if not f["scheme_id"]:
            f["issues"].append("This scheme is not one of the schemes the app tracks (matched by ISIN, Growth option), so it cannot be recorded.")
        for t in f["txns"]:
            buy = t["txn_type"] != "Sell"
            t["price_with_charges"] = round((t["amount"] + (t["charges"].get("stamp", 0) if buy else 0)) / t["units"], 4) if t["units"] else None
            if f["scheme_id"] and ref_navs:
                refs = [p for p in ref_navs(f["scheme_id"], f["plan"], t["date"]) if p]
                if refs and all(abs(t["nav"] / p - 1) > NAV_TOLERANCE for p in refs):
                    near = min(refs, key=lambda p: abs(t["nav"] / p - 1))
                    t["issues"].append(f"NAV {t['nav']:,.4f} is {abs(t['nav'] / near - 1):.0%} away from the month-end NAV {near:,.4f} of the matched scheme; check the scheme and plan.")
            if as_on and t["date"] > as_on:
                t["issues"].append(f"After the valuation date {as_on}; refresh the data first.")
            t.pop("signed_units")
    return {"sha256": hashlib.sha256(data).hexdigest(), "period": {"from": period[0], "to": period[1]}, "folios": folios,
            "summary": {"folios": len(folios), "tracked": sum(1 for f in folios if f["scheme_id"]), "reconciled": n_ok,
                        "transactions": sum(len(f["txns"]) for f in folios)},
            "warnings": warnings}
