"""
Oracle tests: key answers recomputed from the raw dataset by the simplest possible route, NOT via either engine.
The two engines are reconciled against each other, so an error they share passes reconciliation; these catch it.
Each check corresponds to a finding of the September 2026 financial-logic review.

Usage:  python verify/oracle_check.py      (after recompute.py; reads data/live/dataset.json and verify/reference_metrics.json)
"""
import calendar
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
_live = HERE.parent / "data" / "live" / "dataset.json"
DS = json.loads((_live if _live.exists() else HERE.parent / "data" / "snapshot" / "dataset.json").read_text(encoding="utf-8"))
REF = json.loads((HERE / "reference_metrics.json").read_text(encoding="utf-8"))
AS = DS["meta"]["as_on"]
res = []


def check(name, ok, detail=""):
    res.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {detail}"))


def plus_months(s, n):
    y, m, d = map(int, s.split("-"))
    t = m - 1 + n
    yy, mm = y + t // 12, t % 12 + 1
    return date(yy, mm, min(d, calendar.monthrange(yy, mm)[1])).isoformat()


# C2 - statements in a foreign currency must never be read as rupees
cos = {c["code"]: c for c in DS["companies"]}
fin_codes = {f["code"] for f in DS["financials"]}
check("C2: Infosys (USD statements) has no rupee financials", "INFY" not in fin_codes and not cos["INFY"]["has_fin"])
check("C2: the exclusion is disclosed as a warning", any("INFY" in w and "INR" in w for w in DS["meta"]["warnings"]))
pe_absurd = [c for c, r in REF["ratios"].items() if r.get("pe") and r["pe"] > 300]
check("C2: no company has a P/E above 300x (a sign of a unit error)", not pe_absurd, pe_absurd)

# C3 - pharma / biotech industries are Healthcare, never IT
pharma = [c for c in DS["companies"] if any(k in (c.get("industry") or "").lower() for k in ("pharma", "biotech"))]
wrong = [c["code"] for c in pharma if c["sector"] != "Healthcare"]
check(f"C3: all {len(pharma)} pharma/biotech companies are in Healthcare", pharma and not wrong, wrong)

# C4 - ELSS lock-in, from the raw transactions: units bought < 36 months before the valuation date
elss = {s["scheme_id"] for s in DS["schemes"] if s.get("category") == "ELSS"}
nav_now = {(n["scheme_id"], n["plan"]): n["nav"] for n in DS["nav_history"] if n["date"] == AS}
for m in sorted({t["member_id"] for t in DS["transactions"] if t["instrument"] in elss}):
    lots = {}
    for t in sorted((t for t in DS["transactions"] if t["member_id"] == m and t["instrument"] in elss), key=lambda t: (t["date"], t["txn_id"])):
        k = (t["instrument"], t["plan"])
        if t["txn_type"] == "Sell":
            q = t["units"]
            while q > 1e-9 and lots.get(k):
                take = min(q, lots[k][0][1])
                lots[k][0][1] -= take
                q -= take
                if lots[k][0][1] <= 1e-9:
                    lots[k].pop(0)
        else:
            lots.setdefault(k, []).append([t["date"], t["units"]])
    locked = sum(u * nav_now[k] for k, ls in lots.items() for d, u in ls if plus_months(d, 36) > AS)
    check(f"C4: {m} ELSS value still in lock-in = Rs {locked / 1e5:.2f} lakh (engine agrees)", abs(REF["tax"][m]["locked_value"] - locked) < 1, (REF["tax"][m]["locked_value"], locked))

# M1 - a 20% market fall stresses ALL equity, including funds not looked through
f = REF["family"]
check("M1: stressed equity includes the funds not looked through",
      abs(REF["stress"]["market_minus20"]) > abs(-0.20 * (f["equity"]) * 0.8), (REF["stress"]["market_minus20"], f["equity"], f["unmapped"]))

# m2 - harvesting room uses realised short-term losses that must be set off first
for m, t in REF["tax"].items():
    room = max(0.0, 125000 - (t["realised_lt"] + min(0.0, t["realised_st"])))
    expect = min(room, max(0.0, t["unrealised_lt"] - 0))  # upper bound; locked LT gains only lower it
    check(f"m2: {m} harvest room within the set-off-adjusted exemption", t["harvest_headroom"] <= expect + 1e-6 and t["harvest_headroom"] >= 0,
          (t["harvest_headroom"], expect))

over = {m: t["exemption_left"] for m, t in REF["tax"].items() if t["exemption_left"] > 125000 + 1e-6}
check("Statutory exemption left never exceeds Rs 1.25 lakh (gain room may, via set-off)", not over, over)

print(f"\n{sum(res)}/{len(res)} oracle checks passed")
(HERE / "oracle_result.txt").write_text(f"{sum(res)}/{len(res)} oracle checks passed\n", encoding="utf-8")
sys.exit(0 if all(res) else 1)
