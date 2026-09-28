"""
Entities and transactions entered in the app: persistent storage, validation and audit trail.

Storage: data/user/ledger.json (atomic writes, previous version kept as ledger.json.bak) and
data/user/audit.jsonl (append-only: who, what, when, before and after). LOOKTHROUGH_USER_DIR
redirects both, so tests never touch the real files.

Rules enforced here, server-side (the browser is never trusted):
  * entity: name 2-80 characters, a known entity type; an entity with transactions cannot be deleted
  * transaction: known entity; a listed company or configured scheme that has a price/NAV on the
    valuation date (otherwise it could not be valued); units and price > 0 (whole shares for equity);
    date on or before the valuation date; amount = units x price, computed here, not taken from the client
  * no sale may exceed the units held at that date - checked across ALL transactions (demo and user)
    after every add, edit or delete, so an edit cannot leave a later sale uncovered
The demo family (data/config/family.json) is read-only; it can be switched off entirely.
"""
import json
import os
import re
import threading
from datetime import date
from pathlib import Path

from common import DATA, load_json, now_iso, save_json

USER_DIR = Path(os.environ.get("LOOKTHROUGH_USER_DIR") or DATA / "user")
LEDGER = USER_DIR / "ledger.json"
AUDIT = USER_DIR / "audit.jsonl"
ENTITY_TYPES = ("Individual", "HUF", "LLP", "Company", "Partnership firm", "Trust")
TXN_TYPES = {"EQ": ("Buy", "Sell"), "MF": ("Purchase", "SIP", "Sell")}
PLANS = ("Direct", "Regular")
_LOCK = threading.RLock()


# Schemes a user may add. Equity-oriented only: the tax view applies listed-equity rules (12-month holding, LTCG
# exemption) to every fund, and look-through assumes an equity portfolio. Debt, liquid, gold, international and
# fund-of-funds schemes are taxed differently (specified mutual funds at slab rates) and hedged categories
# (arbitrage, balanced advantage) would be overstated by look-through, so they are refused, not mis-modelled.
SCHEME_CATEGORIES = ("Large Cap", "Large & Mid Cap", "Mid Cap", "Small Cap", "Multi Cap", "Flexi Cap", "Focused", "Value", "Contra",
                     "Dividend Yield", "Sectoral / Thematic", "ELSS", "Index Fund", "Aggressive Hybrid")
BENCHMARKS = ("NIFTY50", "NIFTY500", "NIFTYMID", "NIFTYSMALL", "NIFTYBANK", "HYBRID")
NOT_EQUITY = re.compile(r"liquid|overnight|money market|debt|bond|gilt|duration|credit risk|banking and psu|banking & psu|floater|"
                        r"fixed maturity|\bfmp\b|gold|silver|commodit|fund of funds|\bfof\b|overseas|international|global|nasdaq|"
                        r"\bus\b|arbitrage|balanced advantage|dynamic asset|conservative hybrid|equity savings|multi asset|"
                        r"retirement|children|solution oriented|\betf\b", re.I)
MIN_NAV_MONTHS = 13
MIN_PRICE_MONTHS = 13  # the build drops a stock with fewer month-end prices, so it could not be valued
SECTORS = ("Automobile", "Capital Goods", "Chemicals", "Construction Materials", "Consumer Durables", "Consumer Services", "FMCG",
           "Financial Services", "Healthcare", "Information Technology", "Metals & Mining", "Oil, Gas & Energy", "Power", "Realty",
           "Services", "Telecommunication", "Others")


class LedgerError(ValueError):
    """A business-rule violation: shown to the user, nothing is saved."""


def load():
    d = load_json(LEDGER) or {}
    d.setdefault("members", [])
    d.setdefault("transactions", [])
    d.setdefault("seq", {"member": 0, "txn": 0})
    d["seq"].setdefault("scheme", 0)
    d.setdefault("schemes", [])
    d.setdefault("companies", [])
    d.setdefault("settings", {"include_demo_family": True})
    return d


def _save(d):
    USER_DIR.mkdir(parents=True, exist_ok=True)
    if LEDGER.exists():
        LEDGER.with_suffix(".json.bak").write_bytes(LEDGER.read_bytes())
    save_json(LEDGER, d, indent=1)


