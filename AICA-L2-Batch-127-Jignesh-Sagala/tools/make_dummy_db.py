"""Makes the DUMMY database used by the dashboard: db_dummy/*.csv

Real company, fund-house and bank names for realism. EVERY NUMBER IS INVENTED
(prices, units, balances, rates). Seeded: same files every run.

Tables (same layout the private, real data set must follow):
  instruments.csv    key,name,kind,group,house,currency
  transactions.csv   date,account,key,action,qty,price
  prices.csv         date,key,price             (USDINR rows hold the exchange rate)
  bank_balances.csv  bank,account_last4,kind,currency,as_of,balance
  fixed_deposits.csv bank,account_last4,kind,start,maturity,currency,rate_pct,principal,current_value
  broker_cash.csv    broker,account,as_of,cash
  price_sources.csv  key,source,code     (read only by prices_fetch.py; funds with real ISINs need no row)
  sip_plan.csv       key,folio,amount,day    (the monthly SIP plan: 5 funds x INR 40,000 on the 5th)
  owner.csv          name,pan,birth_date   (PAN is made up)
  properties.csv     id,name,city,tenant,rent_monthly,rent_day,lease_start,lease_end,tax_yearly,tax_due,tax_last_paid,
                     cost,cost_date,value,value_date,rent_account
  rent_receipts.csv  date,property,amount
  insurance.csv      id,name,type,cover,cover_note,premium,first_year,last_year,due_month,due_day,
                     payout_monthly,payout_day,payout_start,payout_end
  (sip_plan, owner, properties, rent_receipts and insurance are read by app/life.py, not by the portfolio engine)

Rules baked into the data:
  action = OPENING | BUY | SIP | SELL
  price  = cost per unit/share. For shares it already includes brokerage.
"""
import csv
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

SEED = 127
SCALE = 4   # every money amount and every unit count is 4 times the first version; prices, rates and dates are unchanged
OPEN = date(2025, 12, 31)
LATEST = date(2026, 11, 25)
MONTH_ENDS = [date(2025, 12, 31), date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30),
              date(2026, 5, 31), date(2026, 6, 30), date(2026, 7, 31), date(2026, 8, 31), date(2026, 9, 30),
              date(2026, 10, 31)]
PRICE_DATES = MONTH_ENDS + [LATEST]

# key, name, sector, base price (invented), accounts
SHARES = [
    ("HDFCBANK", "HDFC Bank", "Banking", 1000), ("ICICIBANK", "ICICI Bank", "Banking", 1350),
    ("SBIN", "State Bank of India", "Banking", 850), ("AXISBANK", "Axis Bank", "Banking", 1150),
    ("BAJFINANCE", "Bajaj Finance", "Financial Services", 950),
    ("TCS", "Tata Consultancy Services", "IT", 3300), ("INFY", "Infosys", "IT", 1650),
    ("HCLTECH", "HCL Technologies", "IT", 1600),
    ("RELIANCE", "Reliance Industries", "Energy", 1450), ("ONGC", "Oil and Natural Gas Corporation", "Energy", 250),
    ("ITC", "ITC", "FMCG", 420), ("HINDUNILVR", "Hindustan Unilever", "FMCG", 2400),
    ("NESTLEIND", "Nestle India", "FMCG", 1200),
    ("SUNPHARMA", "Sun Pharmaceutical Industries", "Pharma", 1750), ("DRREDDY", "Dr. Reddy's Laboratories", "Pharma", 1250),
    ("CIPLA", "Cipla", "Pharma", 1500),
    ("MARUTI", "Maruti Suzuki India", "Auto", 12500), ("M&M", "Mahindra and Mahindra", "Auto", 3200),
    ("LT", "Larsen and Toubro", "Capital Goods", 3800),
    ("TITAN", "Titan Company", "Consumer Durables", 3600), ("ASIANPAINT", "Asian Paints", "Consumer Durables", 2400),
    ("TATASTEEL", "Tata Steel", "Metals", 170),
    ("POWERGRID", "Power Grid Corporation of India", "Power", 290), ("NTPC", "NTPC", "Power", 340),
    ("BHARTIARTL", "Bharti Airtel", "Telecom", 1950), ("ULTRACEMCO", "UltraTech Cement", "Cement", 11800),
]

