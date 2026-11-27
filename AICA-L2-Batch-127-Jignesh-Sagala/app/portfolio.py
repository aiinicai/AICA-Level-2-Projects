"""Portfolio engine in plain Python. Reads the database folder (CSV tables) and answers:
what is each holding worth on a date, at what cost, and what are the data checks.

Used for two jobs:
  1. build-time data checks shown on the dashboard's "Data checks" tab
  2. the independent oracle the tests use to verify the numbers the browser shows
The browser has its own copy of the same rules in JavaScript (dashboard_template.html).

Rules
  Holdings on a date = OPENING + BUY + SIP up to the date, less SELL.
  Average cost       = total cost / total units. A SELL removes units at the average cost.
  Value on a date    = units on that date x latest price on or before that date.
  Deposit value      = principal + simple interest to the date; stops growing at maturity.
  Foreign currency   = amount x USDINR on or before the date.
"""
import csv
from datetime import date
from pathlib import Path

CLASSES = ["Mutual funds", "Equity shares", "Bank balances", "Term deposits"]


def d(s):
    return date.fromisoformat(s)


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load(folder):
    f = Path(folder)
    db = {
        "instruments": {r["key"]: r for r in read(f / "instruments.csv")},
        "tx": [dict(r, date=d(r["date"]), qty=float(r["qty"]), price=float(r["price"])) for r in read(f / "transactions.csv")],
        "bank": [dict(r, as_of=d(r["as_of"]), balance=float(r["balance"])) for r in read(f / "bank_balances.csv")],
        "fd": [dict(r, start=d(r["start"]), maturity=d(r["maturity"]), rate=float(r["rate_pct"]),
                    principal=float(r["principal"]) if r["principal"] else None,
                    current_value=float(r["current_value"])) for r in read(f / "fixed_deposits.csv")],
        "cash": [dict(r, as_of=d(r["as_of"]), cash=float(r["cash"])) for r in read(f / "broker_cash.csv")],
    }
    prices = {}
    for r in read(f / "prices.csv"):
        prices.setdefault(r["key"], []).append((d(r["date"]), float(r["price"])))
    for v in prices.values():
        v.sort()
    db["prices"] = prices
    db["latest"] = max(dt for v in prices.values() for dt, _ in v)
    db["tx"].sort(key=lambda t: t["date"])
    return db


def price_on(db, key, on):
    """(price, price_date) latest on or before `on`; (None, None) if there is none."""
    best = None
    for dt, p in db["prices"].get(key, []):
        if dt <= on:
            best = (p, dt)
        else:
            break
    return best if best else (None, None)


def fx_on(db, ccy, on):
    if ccy == "INR":
        return 1.0
    p, _ = price_on(db, ccy + "INR", on)
    return p


def position_series(db, account, key, upto=None):
    """Walk the transactions of one holding. Returns list of events with units and average cost after each."""
    qty = cost = 0.0
    out = []
    for t in db["tx"]:
        if t["account"] != account or t["key"] != key:
            continue
        if upto and t["date"] > upto:
            break
        if t["action"] == "SELL":
            avg = cost / qty if qty else 0.0
            cost -= t["qty"] * avg
            qty -= t["qty"]
        else:
            cost += t["qty"] * t["price"]
            qty += t["qty"]
        out.append(dict(date=t["date"], action=t["action"], qty=t["qty"], price=t["price"], units=qty, cost=cost,
                        avg=(cost / qty if qty > 1e-9 else 0.0)))
    return out


def lines(db, on):
    """Every holding on date `on` as a list of dicts (values in INR)."""
    res = []
    pairs = sorted({(t["account"], t["key"]) for t in db["tx"]})
    for account, key in pairs:
        ev = position_series(db, account, key, on)
        if not ev or ev[-1]["units"] <= 1e-9:
            continue
        ins = db["instruments"][key]
        p, pd_ = price_on(db, key, on)
        qty, cost = ev[-1]["units"], ev[-1]["cost"]
        res.append(dict(cls="Mutual funds" if ins["kind"] == "MF" else "Equity shares", account=account, key=key,
                        name=ins["name"], house=ins["house"] or None, group=ins["group"], ccy="INR", qty=qty,
                        cost=cost, value=qty * p, price=p, price_date=pd_, fx=1.0))
    seen = {}
    for r in db["bank"]:
        if r["as_of"] <= on:
            k = (r["bank"], r["account_last4"])
            if k not in seen or r["as_of"] >= seen[k]["as_of"]:
                seen[k] = r
    for (bank, l4), r in sorted(seen.items()):
        fx = fx_on(db, r["currency"], on)
        res.append(dict(cls="Bank balances", account=f"{bank} {r['kind']} XX{l4}", key=f"{bank}|{l4}",
                        name=f"{bank} {r['kind']} XX{l4}", house=bank, group=None, ccy=r["currency"], qty=None,
                        cost=r["balance"] * fx, value=r["balance"] * fx, price=None, price_date=r["as_of"], fx=fx,
                        local=r["balance"]))
    seen = {}
    for r in db["cash"]:
        if r["as_of"] <= on:
            k = (r["broker"], r["account"])
            if k not in seen or r["as_of"] >= seen[k]["as_of"]:
                seen[k] = r
    for (broker, acct), r in sorted(seen.items()):
        res.append(dict(cls="Bank balances", account=f"Demat {acct}", key=f"{broker}|{acct}",
                        name=f"{broker} cash {acct}", house=broker, group=None, ccy="INR", qty=None,
                        cost=r["cash"], value=r["cash"], price=None, price_date=r["as_of"], fx=1.0, local=r["cash"]))
    for r in db["fd"]:
        if r["start"] > on:
            continue
        fx = fx_on(db, r["currency"], on)
        end = min(on, r["maturity"])
        if r["principal"] is not None:
            local = r["principal"] * (1 + r["rate"] / 100 * (end - r["start"]).days / 365)
            cost_local = r["principal"]
        else:
            local = r["current_value"]
            cost_local = r["current_value"]
        res.append(dict(cls="Term deposits", account=f"{r['bank']} {r['kind']} XX{r['account_last4']}",
                        key=f"{r['bank']}|{r['account_last4']}|FD", name=f"{r['bank']} {r['kind']} XX{r['account_last4']}",
                        house=r["bank"], group=None, ccy=r["currency"], qty=None, cost=cost_local * fx,
                        value=local * fx, price=None, price_date=None, fx=fx, local=local, matured=r["maturity"] <= on,
                        maturity=r["maturity"]))
    return res