def audit(user, action, before=None, after=None, detail=""):
    USER_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": now_iso(), "user": user, "action": action, "before": before, "after": after, "detail": detail},
                           ensure_ascii=False, default=str) + "\n")


def read_audit(limit=500):
    if not AUDIT.exists():
        return []
    lines = AUDIT.read_text(encoding="utf-8").splitlines()[-limit:]
    return [json.loads(x) for x in reversed(lines) if x.strip()]


# ------------------------------------------------------------------ entities
def _clean_member(data):
    name = " ".join(str(data.get("name") or "").split())
    if not 2 <= len(name) <= 80:
        raise LedgerError("Entity name must be 2 to 80 characters.")
    typ = data.get("type")
    if typ not in ENTITY_TYPES:
        raise LedgerError(f"Entity type must be one of: {', '.join(ENTITY_TYPES)}.")
    rel = " ".join(str(data.get("relationship") or "").split())[:60]
    return {"name": name, "type": typ, "relationship": rel}


def all_member_ids(led, demo_members):
    return {m["member_id"] for m in led["members"]} | {m["member_id"] for m in (demo_members if led["settings"]["include_demo_family"] else [])}


def add_member(data, user, demo_members):
    with _LOCK:
        led = load()
        m = _clean_member(data)
        taken = {x["name"].lower() for x in led["members"]} | {x["name"].lower() for x in demo_members}
        if m["name"].lower() in taken:
            raise LedgerError(f"An entity named {m['name']!r} already exists.")
        used = [int(x["member_id"][1:]) for x in led["members"] + list(demo_members) if x["member_id"][1:].isdigit()]
        n = max(used + [led["seq"]["member"]]) + 1
        m = {"member_id": f"M{n}", **m, "created_by": user, "created_at": now_iso()}
        led["members"].append(m)
        led["seq"]["member"] = n
        _save(led)
        audit(user, "ENTITY_ADD", None, m)
        return m


def update_member(member_id, data, user):
    with _LOCK:
        led = load()
        cur = next((x for x in led["members"] if x["member_id"] == member_id), None)
        if not cur:
            raise LedgerError(f"{member_id} is not an entity you added (demo entities are read-only).")
        new = {**cur, **_clean_member(data), "updated_by": user, "updated_at": now_iso()}
        led["members"] = [new if x["member_id"] == member_id else x for x in led["members"]]
        _save(led)
        audit(user, "ENTITY_EDIT", cur, new)
        return new


def delete_member(member_id, user):
    with _LOCK:
        led = load()
        cur = next((x for x in led["members"] if x["member_id"] == member_id), None)
        if not cur:
            raise LedgerError(f"{member_id} is not an entity you added (demo entities are read-only).")
        n = sum(t["member_id"] == member_id for t in led["transactions"])
        if n:
            raise LedgerError(f"{cur['name']} has {n} transaction(s). Delete those first; entities with history are never deleted silently.")
        led["members"] = [x for x in led["members"] if x["member_id"] != member_id]
        _save(led)
        audit(user, "ENTITY_DELETE", cur, None)


# ------------------------------------------------------------------ transactions
def _num(v, what):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise LedgerError(f"{what} must be a number.") from None
    if not x > 0 or x != x or x == float("inf"):
        raise LedgerError(f"{what} must be greater than zero.")
    return x


def _priced(ds, asset, inst, plan):
    """Is the instrument known and valued on the valuation date?"""
    as_on = ds["meta"]["as_on"]
    if asset == "EQ":
        if not any(c["code"] == inst for c in ds["companies"]):
            return False, f"{inst} is not in the security master. Add it under Data & controls > Securities first."
        ok = any(p["code"] == inst and p["date"] == as_on for p in ds["prices"])
        return ok, f"{inst} has no price on the valuation date {as_on}, so it cannot be valued."
    if not any(s["scheme_id"] == inst for s in ds["schemes"]):
        return False, f"{inst} is not a configured scheme."
    ok = any(n["scheme_id"] == inst and n["plan"] == plan and n["date"] == as_on for n in ds["nav_history"])
    return ok, f"{inst} {plan} plan has no NAV on the valuation date {as_on}."