# name, house, category, base NAV (invented)
FUNDS = [
    ("HDFC Flexi Cap Fund - Direct Growth", "HDFC Mutual Fund", "Flexi Cap", 1950),
    ("HDFC Mid-Cap Opportunities Fund - Direct Growth", "HDFC Mutual Fund", "Mid Cap", 210),
    ("HDFC Balanced Advantage Fund - Direct Growth", "HDFC Mutual Fund", "Hybrid", 520),
    ("SBI Large Cap Fund - Direct Growth", "SBI Mutual Fund", "Large Cap", 95),
    ("SBI Small Cap Fund - Direct Growth", "SBI Mutual Fund", "Small Cap", 190),
    ("ICICI Prudential Large Cap Fund - Direct Growth", "ICICI Prudential Mutual Fund", "Large Cap", 115),
    ("ICICI Prudential Value Discovery Fund - Direct Growth", "ICICI Prudential Mutual Fund", "Value", 480),
    ("ICICI Prudential Liquid Fund - Direct Growth", "ICICI Prudential Mutual Fund", "Liquid", 380),
    ("ICICI Prudential Corporate Bond Fund - Direct Growth", "ICICI Prudential Mutual Fund", "Debt", 31),
    ("Axis Large Cap Fund - Direct Growth", "Axis Mutual Fund", "Large Cap", 70),
    ("Axis Midcap Fund - Direct Growth", "Axis Mutual Fund", "Mid Cap", 105),
    ("Kotak Flexicap Fund - Direct Growth", "Kotak Mahindra Mutual Fund", "Flexi Cap", 90),
    ("Kotak Emerging Equity Fund - Direct Growth", "Kotak Mahindra Mutual Fund", "Mid Cap", 135),
    ("Nippon India Small Cap Fund - Direct Growth", "Nippon India Mutual Fund", "Small Cap", 175),
    ("Nippon India Large Cap Fund - Direct Growth", "Nippon India Mutual Fund", "Large Cap", 95),
    ("Parag Parikh Flexi Cap Fund - Direct Growth", "PPFAS Mutual Fund", "Flexi Cap", 85),
    ("Mirae Asset Large and Midcap Fund - Direct Growth", "Mirae Asset Mutual Fund", "Large and Mid Cap", 140),
    ("UTI Nifty 50 Index Fund - Direct Growth", "UTI Mutual Fund", "Index", 175),
    ("Motilal Oswal Midcap Fund - Direct Growth", "Motilal Oswal Mutual Fund", "Mid Cap", 105),
    ("Franklin India Flexi Cap Fund - Direct Growth", "Franklin Templeton Mutual Fund", "Flexi Cap", 330),
    ("Aditya Birla Sun Life Large Cap Fund - Direct Growth", "Aditya Birla Sun Life Mutual Fund", "Large Cap", 600),
    ("Tata Digital India Fund - Direct Growth", "Tata Mutual Fund", "Sectoral", 48),
]
NEW_FUNDS = {20, 21}          # no opening balance: first bought in 2026
SIP_FUNDS = {0, 5, 12, 15, 17}       # the SIP plan: 5 funds, INR 40,000 each, on the 5th = INR 2,00,000 a month
SIP_AMT = {i: 10000 * SCALE for i in SIP_FUNDS}
LUMPS = [(20, "2026-03-05", 60000), (21, "2026-04-06", 40000),      # the two newest funds: one-off purchases
         (2, "2026-03-12", 150000), (6, "2026-05-18", 200000), (10, "2026-06-24", 100000), (12, "2026-08-07", 120000),
         (16, "2026-09-15", 250000), (19, "2026-02-10", 100000)]
LUMPS = [(i, d, a * SCALE) for i, d, a in LUMPS]
REDEEMS = [(14, "2026-07-20", 0.20), (18, "2026-09-02", 0.15), (7, "2026-04-08", 0.30)]
AMC_CODE = {"HDFC Mutual Fund": "HDFC", "SBI Mutual Fund": "SBI", "ICICI Prudential Mutual Fund": "ICICI",
            "Axis Mutual Fund": "AXIS", "Kotak Mahindra Mutual Fund": "KOTAK", "Nippon India Mutual Fund": "NIPPON",
            "PPFAS Mutual Fund": "PPFAS", "Mirae Asset Mutual Fund": "MIRAE", "UTI Mutual Fund": "UTI",
            "Motilal Oswal Mutual Fund": "MOTILAL", "Franklin Templeton Mutual Fund": "FRANKLIN",
            "Aditya Birla Sun Life Mutual Fund": "ABSL", "Tata Mutual Fund": "TATA"}

