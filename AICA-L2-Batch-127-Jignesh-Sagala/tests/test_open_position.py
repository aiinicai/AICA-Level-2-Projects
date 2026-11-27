"""Tests for the opening-cost back-solve (app/open_position.py), on made-up numbers only.
Run:  python tests/test_open_position.py
"""
import sys
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import open_position as op  # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


def case(u0, c0, trades):
    """final units and Zerodha-style average price from a known opening, then ask solve() to find the opening back."""
    units, cost = op.simulate(trades, u0, c0)
    return units, cost / units


T1 = [("B", D(50), D(60)), ("S", D(30), D(70)), ("B", D(20), D(40))]
units, avg = case(100, 5000, T1)
r = op.solve(T1, units, avg, method="avg")
check("opening 100 units, cost 5000: solved units equal", r["u0"] == 100)
check("opening 100 units, cost 5000: solved cost equals planted", abs(r["c0"] - 5000) < D("1e-9") and r["status"] == "SOLVED", str(r))

T2 = [("B", D(10), D(100)), ("B", D(10), D(120))]
units, avg = case(0, 0, T2)
r = op.solve(T2, units, avg, method="avg")
check("no opening: pass when cost equals Zerodha average", r["status"] == "NO_OPENING_PASS")
r = op.solve(T2, units, avg * D("1.2"), method="avg")
check("no opening: fails when Zerodha average is 20% off", r["status"] == "NO_OPENING_FAIL")

T3 = [("S", D(100), D(50)), ("B", D(10), D(55))]
units, avg = case(100, 4000, T3)
r = op.solve(T3, units, avg, method="avg")
check("opening units all sold: no information, flagged", r["status"].startswith("NO_INFO") and r["c0"] is None)

r = op.solve([("B", D(20), D(10))], D(5), D(10))
check("net trades above holding: opening units negative, flagged", r["status"] == "FLAG_OPENING_UNITS_NEGATIVE")

units, avg = case(40, 1000, [("S", D(10), D(30))])
r = op.solve([("S", D(10), D(30))], units, avg, method="avg")
check("sale only: opening solved", abs(r["c0"] - 1000) < D("1e-9"))

r = op.solve([("S", D(50), D(30))], D(0) + 10, D(25))     # holding 10, sold 50 -> opening 60 then sale fits; cost solved
check("opening bigger than sale: no flag", r["status"] in ("SOLVED", "FLAG_OPENING_COST_NEGATIVE"))

# split: 51 units bought before a 10-for-1 split, holding 1150 afterwards
pre = [("B", D(1), D("76.29")), ("B", D(50), D("96.42"))]
post = op.apply_split(pre, 10)
check("split: units x10, price /10", sum(q for s, q, p in post) == 510 and post[0][2] == D("7.629"))
tot = D(1150) * D("8.592704")
r = op.solve(post, D(1150), D("8.592704"), method="avg")
check("split: opening units 640 and cost = total - trades", r["u0"] == 640 and abs(r["c0"] - (tot - (D("76.29") + D(50) * D("96.42")))) < D("0.0001"))

# FIFO (Zerodha average price) and same-day netting
F = [("B", D(10), D(100)), ("B", D(10), D(120)), ("S", D(10), D(130))]
u, c = op.simulate_fifo(F, 0, 0)
check("FIFO: sale takes the oldest lot, 10 units left at 120", u == 10 and c == 1200)
u, c = op.simulate(F, 0, 0)
check("average cost: same trades leave 10 units at 110 (differs from FIFO)", u == 10 and c == 1100)
r = op.solve(F, D(10), D(120), method="fifo")
check("FIFO: no opening, Zerodha average 120 passes", r["status"] == "NO_OPENING_PASS")
r = op.solve(F, D(10), D(120), method="avg")
check("average cost: same data fails against Zerodha 120", r["status"] == "NO_OPENING_FAIL")
FO = [("S", D(30), D(70)), ("B", D(50), D(60))]
u, c = op.simulate_fifo(FO, 100, 5000)
r = op.solve(FO, u, c / u, method="fifo")
check("FIFO: opening cost solved when opening units remain", abs(r["c0"] - 5000) < D("1e-9") and r["u0"] == 100, str(r))
n = op.net_intraday([("B", D(10), D(100)), ("S", D(10), D(105)), ("B", D(5), D(98))])
check("same-day buy and sell netted out: 5 units left at the day's average buy price", len(n) == 1 and n[0][0] == "B" and n[0][1] == 5 and abs(n[0][2] - (D(1000) + D(490)) / 15) < D("1e-9"), str(n))

print("\nALL PASSED" if not FAILS else f"\n{len(FAILS)} FAILED")
sys.exit(1 if FAILS else 0)
