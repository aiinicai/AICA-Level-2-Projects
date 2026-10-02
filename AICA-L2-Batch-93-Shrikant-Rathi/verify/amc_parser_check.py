"""
Checks of the AMC portfolio parser on synthetic files (no network, no real data touched).

  * a normal one-scheme sheet is read as before;
  * a stacked all-scheme sheet (UTI's SEBI exposure format: every scheme in ONE sheet, each block opening with
    "SCHEME: <name>") is split into blocks; only the configured scheme is read, with its own holdings, weights and date;
  * a similar-named scheme (UTI Nifty 500 Value 50 Index Fund) is not taken for UTI Nifty 50 Index Fund.

Usage:  python verify/amc_parser_check.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bridge"))
import openpyxl  # noqa: E402

import amc_parser  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {detail}"))


SCHEMES = [{"scheme_id": "S03", "match_any": [["uti nifty 50 index"]]}, {"scheme_id": "S99", "match_any": [["example flexi cap"]]}]
HDR = ["NAME OF THE INSTRUMENT", "RATING/INDUSTRY", "QUANTITY", "MARKET-VALUE", "% TO NAV", None, None, "ISIN"]
# real ISINs with valid check digits (HDFC Bank, ICICI Bank, Reliance, Infosys, TCS)
ISINS = ["INE040A01034", "INE090A01021", "INE002A01018", "INE009A01021", "INE467B01029"]


def block(code, scheme, weights):
    rows = [[f"SCHEME CODE{code}STARTS"], ["UTI MUTUAL FUND"], [f"SCHEME: {scheme}"], ["PROVISIONAL AND UNAUDITED PORTFOLIO DISCLOSURE AS OF 31/08/2026"], [], HDR]
    rows += [[f"EQ - STOCK {i}", "Banks", 100, 1000, w, None, None, ISINS[i]] for i, w in enumerate(weights)]
    rows += [[f"TOTAL : {scheme}", None, None, None, round(sum(weights), 2)], []]
    return rows


tmp = Path(tempfile.mkdtemp(prefix="lt_amcp_"))
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "EXPOSURE"
for r in block("002", "UTI - Unit Linked Insurance Plan", [30, 30, 20]) + block("140", "UTI Nifty 500 Value 50 Index Fund", [40, 30, 29]) \
        + block("128", "UTI Nifty 50 Index Fund", [12.5, 10.25, 9.0, 8.0, 7.25]):
    ws.append(r)
wb.save(tmp / "UTI_2026-08.xlsx")
res = amc_parser.parse_file(tmp / "UTI_2026-08.xlsx", SCHEMES)
got = [r for r in res if r.get("scheme_id")]
check("Stacked sheet: exactly one block read, the configured scheme (S03), not its similar-named sibling",
      len(got) == 1 and got[0]["scheme_id"] == "S03", [(r.get("sheet"), r.get("scheme_id")) for r in res])
if got:
    g = got[0]
    check("Stacked sheet: the block's own holdings and weights (5 stocks, 47.0% listed), not the whole sheet",
          g["n"] == 5 and abs(g["listed_total_pct"] - 47.0) < 1e-9 and g["holdings"][0]["isin"] == "INE040A01034", (g["n"], g["listed_total_pct"]))
    check("Stacked sheet: the block's date (31 Aug 2026)", g["portfolio_date"] == "2026-08-31", g["portfolio_date"])
    check("Stacked sheet: the TOTAL line is not read as a holding", all(h["isin"].startswith("INE") for h in g["holdings"]))

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "EXFLEXI"
for r in [["Example Flexi Cap Fund"], ["Portfolio as on 31-Aug-2026"], [], ["Name of the Instrument", "ISIN", "Industry", "Quantity", "Market value", "% to Net Assets"],
          ["HDFC Bank", "INE040A01034", "Banks", 1, 1, 6.5], ["ICICI Bank", "INE090A01021", "Banks", 1, 1, 5.25]]:
    ws.append(r)
wb.save(tmp / "S99_2026-08.xlsx")
res = amc_parser.parse_file(tmp / "S99_2026-08.xlsx", SCHEMES)
check("One-scheme sheet: read as before (scheme, 2 holdings, 11.75%, date)",
      len(res) == 1 and res[0]["scheme_id"] == "S99" and res[0]["n"] == 2 and abs(res[0]["listed_total_pct"] - 11.75) < 1e-9 and res[0]["portfolio_date"] == "2026-08-31",
      [(r.get("scheme_id"), r.get("n"), r.get("listed_total_pct"), r.get("portfolio_date")) for r in res])

print(f"\n{sum(results)}/{len(results)} AMC parser checks passed")
sys.exit(0 if all(results) else 1)