BANKS = [  # bank, last4, kind, currency, start balance, monthly noise
    ("HDFC Bank", "1101", "NRE savings", "INR", 1450000, 180000),
    ("HDFC Bank", "1102", "NRO savings", "INR", 620000, 90000),
    ("ICICI Bank", "2201", "NRE savings", "INR", 880000, 120000),
    ("State Bank of India", "3301", "NRE savings", "INR", 340000, 60000),
    ("Federal Bank", "4401", "Foreign currency account", "USD", 18500, 2500),
]
FDS = [  # bank, last4, kind, start, maturity, ccy, rate, principal
    ("HDFC Bank", "5501", "NRE FD", "2024-12-10", "2026-12-10", "INR", 7.10, 2500000),
    ("ICICI Bank", "5502", "NRE FD", "2025-03-03", "2027-03-03", "INR", 6.90, 1500000),
    ("State Bank of India", "5503", "NRE FD", "2025-10-15", "2028-10-15", "INR", 6.80, 2000000),
    ("HDFC Bank", "5504", "NRO FD", "2025-06-20", "2027-06-20", "INR", 6.60, 1000000),
    ("ICICI Bank", "5505", "NRE FD", "2026-02-14", "2027-02-14", "INR", 7.00, 1800000),
    ("Federal Bank", "5506", "FCNR FD", "2025-10-01", "2027-10-01", "USD", 4.30, 40000),
    ("Federal Bank", "5507", "FCNR FD", "2026-04-20", "2029-04-20", "USD", 4.60, 25000),
    ("State Bank of India", "5508", "NRE FD", "2025-09-15", "2026-09-15", "INR", 6.60, 1200000),
]


def bdays(start, end):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def build_paths(keys_vol):
    """keys_vol: key -> (base, daily drift, daily sigma). Returns key -> {date: price}."""
    out = {}
    for key, (base, mu, sg) in keys_vol.items():
        rng = random.Random(f"{SEED}-{key}")
        p = base
        path = {}
        for d in bdays(date(2025, 11, 1), LATEST):
            p *= math.exp(mu + sg * rng.gauss(0, 1))
            path[d] = p
        # scale so that the price on the opening date is the base price
        k = base / path[date(2025, 12, 31)]
        out[key] = {d: v * k for d, v in path.items()}
    return out


def px(path, d):
    while d not in path:
        d -= timedelta(days=1)
    return path[d]


