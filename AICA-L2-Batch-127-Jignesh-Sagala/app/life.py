"""Owner, house property, rent, insurance and the calendar of cash commitments, in plain Python.

Read from the same database folder as the portfolio tables. A table that is missing gives an empty list, so a
database without a rented house or insurance still builds.

None of this is added to the consolidated total. Insurance cover is not an asset, and the house sits on its own page.

Used for two jobs:
  1. build-time data checks shown on the "Data checks" page
  2. the independent oracle the tests use to verify the calendar and the insurance figures the browser shows
The browser has its own copy of the same rules in JavaScript (app.js).

Calendar rules
  Window   = the 12 months after the latest data date (the day after, up to the same day a year later).
  SIP      = every SIP plan line, on its day of the month.
  Premium  = each policy on its due day, in every year from its first year to its last year.
             A policy with no first and last year (medical) runs every year.
  House tax and maintenance = each property on its due day (month-day) every year.
  Rent and deposit maturities are money coming in, so they are not commitments and are not listed.
"""
import calendar as _cal
import csv
from datetime import date
from pathlib import Path


def d(s):
    return date.fromisoformat(s)


def _read(path):
    p = Path(path)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(s):
    return float(s) if s not in ("", None) else None


def _int(s):
    return int(float(s)) if s not in ("", None) else None


def _date(s):
    return d(s) if s else None


def load(folder):
    f = Path(folder)
    owner = _read(f / "owner.csv")
    return {
        "owner": ({"name": owner[0]["name"], "pan": owner[0].get("pan", ""), "birth": d(owner[0]["birth_date"])} if owner else None),
        "sip": [dict(r, amount=float(r["amount"]), day=int(r["day"])) for r in _read(f / "sip_plan.csv")],
        "props": [dict(r, rent=float(r["rent_monthly"]), rent_day=int(r["rent_day"]), lease_start=d(r["lease_start"]),
                       lease_end=d(r["lease_end"]), tax=float(r["tax_yearly"]), tax_md=r["tax_due"],
                       tax_paid=_date(r["tax_last_paid"]), cost=_num(r["cost"]), value=_num(r["value"]),
                       value_date=_date(r["value_date"])) for r in _read(f / "properties.csv")],
        "rent": [dict(r, date=d(r["date"]), amount=float(r["amount"])) for r in _read(f / "rent_receipts.csv")],
        "ins": [dict(r, cover=_num(r["cover"]), premium=float(r["premium"]), first=_int(r["first_year"]),
                     last=_int(r["last_year"]), month=int(r["due_month"]), day=int(r["due_day"]),
                     payout=_num(r["payout_monthly"]), payout_day=_int(r["payout_day"]),
                     payout_start=_date(r["payout_start"]), payout_end=_date(r["payout_end"])) for r in _read(f / "insurance.csv")],
    }


def add_months(dt, n):
    m = dt.month - 1 + n
    y, m = dt.year + m // 12, m % 12 + 1
    return date(y, m, min(dt.day, _cal.monthrange(y, m)[1]))


def premium_dates(pol, lo, hi):
    """Premium due dates after lo and on or before hi."""
    out = []
    for y in range(lo.year, hi.year + 1):
        if (pol["first"] is not None and y < pol["first"]) or (pol["last"] is not None and y > pol["last"]):
            continue
        dt = date(y, pol["month"], pol["day"])
        if lo < dt <= hi:
            out.append(dt)
    return out


def premiums_paid(pol, on):
    """Number of premiums due up to and including `on`; None when the policy has no first year."""
    if pol["first"] is None:
        return None
    return len(premium_dates(pol, date(pol["first"] - 1, 12, 31), on))


def premiums_total(pol):
    if pol["first"] is None or pol["last"] is None:
        return None
    return pol["last"] - pol["first"] + 1


def tax_dates(prop, lo, hi):
    mm, dd = (int(x) for x in prop["tax_md"].split("-"))
    return [date(y, mm, dd) for y in range(lo.year, hi.year + 1) if lo < date(y, mm, dd) <= hi]


def calendar(life, latest, months=12, names=None):
    """Cash commitments in the `months` months after `latest`. Rows: (date, kind, label, amount), sorted."""
    hi = add_months(latest, months)
    ev = []
    y, m = latest.year, latest.month
    for _ in range(months + 2):
        for s in life["sip"]:
            dt = date(y, m, min(s["day"], _cal.monthrange(y, m)[1]))
            if latest < dt <= hi:
                ev.append((dt, "SIP", (names or {}).get(s["key"], s["key"]), s["amount"]))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    for p in life["ins"]:
        for dt in premium_dates(p, latest, hi):
            ev.append((dt, "Insurance", p["name"], p["premium"]))
    for p in life["props"]:
        for dt in tax_dates(p, latest, hi):
            ev.append((dt, "House tax and maintenance", p["name"] + ", " + p["city"], p["tax"]))
    return sorted(ev, key=lambda e: (e[0], e[1], e[2]))


def checks(life, db):
    """Data checks. Each: (name, passed, detail)."""
    out = []
    latest = db["latest"]
    if life["sip"]:
        ym = (latest.year, latest.month)
        got = {}
        for t in db["tx"]:
            if t["action"] == "SIP" and (t["date"].year, t["date"].month) == ym:
                got[t["key"]] = got.get(t["key"], 0) + t["qty"] * t["price"]
        plan = {s["key"]: s["amount"] for s in life["sip"]}
        ok = set(got) == set(plan) and all(abs(got[k] - plan[k]) <= 1 for k in plan)
        out.append(("SIP plan = the SIPs in the latest month", ok,
                    f"{len(plan)} funds, plan {sum(plan.values()):,.0f}, statement {sum(got.values()):,.0f}"))
    for p in life["props"]:
        months = (latest.year - p["lease_start"].year) * 12 + latest.month - p["lease_start"].month + (
            1 if latest.day >= p["rent_day"] else 0)
        mine = [r for r in life["rent"] if r["property"] == p["id"]]
        ok = len(mine) == months and all(abs(r["amount"] - p["rent"]) < 0.5 for r in mine)
        out.append((f"Rent received for every month of the lease ({p['name']})", ok, f"{len(mine)} receipts, {months} due"))
        out.append((f"Lease runs forward and ends after it starts ({p['name']})", p["lease_start"] < p["lease_end"] and p["lease_end"] >= latest,
                    f"ends {p['lease_end'].isoformat()}"))
    if life["owner"]:
        for p in life["ins"]:
            if p["payout"] is not None:
                end = date(life["owner"]["birth"].year + 85, life["owner"]["birth"].month, life["owner"]["birth"].day)
                ok = p["payout_end"] < end and add_months(p["payout_end"], 1) >= end and p["payout_start"] > date(p["last"], p["month"], p["day"])
                n = (p["payout_end"].year - p["payout_start"].year) * 12 + p["payout_end"].month - p["payout_start"].month + 1
                out.append((f"Retirement income starts after the last premium and ends before age 85 ({p['name']})", ok, f"{n} payments"))
    return out