def _clean_txn(data, ds, member_ids):
    asset = data.get("asset_type")
    if asset not in TXN_TYPES:
        raise LedgerError("Asset type must be EQ (listed equity) or MF (mutual fund).")
    member = data.get("member_id")
    if member not in member_ids:
        raise LedgerError(f"Unknown entity {member!r}.")
    inst = str(data.get("instrument") or "").strip().upper()
    plan = data.get("plan") if asset == "MF" else ""
    if asset == "MF" and plan not in PLANS:
        raise LedgerError("Plan must be Direct or Regular for a mutual fund.")
    typ = data.get("txn_type")
    if typ not in TXN_TYPES[asset]:
        raise LedgerError(f"Transaction type for {asset} must be one of: {', '.join(TXN_TYPES[asset])}.")
    try:
        d = date.fromisoformat(str(data.get("date")))
    except ValueError:
        raise LedgerError("Date must be YYYY-MM-DD.") from None
    as_on = ds["meta"]["as_on"]
    if d.isoformat() > as_on:
        raise LedgerError(f"Date is after the valuation date {as_on}. Refresh the data first to record later transactions.")
    if d.year < 2000:
        raise LedgerError("Date is too early.")
    units = _num(data.get("units"), "Units")
    if asset == "EQ" and units != int(units):
        raise LedgerError("Equity units must be whole shares.")
    price = _num(data.get("price"), "Price")
    ok, why = _priced(ds, asset, inst, plan)
    if not ok:
        raise LedgerError(why)
    units = int(units) if asset == "EQ" else round(units, 3)
    note = " ".join(str(data.get("note") or "").split())[:120]
    return {"date": d.isoformat(), "member_id": member, "asset_type": asset, "instrument": inst, "plan": plan, "txn_type": typ,
            "units": units, "price": round(price, 4), "amount": round(units * price, 2), "note": note}


def oversold(txns):
    """Transactions (ids) where cumulative units for an entity/instrument/plan go negative, in date order.
    Same-day purchases are counted before same-day sales."""
    bal, bad = {}, []
    for t in sorted(txns, key=lambda x: (x["date"], x["txn_type"] == "Sell")):
        k = (t["member_id"], t["instrument"], t["plan"])
        bal[k] = bal.get(k, 0) + (-t["units"] if t["txn_type"] == "Sell" else t["units"])
        if bal[k] < -1e-6:
            bad.append(t.get("txn_id") or "(new)")
    return bad


def _commit_txns(led, ds, new_user_txns, user, action, before, after):
    demo = [t for t in ds["transactions"] if not str(t.get("txn_id", "")).startswith("U")] if led["settings"]["include_demo_family"] else []
    bad = oversold(demo + new_user_txns)
    if bad:
        raise LedgerError(f"This would leave a sale larger than the units held ({', '.join(bad[:5])}). Nothing was saved.")
    led["transactions"] = new_user_txns
    _save(led)
    audit(user, action, before, after)


def add_txn(data, user, ds):
    with _LOCK:
        led = load()
        t = _clean_txn(data, ds, all_member_ids(led, ds["members_demo"]))
        led["seq"]["txn"] += 1
        t = {"txn_id": f"U{led['seq']['txn']:05d}", **t, "created_by": user, "created_at": now_iso()}
        _commit_txns(led, ds, led["transactions"] + [t], user, "TXN_ADD", None, t)
        return t


def txn_key(t):
    """Identity of a transaction for duplicate detection across overlapping statements."""
    return (t["member_id"], t["instrument"], t.get("plan") or "", t["date"], t["txn_type"] == "Sell", round(float(t["units"]), 3))