def bday_on_or_after(d):
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def accrued(principal, rate, start, d):
    days = max((d - start).days, 0)
    return principal * (1 + rate / 100 * days / 365)


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    # ---- instruments
    inst = []
    vol = {}
    for t, n, s, base in SHARES:
        inst.append([t, n, "SHARE", s, "", "INR"])
        vol[t] = (base, 0.0004, 0.014)
    fkeys = []
    for i, (n, h, c, base) in enumerate(FUNDS):
        k = f"INF00D{i + 1:06d}"
        fkeys.append(k)
        inst.append([k, n, "MF", c, h, "INR"])
        debt = c in ("Liquid", "Debt")
        vol[k] = (base, 0.00022 if debt else 0.0004, 0.0003 if c == "Liquid" else (0.0012 if c == "Debt" else 0.009))
    vol["USDINR"] = (86.0, 0.0001, 0.0018)
    paths = build_paths(vol)

    # ---- prices (month ends + latest)
    prices = []
    for k in vol:
        for d in PRICE_DATES:
            v = px(paths[k], d)
            prices.append([d.isoformat(), k, f"{v:.4f}" if k.startswith("INF") or k == "USDINR" else f"{v:.2f}"])
    prices.sort(key=lambda r: (r[0], r[1]))

    # ---- transactions
    tx = []
    demat = ["Demat ZD1234", "Demat ZD5678"]
    held_in = {}
    for idx, (t, n, s, base) in enumerate(SHARES):
        path = paths[t]
        has_open = idx % 4 != 3 and idx not in (24, 25)
        accts = [demat[idx % 2]] + ([demat[(idx + 1) % 2]] if idx in (0, 5, 8, 15) else [])
        if has_open:
            for a in accts:
                qty = SCALE * max(5, int(round(rng.uniform(150000, 600000) / base / 5.0)) * 5)
                cost = round(px(path, OPEN) * rng.uniform(0.80, 1.06), 2)
                tx.append([OPEN.isoformat(), a, t, "OPENING", qty, f"{cost:.2f}"])
                held_in[(a, t)] = qty
        nb = rng.choice([1, 2, 3]) if (idx % 3 != 0 or not has_open) else 0
        for _ in range(nb):
            a = rng.choice(accts)
            d = bday_on_or_after(date(2026, 1, 5) + timedelta(days=rng.randint(0, 320)))
            qty = SCALE * max(1, int(round(rng.uniform(80000, 300000) / base)))
            price = round(px(path, d) * 1.0004, 2)
            tx.append([d.isoformat(), a, t, "BUY", qty, f"{price:.2f}"])
            held_in[(a, t)] = held_in.get((a, t), 0) + qty
    # sells: five partial sells after the buys, on days after the position exists
    for t, mth in [("INFY", 4), ("ITC", 6), ("SBIN", 8), ("TATASTEEL", 5), ("HCLTECH", 9)]:
        cands = [(a, k) for (a, k) in held_in if k == t]
        a = cands[0][0]
        first = min(date.fromisoformat(r[0]) for r in tx if r[1] == a and r[2] == t)
        d = bday_on_or_after(max(date(2026, mth, 14), first + timedelta(days=20)))
        have = sum(r[4] if r[3] in ("OPENING", "BUY") else -r[4] for r in tx if r[1] == a and r[2] == t
                   and date.fromisoformat(r[0]) <= d)
        q = SCALE * max(1, int(have / SCALE * 0.3))
        tx.append([d.isoformat(), a, t, "SELL", q, f"{px(paths[t], d) * 0.9996:.2f}"])

    folio = {}
    for i, (n, h, c, base) in enumerate(FUNDS):
        code = AMC_CODE[h]
        folio.setdefault(h, f"Folio {code} {1000 + 17 * len(folio) + 451:04d}")
        a = folio[h]
        k = fkeys[i]
        path = paths[k]
        if i not in NEW_FUNDS:
            val = SCALE * rng.uniform(150000, 900000)
            nav0 = px(path, OPEN)
            units = round(val / SCALE / nav0, 3) * SCALE
            cost = round(nav0 * rng.uniform(0.70, 1.02), 4)
            tx.append([OPEN.isoformat(), a, k, "OPENING", f"{units:.3f}", f"{cost:.4f}"])
        if i in SIP_FUNDS:
            for m in range(1, 12):
                d = bday_on_or_after(date(2026, m, 5))
                nav = px(path, d)
                u = SCALE * round(SIP_AMT[i] / SCALE / nav, 3)      # units to 3 decimals, as on a statement
                tx.append([d.isoformat(), a, k, "SIP", f"{u:.3f}", f"{SIP_AMT[i] / u:.4f}"])   # price = amount / units, so units x price = the SIP amount
    for i, ds, amt in LUMPS:
        d = date.fromisoformat(ds)
        k = fkeys[i]
        nav = px(paths[k], d)
        tx.append([ds, folio[FUNDS[i][1]], k, "BUY", f"{SCALE * round(amt / SCALE / nav, 3):.3f}", f"{nav:.4f}"])
    for i, ds, frac in REDEEMS:
        d = date.fromisoformat(ds)
        k = fkeys[i]
        a = folio[FUNDS[i][1]]
        have = sum(float(r[4]) if r[3] != "SELL" else -float(r[4]) for r in tx
                   if r[1] == a and r[2] == k and date.fromisoformat(r[0]) <= d)
        tx.append([ds, a, k, "SELL", f"{SCALE * round(have / SCALE * frac, 3):.3f}", f"{px(paths[k], d):.4f}"])
    tx.sort(key=lambda r: (r[0], r[1], r[2], {"OPENING": 0, "BUY": 1, "SIP": 1, "SELL": 2}[r[3]]))

    # ---- bank balances (month ends + latest)
    bal = []
    for bank, l4, kind, ccy, start, noise in BANKS:
        b = float(start) * SCALE
        for d in PRICE_DATES:
            b = max(b + rng.uniform(-noise * SCALE, noise * SCALE * 1.3), noise * SCALE)
            bal.append([bank, l4, kind, ccy, d.isoformat(), f"{b:.2f}"])

    # ---- deposits
    fds = []
    for bank, l4, kind, s, m, ccy, r, p in FDS:
        p = p * SCALE
        sd, md = date.fromisoformat(s), date.fromisoformat(m)
        cv = accrued(p, r, sd, min(LATEST, md))
        fds.append([bank, l4, kind, s, m, ccy, f"{r:.2f}", f"{p:.2f}", f"{cv:.2f}"])

    # ---- broker cash
    cash = []
    for a, start in [("ZD1234", 185000.0), ("ZD5678", 64000.0)]:
        c = start * SCALE
        for d in PRICE_DATES:
            c = max(c + rng.uniform(-30000 * SCALE, 45000 * SCALE), 2000 * SCALE)
            cash.append(["Demo Broker", a, d.isoformat(), f"{c:.2f}"])

    # ---- SIP plan (the plan the transactions above follow)
    sip = [[fkeys[i], folio[FUNDS[i][1]], f"{SIP_AMT[i]:.0f}", 5] for i in sorted(SIP_FUNDS)]

    # ---- owner, house property, rent, insurance (every figure invented)
    owner = [["BusyMe", "ABCDE1234F", "1975-07-10"]]
    props = [["P1", "2-bedroom flat", "Ahmedabad", "Tenant A", 45000 * SCALE, 5, "2025-07-01", "2027-06-30", 35000 * SCALE, "04-30",
              "2026-04-24", 4500000 * SCALE, "2012-03-31", 7000000 * SCALE, LATEST.isoformat(), "HDFC Bank NRO savings 1102"]]
    rent = []
    y, m = 2025, 7
    while date(y, m, 5) <= LATEST:
        rent.append([date(y, m, 5).isoformat(), "P1", 45000 * SCALE])
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    ins = [["I1", "Term plan", "Term life", 100000000, "Life cover", 500000, 2024, 2033, 1, 15, "", "", "", ""],
           ["I2", "Medical policy", "Health", 20000000, "Family of 4, floater", 75000, "", "", 8, 1, "", "", "", ""],
           ["I3", "Retirement policy", "Retirement", "", "", 25000, 2015, 2035, 6, 10, 10000, 10, "2035-07-10", "2060-06-10"]]

    def w(name, header, rows):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            cw = csv.writer(f)
            cw.writerow(header)
            cw.writerows(rows)

    w("instruments.csv", ["key", "name", "kind", "group", "house", "currency"], inst)
    w("transactions.csv", ["date", "account", "key", "action", "qty", "price"], tx)
    w("prices.csv", ["date", "key", "price"], prices)
    w("bank_balances.csv", ["bank", "account_last4", "kind", "currency", "as_of", "balance"], bal)
    w("fixed_deposits.csv", ["bank", "account_last4", "kind", "start", "maturity", "currency", "rate_pct", "principal",
                             "current_value"], fds)
    w("broker_cash.csv", ["broker", "account", "as_of", "cash"], cash)
    w("price_sources.csv", ["key", "source", "code"], [[t, "yahoo", t + ".NS"] for t, *_ in SHARES] + [["USDINR", "fx", "USD"]])
    w("sip_plan.csv", ["key", "folio", "amount", "day"], sip)
    w("owner.csv", ["name", "pan", "birth_date"], owner)
    w("properties.csv", ["id", "name", "city", "tenant", "rent_monthly", "rent_day", "lease_start", "lease_end", "tax_yearly",
                         "tax_due", "tax_last_paid", "cost", "cost_date", "value", "value_date", "rent_account"], props)
    w("rent_receipts.csv", ["date", "property", "amount"], rent)
    w("insurance.csv", ["id", "name", "type", "cover", "cover_note", "premium", "first_year", "last_year", "due_month",
                        "due_day", "payout_monthly", "payout_day", "payout_start", "payout_end"], ins)
    print(f"instruments {len(inst)} (shares {len(SHARES)}, funds {len(FUNDS)}), transactions {len(tx)}, "
          f"prices {len(prices)}, bank rows {len(bal)}, deposits {len(fds)}, broker cash rows {len(cash)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "db_dummy")
