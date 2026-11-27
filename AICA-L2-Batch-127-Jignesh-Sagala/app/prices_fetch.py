"""Price fetch. A SEPARATE backend script: the dashboard never calls the internet, it only reads prices.csv.
This script adds today's prices to prices.csv from public sources:

    mutual fund NAV   AMFI daily file  (by ISIN)                    source = amfi
    shares            Yahoo Finance chart data (NSE: SYMBOL.NS)     source = yahoo   (unofficial, may change)
    USD/INR           Frankfurter (European Central Bank rates)     source = fx
    commodities       Yahoo symbols such as GC=F, SI=F              source = yahoo   (USD per ounce)

Usage (from the project folder, on the laptop that has internet):
    py -m app.prices_fetch  path\\to\\database_folder          add today's prices
    py -m app.prices_fetch  path\\to\\database_folder --dry-run  show what would be added, change nothing

Which key reads from where is in the database folder's price_sources.csv (key,source,code).
A fund with no row is read from AMFI using its key as the ISIN. A share with no row is read from Yahoo as key.NS.

Fund NAVs are published once a day by the fund houses. They are not real time. Share prices from Yahoo may be
delayed. Month-end history is built by running this script on each month end; the file is never rewritten, only
added to, and a (date, key) pair is never added twice.

The dummy database is protected: the script refuses to write into a folder whose name contains "dummy"
(real prices would be mixed with invented numbers). Use --force only if you mean it.
"""
import csv
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5d&interval=1d"
FX_URL = "https://api.frankfurter.app/latest?from={base}&to=INR"
UA = {"User-Agent": "Mozilla/5.0 (price-fetch for personal dashboard)"}


# ---------------------------------------------------------------- parsers (pure, tested offline)
def parse_amfi(text):
    """AMFI NAVAll.txt -> {isin: (nav, 'YYYY-MM-DD')}. Lines: code;ISIN payout;ISIN reinvest;name;NAV;date."""
    out = {}
    for line in text.splitlines():
        p = [x.strip() for x in line.split(";")]
        if len(p) < 6 or not p[0].isdigit():
            continue
        try:
            nav = float(p[4].replace(",", ""))
            dt = datetime.strptime(p[5], "%d-%b-%Y").date().isoformat()
        except ValueError:
            continue
        for isin in (p[1], p[2]):
            if isin and isin != "-":
                out[isin] = (nav, dt)
    return out


def parse_yahoo(payload):
    """Yahoo chart JSON -> (price, 'YYYY-MM-DD') of the last valid close."""
    res = json.loads(payload)["chart"]["result"][0]
    ts = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    for t, c in zip(reversed(ts), reversed(closes)):
        if c is not None:
            off = res.get("meta", {}).get("gmtoffset", 0)
            return float(c), datetime.utcfromtimestamp(t + off).date().isoformat()
    raise ValueError("no close price in the answer")


def parse_fx(payload):
    """Frankfurter JSON -> (rate, 'YYYY-MM-DD')."""
    j = json.loads(payload)
    return float(j["rates"]["INR"]), j["date"]


# ---------------------------------------------------------------- network
def get(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def plan(folder):
    """List of (key, source, code) to fetch for the database folder."""
    folder = Path(folder)
    ins = read_csv(folder / "instruments.csv")
    src = {r["key"]: (r["source"], r["code"]) for r in read_csv(folder / "price_sources.csv")} if (folder / "price_sources.csv").exists() else {}
    held = {r["key"] for r in read_csv(folder / "transactions.csv")}
    out = []
    for r in ins:
        if r["key"] not in held:
            continue
        s, c = src.get(r["key"], ("amfi", r["key"]) if r["kind"] == "MF" else ("yahoo", r["key"] + ".NS"))
        out.append((r["key"], s, c))
    for k, (s, c) in src.items():
        if s == "fx":
            out.append((k, s, c))
    if not any(k == "USDINR" for k, _, _ in out):
        ccys = {r["currency"] for r in read_csv(folder / "bank_balances.csv")} | {r["currency"] for r in read_csv(folder / "fixed_deposits.csv")}
        if "USD" in ccys:
            out.append(("USDINR", "fx", "USD"))
    return out


def fetch_all(items, fetch=get):
    """-> (rows [(date,key,price)], problems [text])."""
    rows, problems = [], []
    amfi = None
    for key, s, c in items:
        try:
            if s == "amfi":
                if amfi is None:
                    amfi = parse_amfi(fetch(AMFI_URL, 90))
                nav, dt = amfi[c]
            elif s == "yahoo":
                nav, dt = parse_yahoo(fetch(YAHOO_URL.format(sym=urllib.parse.quote(c))))
            elif s == "fx":
                nav, dt = parse_fx(fetch(FX_URL.format(base=c)))
            else:
                raise ValueError(f"unknown source {s}")
            rows.append((dt, key, nav))
        except Exception as e:  # one failure must not stop the others
            problems.append(f"{key} ({s} {c}): {type(e).__name__}: {e}")
    return rows, problems


def add_rows(folder, rows):
    """Append rows not yet in prices.csv. Returns the rows really added."""
    p = Path(folder) / "prices.csv"
    have = {(r["date"], r["key"]) for r in read_csv(p)}
    new = [r for r in rows if (r[0], r[1]) not in have]
    if new:
        with open(p, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for dt, k, v in sorted(new):
                w.writerow([dt, k, f"{v:.4f}" if k.startswith("INF") or k == "USDINR" else f"{v:.2f}"])
    return new


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 1
    folder, dry, force = Path(argv[0]), "--dry-run" in argv, "--force" in argv
    if "dummy" in folder.name.lower() and not force and not dry:
        print("Refused: this is the dummy database. Real prices must not be mixed into it. (Use --force only if you mean it.)")
        return 2
    items = plan(folder)
    print(f"{len(items)} prices to fetch")
    rows, problems = fetch_all(items)
    print(f"fetched {len(rows)}, failed {len(problems)}")
    for t in problems:
        print("  FAILED", t)
    if dry:
        for r in rows[:10]:
            print("  would add", r)
        print("dry run: nothing written")
        return 0
    new = add_rows(folder, rows)
    print(f"added {len(new)} new rows to {folder / 'prices.csv'} ({len(rows) - len(new)} already there)")
    return 0 if not problems else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
