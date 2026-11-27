"""Offline tests of the price script: the parsers on sample answers, the plan, and the safe append.
The live internet calls are NOT tested here (the build sandbox cannot reach those sites); the owner checks them
once on the laptop with:  py -m app.prices_fetch <folder> --dry-run
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import prices_fetch as PF  # noqa: E402

AMFI = """Open Ended Schemes(Equity Scheme - Large Cap Fund)
Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date

Test Mutual Fund
100001;INF000A00001;-;Test Large Cap Fund - Direct Growth;123.4567;24-Nov-2026
100002;-;INF000A00003;Test Liquid Fund;1,020.50;24-Nov-2026
100003;INF000A00004;-;Bad Row Fund;N.A.;24-Nov-2026
"""


def test_amfi():
    r = PF.parse_amfi(AMFI)
    assert r["INF000A00001"] == (123.4567, "2026-11-24") and r["INF000A00003"][1] == "2026-11-24"
    assert "INF000A00004" not in r          # NAV "N.A." skipped, no crash
    print("  AMFI: 2 ISINs read, header lines and N.A. row skipped")


def test_yahoo_fx():
    y = json.dumps({"chart": {"result": [{"meta": {"gmtoffset": 19800}, "timestamp": [1796000000, 1796086400, 1796172800],
                                          "indicators": {"quote": [{"close": [100.0, 101.5, None]}]}}]}})
    p, d = PF.parse_yahoo(y)
    assert p == 101.5 and len(d) == 10                 # last non-empty close
    r, d = PF.parse_fx(json.dumps({"amount": 1.0, "base": "USD", "date": "2026-11-24", "rates": {"INR": 87.12}}))
    assert r == 87.12 and d == "2026-11-24"
    print("  Yahoo: last valid close taken; FX: rate and date read")


def test_plan_and_append():
    d = Path(tempfile.mkdtemp()) / "real_db"
    shutil.copytree(ROOT / "db_dummy", d)
    items = PF.plan(d)
    kinds = {s for _, s, _ in items}
    assert kinds == {"amfi", "yahoo", "fx"} and sum(1 for _, s, _ in items if s == "fx") == 1, items
    before = len(PF.read_csv(d / "prices.csv"))
    fake = {PF.AMFI_URL: AMFI.replace("INF000A00001", "INF00D000001")}

    def fetch(url, timeout=30):
        if url in fake:
            return fake[url]
        if "yahoo" in url:
            raise OSError("no network")
        return json.dumps({"date": "2026-11-26", "rates": {"INR": 88.0}})
    rows, problems = PF.fetch_all(items, fetch)
    assert any(k == "INF00D000001" for _, k, _ in rows) and any(k == "USDINR" for _, k, _ in rows)
    assert len(problems) >= 26 and any("TCS" in x for x in problems)       # every share failed, others still read
    n1 = len(PF.add_rows(d, rows))
    n2 = len(PF.add_rows(d, rows))
    assert n1 == len(rows) and n2 == 0 and len(PF.read_csv(d / "prices.csv")) == before + n1
    print(f"  plan: {len(items)} prices; one failing source did not stop the rest; added {n1} rows, second run added {n2}")


def test_dummy_protected():
    assert PF.main([str(ROOT / "db_dummy")]) == 2
    print("  dummy folder refused")


if __name__ == "__main__":
    for f in (test_amfi, test_yahoo_fx, test_plan_and_append, test_dummy_protected):
        print(f.__name__)
        f()
    print("ALL PASS")
