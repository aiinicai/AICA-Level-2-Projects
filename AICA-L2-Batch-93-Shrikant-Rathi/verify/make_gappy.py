"""
Edge-case fixture: takes a complete dataset and removes data the way real
sources fail, so the reconciliation also proves both engines agree on gaps.
    python make_gappy.py <dataset.json> <out_dir>   ->  out_dir/dataset.json + out_dir/LookThrough.html
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bridge"))
src, out = Path(sys.argv[1]), Path(sys.argv[2])
d = json.loads(src.read_text())
D = d["meta"]["dates"]
notes = []

# 1. No AMC file for S05 (held) -> its value is "not looked through"
d["scheme_portfolios"] = [r for r in d["scheme_portfolios"] if r["scheme_id"] != "S05"]
notes.append("S05 portfolio removed (unmapped fund)")
# 2. S06 has only the latest month -> no activity
last = max(r["portfolio_date"] for r in d["scheme_portfolios"])
d["scheme_portfolios"] = [r for r in d["scheme_portfolios"] if not (r["scheme_id"] == "S06" and r["portfolio_date"] != last)]
notes.append("S06 previous month removed")
# 3. Recent listings: DIXON 20 months of history (beta computed, no 3Y CAGR), KPITTECH 10 months (no beta -> 1.0)
for code, keep in (("DIXON", 20), ("KPITTECH", 10)):
    d["prices"] = [r for r in d["prices"] if not (r["code"] == code and r["date"] < D[-keep])]
notes.append("DIXON/KPITTECH short price history")
# 4. A scattered missing price month
d["prices"] = [r for r in d["prices"] if not (r["code"] == "ITC" and r["date"] in (D[20], D[21]))]
# 5. S08 NAV starts 14 months ago; S09 Regular NAV missing 12 months back -> no implied gap
d["nav_history"] = [r for r in d["nav_history"] if not (r["scheme_id"] == "S08" and r["date"] < D[-15])]
d["nav_history"] = [r for r in d["nav_history"] if not (r["scheme_id"] == "S09" and r["plan"] == "Regular" and r["date"] == D[-13])]
# 6. Mid-cap benchmark missing -> S07/S08 fall back to the market index
d["indices"] = [r for r in d["indices"] if r["index_code"] != "NIFTYMID"]
notes.append("NIFTYMID index removed")
# 7. TER now known for every scheme -> weighted TER computed
for i, s in enumerate(d["schemes"]):
    s["ter_direct"], s["ter_regular"] = round(0.4 + 0.05 * i, 2), round(1.3 + 0.07 * i, 2)
# 8. Financials: TCS only 2 years (no F-score / CAGR); INFY missing CFO & capex; a loss year for DLF
tcs = sorted([r for r in d["financials"] if r["code"] == "TCS"], key=lambda r: r["fy"])
keep = {r["fy"] for r in tcs[-2:]}
d["financials"] = [r for r in d["financials"] if r["code"] != "TCS" or r["fy"] in keep]
for r in d["financials"]:
    if r["code"] == "INFY":
        r["cfo"] = r["capex"] = None
dl = sorted([r for r in d["financials"] if r["code"] == "DLF"], key=lambda r: r["fy"])
if dl:
    dl[-1]["pat"] = -abs(dl[-1]["pat"] or 100)
# 9. Company with no price at all but held directly? keep holdings intact; a missing market cap instead
for c in d["companies"]:
    if c["code"] == "POLYCAB":
        c["mcap_cr"] = None
d["meta"]["warnings"] = d["meta"].get("warnings", []) + ["TEST FIXTURE: " + "; ".join(notes)]
out.mkdir(parents=True, exist_ok=True)
(out / "dataset.json").write_text(json.dumps(d))
import build_dataset  # noqa: E402
build_dataset.APP_OUT = out / "LookThrough.html"
build_dataset.build_app(d)
print("gappy fixture written to", out)