def add_txns(rows, user, ds, ref, kind="contract_note"):
    """Record several transactions at once, from a contract note (equity) or a CAS (mutual funds): all are validated,
    and either all are saved or none is.
    contract_note: ref = {"sha256", "contract_note_no", "file"}; the same note (by file hash) cannot be imported twice.
    cas:           ref = {"sha256", "file"}; statements overlap, so each row is refused if the same transaction
                   (entity, scheme, plan, date, direction, units) is already recorded, rather than the whole file."""
    if kind not in ("contract_note", "cas"):
        raise LedgerError("Unknown import type.")
    what = "contract note" if kind == "contract_note" else "CAS statement"
    if not isinstance(rows, list) or not rows:
        raise LedgerError("Nothing to record: select at least one transaction.")
    if len(rows) > 500:
        raise LedgerError("Too many transactions in one import (limit 500).")
    sha = str((ref or {}).get("sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise LedgerError(f"The import reference is missing; read the {what} again.")
    note_no = " ".join(str((ref or {}).get("contract_note_no") or "").split())[:40]
    with _LOCK:
        led = load()
        if kind == "contract_note":
            dup = next((t for t in led["transactions"] if t.get("import_sha256") == sha), None)
            if dup:
                raise LedgerError(f"This contract note was already imported ({dup['txn_id']} and others). Nothing was saved.")
        demo = [t for t in ds["transactions"] if not str(t.get("txn_id", "")).startswith("U")] if led["settings"]["include_demo_family"] else []
        seen = {txn_key(t): t["txn_id"] for t in demo + led["transactions"]}
        ids = all_member_ids(led, ds["members_demo"])
        new = []
        for i, r in enumerate(rows, 1):
            if kind == "contract_note":
                fixed = {"asset_type": "EQ", "note": f"Contract note {note_no}".strip() if note_no else "Contract note import"}
            else:
                folio = " ".join(str(r.get("folio") or "").split())[:30]
                fixed = {"asset_type": "MF", "note": f"CAS, folio {folio}" if folio else "CAS import"}
            try:
                t = _clean_txn({**r, **fixed}, ds, ids)
            except LedgerError as e:
                raise LedgerError(f"Row {i} ({r.get('instrument') or 'unidentified'}): {e} Nothing was saved.") from None
            if kind == "cas" and txn_key(t) in seen:
                raise LedgerError(f"Row {i} ({t['instrument']} {t['plan']} {t['date']}, {t['units']} units) is already recorded as "
                                  f"{seen[txn_key(t)]}. Untick it and record the rest. Nothing was saved.")
            seen[txn_key(t)] = "(this import)"
            led["seq"]["txn"] += 1
            new.append({"txn_id": f"U{led['seq']['txn']:05d}", **t, "import_sha256": sha, "created_by": user, "created_at": now_iso()})
        _commit_txns(led, ds, led["transactions"] + new, user, "TXN_IMPORT", None,
                     {"source": what, "contract_note_no": note_no or None, "file": str((ref or {}).get("file") or "")[:120] or None,
                      "sha256": sha, "rows": len(new), "txn_ids": [t["txn_id"] for t in new]})
        return new


def _scheme_code_row(navall, code, plan):
    r = next((x for x in navall if x["code"] == str(code or "").strip()), None)
    if not r:
        raise LedgerError(f"AMFI code {code} is not in AMFI's current scheme list.")
    n = r["name"].lower()
    if "growth" not in n or re.search(r"idcw|dividend|bonus|payout|reinvest|segregated", n):
        raise LedgerError(f"AMFI code {code} is not a Growth option ({r['name']}). Choose the Growth option: IDCW options pay out and are valued differently.")
    if (plan == "Direct") != ("direct" in n):
        raise LedgerError(f"AMFI code {code} is not the {plan} plan ({r['name']}).")
    return r


def add_scheme(data, user, config_schemes, navall, nav_months):
    """Add a mutual-fund scheme the user wants to track. `nav_months(code)` = month-end NAVs available for that code
    in the app's 37-month window (fetches the history). Codes are checked against AMFI's current list."""
    with _LOCK:
        led = load()
        d = _scheme_code_row(navall, data.get("amfi_code_direct"), "Direct")
        rg = _scheme_code_row(navall, data.get("amfi_code_regular"), "Regular") if str(data.get("amfi_code_regular") or "").strip() else None
        if rg and rg["amc"] != d["amc"]:
            raise LedgerError("The Direct and Regular codes belong to different fund houses.")
        if NOT_EQUITY.search(d["name"]):
            raise LedgerError(f"{d['name']} does not look like an equity-oriented scheme. The app's tax and look-through model "
                              "equity-oriented funds only; debt, liquid, gold, international, fund-of-funds and hedged (arbitrage, "
                              "balanced advantage) schemes are taxed or exposed differently and are not supported yet.")
        cat, bm = data.get("category"), data.get("benchmark")
        if cat not in SCHEME_CATEGORIES:
            raise LedgerError("Choose an equity-oriented category from the list.")
        if bm not in BENCHMARKS:
            raise LedgerError("Choose a benchmark from the list.")
        name = " ".join(str(data.get("name") or "").split())
        if not 3 <= len(name) <= 80:
            raise LedgerError("Enter the scheme name (3 to 80 characters).")
        all_s = list(config_schemes) + led["schemes"]
        for x in all_s:
            codes = {str(x.get("amfi_code_direct") or ""), str(x.get("amfi_code_regular") or "")}
            if d["code"] in codes or (rg and rg["code"] in codes):
                raise LedgerError(f"This scheme is already tracked as {x['scheme_id']} ({x['name']}).")
            if x["name"].lower() == name.lower():
                raise LedgerError(f"A scheme named {name!r} already exists ({x['scheme_id']}).")
        n = nav_months(d["code"])
        if n < MIN_NAV_MONTHS:
            raise LedgerError(f"{d['name']} has {n} month-end NAVs in the app's 3-year window; at least {MIN_NAV_MONTHS} are needed "
                              "(returns and risk use 12 monthly returns). It cannot be added yet.")
        used = [int(x["scheme_id"][1:]) for x in all_s if str(x["scheme_id"])[1:].isdigit()]
        k = max(used + [led["seq"]["scheme"]]) + 1
        rec = {"scheme_id": f"S{k:02d}", "name": name, "amc": d["amc"], "category": cat, "benchmark": bm,
               "amfi_code_direct": d["code"], "amfi_code_regular": rg["code"] if rg else None,
               "amfi_name_direct": d["name"], "amfi_name_regular": rg["name"] if rg else None,
               "match_any": [], "exclude": [], "amfi_code_basis": f"Chosen from AMFI NAVAll.txt by {user} on {now_iso()[:10]}",
               "created_by": user, "created_at": now_iso()}
        led["schemes"].append(rec)
        led["seq"]["scheme"] = k
        _save(led)
        audit(user, "SCHEME_ADD", None, {x: rec[x] for x in ("scheme_id", "name", "category", "benchmark", "amfi_code_direct", "amfi_code_regular")})
        return rec


def update_scheme(scheme_id, data, user):
    """Only the display name, category and benchmark of a scheme the user added can change (never its AMFI codes)."""
    with _LOCK:
        led = load()
        cur = next((x for x in led["schemes"] if x["scheme_id"] == scheme_id), None)
        if not cur:
            raise LedgerError(f"{scheme_id} is not a scheme you added (the configured schemes are read-only).")
        new = dict(cur)
        if data.get("name") is not None:
            new["name"] = " ".join(str(data["name"]).split())
            if not 3 <= len(new["name"]) <= 80:
                raise LedgerError("Enter the scheme name (3 to 80 characters).")
        if data.get("category") is not None:
            if data["category"] not in SCHEME_CATEGORIES:
                raise LedgerError("Choose an equity-oriented category from the list.")
            new["category"] = data["category"]
        if data.get("benchmark") is not None:
            if data["benchmark"] not in BENCHMARKS:
                raise LedgerError("Choose a benchmark from the list.")
            new["benchmark"] = data["benchmark"]
        new.update(updated_by=user, updated_at=now_iso())
        led["schemes"] = [new if x["scheme_id"] == scheme_id else x for x in led["schemes"]]
        _save(led)
        audit(user, "SCHEME_EDIT", {k: cur[k] for k in ("name", "category", "benchmark")}, {k: new[k] for k in ("name", "category", "benchmark")})
        return new


def delete_scheme(scheme_id, user):
    with _LOCK:
        led = load()
        cur = next((x for x in led["schemes"] if x["scheme_id"] == scheme_id), None)
        if not cur:
            raise LedgerError(f"{scheme_id} is not a scheme you added (the configured schemes are read-only).")
        used = [t["txn_id"] for t in led["transactions"] if t["instrument"] == scheme_id]
        if used:
            raise LedgerError(f"{scheme_id} has {len(used)} transaction(s) ({', '.join(used[:3])}{'…' if len(used) > 3 else ''}); delete them first.")
        led["schemes"] = [x for x in led["schemes"] if x["scheme_id"] != scheme_id]
        _save(led)
        audit(user, "SCHEME_DELETE", {k: cur[k] for k in ("scheme_id", "name", "amfi_code_direct")}, None)


def add_company(rec, user):
    """Record a listed company the user added. `rec` has been checked by the bridge against NSE's list and Yahoo prices
    (symbol, name, isin, sector, industry, has_fin); here only the ledger rules are applied."""
    with _LOCK:
        led = load()
        sym = str(rec.get("symbol") or "").upper()
        if not re.fullmatch(r"[A-Z0-9&\-]{1,20}", sym):
            raise LedgerError("Symbol has unexpected characters.")
        if any(c["symbol"] == sym for c in led["companies"]):
            raise LedgerError(f"{sym} has already been added.")
        if rec.get("sector") not in SECTORS:
            raise LedgerError("Choose a sector from the list.")
        new = {"symbol": sym, "name": " ".join(str(rec.get("name") or sym).split())[:100], "isin": rec.get("isin") or "",
               "sector": rec["sector"], "industry": str(rec.get("industry") or "")[:80], "has_fin": bool(rec.get("has_fin")),
               "created_by": user, "created_at": now_iso()}
        led["companies"].append(new)
        _save(led)
        audit(user, "COMPANY_ADD", None, {k: new[k] for k in ("symbol", "name", "isin", "sector", "has_fin")})
        return new


def update_company(symbol, data, user):
    """Only the sector of a company the user added can change (it drives the sector limit)."""
    with _LOCK:
        led = load()
        cur = next((c for c in led["companies"] if c["symbol"] == symbol), None)
        if not cur:
            raise LedgerError(f"{symbol} is not a company you added (the research universe and fund holdings are read-only).")
        if data.get("sector") not in SECTORS:
            raise LedgerError("Choose a sector from the list.")
        new = {**cur, "sector": data["sector"], "updated_by": user, "updated_at": now_iso()}
        led["companies"] = [new if c["symbol"] == symbol else c for c in led["companies"]]
        _save(led)
        audit(user, "COMPANY_EDIT", {"symbol": symbol, "sector": cur["sector"]}, {"symbol": symbol, "sector": new["sector"]})
        return new


def delete_company(symbol, user):
    with _LOCK:
        led = load()
        cur = next((c for c in led["companies"] if c["symbol"] == symbol), None)
        if not cur:
            raise LedgerError(f"{symbol} is not a company you added (the research universe and fund holdings are read-only).")
        used = [t["txn_id"] for t in led["transactions"] if t["asset_type"] == "EQ" and t["instrument"] == symbol]
        if used:
            raise LedgerError(f"{symbol} has {len(used)} transaction(s) ({', '.join(used[:3])}{'…' if len(used) > 3 else ''}); delete them first.")
        led["companies"] = [c for c in led["companies"] if c["symbol"] != symbol]
        _save(led)
        audit(user, "COMPANY_DELETE", {k: cur[k] for k in ("symbol", "name", "isin")}, None)


def update_txn(txn_id, data, user, ds):
    with _LOCK:
        led = load()
        cur = next((x for x in led["transactions"] if x["txn_id"] == txn_id), None)
        if not cur:
            raise LedgerError(f"{txn_id} is not a transaction you entered (demo transactions are read-only).")
        new = {"txn_id": txn_id, **_clean_txn(data, ds, all_member_ids(led, ds["members_demo"])),
               **({"import_sha256": cur["import_sha256"]} if cur.get("import_sha256") else {}),
               "created_by": cur.get("created_by"), "created_at": cur.get("created_at"), "updated_by": user, "updated_at": now_iso()}
        _commit_txns(led, ds, [new if x["txn_id"] == txn_id else x for x in led["transactions"]], user, "TXN_EDIT", cur, new)
        return new


def delete_txn(txn_id, user, ds):
    with _LOCK:
        led = load()
        cur = next((x for x in led["transactions"] if x["txn_id"] == txn_id), None)
        if not cur:
            raise LedgerError(f"{txn_id} is not a transaction you entered (demo transactions are read-only).")
        _commit_txns(led, ds, [x for x in led["transactions"] if x["txn_id"] != txn_id], user, "TXN_DELETE", cur, None)


def set_demo(include, user, ds):
    with _LOCK:
        led = load()
        before = led["settings"]["include_demo_family"]
        if not include:
            demo_ids = {m["member_id"] for m in ds["members_demo"]}
            used = sorted({t["member_id"] for t in led["transactions"] if t["member_id"] in demo_ids})
            if used:
                raise LedgerError(f"Your transactions use demo entities ({', '.join(used)}); move or delete them before hiding the demo family.")
        led["settings"]["include_demo_family"] = bool(include)
        _save(led)
        audit(user, "SETTING_DEMO_FAMILY", before, bool(include))
