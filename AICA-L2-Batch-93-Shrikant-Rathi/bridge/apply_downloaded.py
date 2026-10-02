"""
Apply the AMC files fetched by fetch_amc.py, using the download manifest as the authority for the month.

For each scanned sheet matched to a configured scheme:
  * the month comes from the manifest row of the file it was read from;
  * if the parser also found a date inside the file, the two must agree, otherwise the sheet is rejected;
  * exactly one sheet per (scheme, month) is allowed, otherwise nothing for that pair is applied.
Prints what was applied and what was refused, so the user can review before rebuilding.

Usage:  python apply_downloaded.py [--dry-run]
"""
import calendar
import csv
import sys
from collections import defaultdict
from datetime import date

import lookthrough_bridge as B
from common import CACHE, PORTFOLIO_DIR, load_json


def month_end(ym):
    y, m = map(int, ym.split("-"))
    return date(y, m, calendar.monthrange(y, m)[1]).isoformat()


def main(dry):
    manifest = {r["file"]: r for r in csv.DictReader((PORTFOLIO_DIR / "_sources.csv").open(encoding="utf-8"))}
    B.scan()
    scanned = load_json(CACHE / "portfolios_scanned.json", []) or []
    groups, refused = defaultdict(list), []
    for i, r in enumerate(scanned):
        sid = r.get("scheme_id")
        if not sid or not r.get("holdings"):
            continue
        src = manifest.get(r["file"])
        if not src:
            refused.append(f"{r['file']} [{r['sheet']}] {sid}: file not in the download manifest")
            continue
        want = month_end(src["month"])
        if r.get("portfolio_date") and r["portfolio_date"] != want:
            refused.append(f"{r['file']} [{r['sheet']}] {sid}: date inside file {r['portfolio_date']} != manifest month {want}")
            continue
        if r.get("listed_total_pct", 0) > 101.5:
            refused.append(f"{r['file']} [{r['sheet']}] {sid}: weights add to {r['listed_total_pct']}%")
            continue
        groups[(sid, want)].append((i, r))
    assign = []
    for (sid, d), rows in sorted(groups.items()):
        if len(rows) > 1:
            refused.append(f"{sid} {d}: {len(rows)} candidate sheets {[f'{r[1]['file']}[{r[1]['sheet']}]' for r in rows]}; none applied")
            continue
        i, r = rows[0]
        assign.append({"id": i, "scheme_id": sid, "portfolio_date": d})
        print(f"APPLY  {sid} {d}  {r['file']} [{r['sheet']}]  n={r['n']}  equity={r['equity_pct']:.2f}%  listed total={r['listed_total_pct']:.2f}%")
    for x in refused:
        print("REFUSE", x)
    if not dry:
        print("applied:", B.apply_portfolios(assign))
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main("--dry-run" in sys.argv))