def totals(res):
    t = {c: dict(value=0.0, cost=0.0) for c in CLASSES}
    for x in res:
        t[x["cls"]]["value"] += x["value"]
        t[x["cls"]]["cost"] += x["cost"]
    t["ALL"] = dict(value=sum(t[c]["value"] for c in CLASSES), cost=sum(t[c]["cost"] for c in CLASSES))
    return t


def xirr(flows):
    """flows: list of (date, amount). Returns annual rate or None. Day count /365."""
    if not flows or not any(a < 0 for _, a in flows) or not any(a > 0 for _, a in flows):
        return None
    t0 = min(dt for dt, _ in flows)

    def npv(r):
        return sum(a / (1 + r) ** ((dt - t0).days / 365.0) for dt, a in flows)

    lo, hi = -0.99, 10.0
    flo, fhi = npv(lo), npv(hi)
    if flo * fhi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = npv(mid)
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def xirr_flows(db, on, kind="MF", accounts=None, keys=None, open_date=None):
    """Cash flows of the chosen holdings up to `on`. Opening units count as bought on the opening date at that
    day's price (their original purchase dates are not in the data)."""
    flows = []
    end = 0.0
    sel = {(t["account"], t["key"]) for t in db["tx"] if db["instruments"][t["key"]]["kind"] == kind
           and (accounts is None or t["account"] in accounts) and (keys is None or t["key"] in keys)}
    for account, key in sorted(sel):
        for t in db["tx"]:
            if t["account"] != account or t["key"] != key or t["date"] > on:
                continue
            if t["action"] == "OPENING":
                p, _ = price_on(db, key, t["date"])
                flows.append((t["date"], -t["qty"] * p))
            elif t["action"] == "SELL":
                flows.append((t["date"], t["qty"] * t["price"]))
            else:
                flows.append((t["date"], -t["qty"] * t["price"]))
        ev = position_series(db, account, key, on)
        if ev and ev[-1]["units"] > 1e-9:
            p, _ = price_on(db, key, on)
            end += ev[-1]["units"] * p
    if end:
        flows.append((on, end))
    return flows


def checks(db):
    """Data checks. Each: (name, passed, detail)."""
    out = []
    bad = [t for t in db["tx"] if t["key"] not in db["instruments"]]
    out.append(("Every transaction key exists in the instruments table", not bad, f"{len(bad)} unknown"))
    bad = [t for t in db["tx"] if t["action"] not in ("OPENING", "BUY", "SIP", "SELL") or t["qty"] <= 0 or t["price"] <= 0]
    out.append(("Every transaction has a valid action, units above zero, price above zero", not bad, f"{len(bad)} invalid"))
    neg = 0
    for account, key in {(t["account"], t["key"]) for t in db["tx"]}:
        if any(e["units"] < -1e-9 for e in position_series(db, account, key)):
            neg += 1
    out.append(("No sale takes units below zero", neg == 0, f"{neg} holdings go negative"))
    miss = set()
    for account, key in {(t["account"], t["key"]) for t in db["tx"]}:
        for t in db["tx"]:
            if t["account"] == account and t["key"] == key:
                if price_on(db, key, t["date"])[0] is None:
                    miss.add(key)
    out.append(("A price exists on or before every transaction date", not miss, f"{len(miss)} holdings without a price"))
    held = {k for (_, k) in {(t["account"], t["key"]) for t in db["tx"]}}
    nolatest = [k for k in held if price_on(db, k, db["latest"])[1] != db["latest"]]
    out.append(("Every holding has a price on the latest date", not nolatest, f"{len(nolatest)} on an older price"))
    usd = any(r["currency"] == "USD" for r in db["bank"]) or any(r["currency"] == "USD" for r in db["fd"])
    out.append(("USD/INR rate exists when a USD amount is held", (not usd) or "USDINR" in db["prices"],
                "rate present" if "USDINR" in db["prices"] else "missing"))
    bad = [r for r in db["fd"] if r["maturity"] <= r["start"]]
    out.append(("Every deposit matures after it starts", not bad, f"{len(bad)} wrong"))
    diff = 0
    n = 0
    for r in db["fd"]:
        if r["principal"] is not None:
            n += 1
            calc = r["principal"] * (1 + r["rate"] / 100 * (min(db["latest"], r["maturity"]) - r["start"]).days / 365)
            if abs(calc - r["current_value"]) > 0.01:
                diff += 1
    out.append(("Deposit value in file = principal plus simple interest to the latest date", diff == 0, f"{n} compared, {diff} differ"))
    return out
