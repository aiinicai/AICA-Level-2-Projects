"""
Build data/seed_cache: the smallest set of cached source data from which an OFFLINE rebuild reproduces the committed
snapshot (data/snapshot/dataset.json) exactly.

Why: data/cache (raw downloads) is never committed, so a fresh clone could not rebuild the dataset without the
internet, and every check that rebuilds (bridge, entry, contract note, equity) failed there. The seed keeps only what
the build reads, trimmed to what the snapshot already publishes:

  * prices and NAV histories: only the one observation the build takes for each month-end (the last one on or
    before it, as sources.monthly_from_daily does), not the daily series;
  * AMFI's NAV list: only the tracked schemes' lines (plus the header); NSE's equity list (public, 0.2 MB);
  * market caps, company profiles and statements as cached; the parsed AMC holdings (portfolios_applied.json).

bridge/common.py copies a seed file into data/cache only when that file is missing, and back-dates it, so an online
session replaces it with a full download at first use while an offline one still has it.

Usage:  python tools/make_seed_cache.py      (after a build whose data/live/dataset.json is the snapshot)
"""
import csv
import io
import json
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE, SEED = ROOT / "data" / "cache", ROOT / "data" / "seed_cache"
SNAP = json.loads((ROOT / "data" / "snapshot" / "dataset.json").read_text(encoding="utf-8"))
DATES = [date.fromisoformat(d) for d in SNAP["meta"]["dates"]]


def month_end_picks(pairs):
    """The observations monthly_from_daily would take: for each month-end, the last one on or before it (<= 10 days)."""
    pairs, keep, j, last = sorted(pairs), set(), 0, None
    for d in DATES:
        while j < len(pairs) and pairs[j][0] <= d:
            last = pairs[j]
            j += 1
        if last and (d - last[0]).days <= 10:
            keep.add(last[0])
    return keep


def main():
    if SEED.exists():
        shutil.rmtree(SEED)
    SEED.mkdir(parents=True)
    # prices: month-end picks only
    px = json.loads((CACHE / "yahoo_prices.json").read_text(encoding="utf-8"))
    out = {}
    for tk, v in px.items():
        pts = [(date.fromisoformat(d), c) for d, c in v.get("points") or []]
        keep = month_end_picks(pts)
        out[tk] = {**{k: x for k, x in v.items() if k != "points"}, "points": [[d.isoformat(), c] for d, c in sorted(pts) if d in keep]}
    (SEED / "yahoo_prices.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    # NAV histories of the tracked schemes: month-end picks only
    codes = {str(c) for s in SNAP["schemes"] for c in (s.get("amfi_code"), s.get("amfi_code_regular")) if c}
    for code in sorted(codes):
        p = CACHE / f"mf_nav_{code}.json"
        if not p.exists():
            continue
        raw = json.loads(p.read_text(encoding="utf-8"))
        rows = [(datetime.strptime(x["date"], "%d-%m-%Y").date(), x) for x in raw.get("data", []) if x.get("date")]
        keep = month_end_picks([(d, 0) for d, _ in rows])
        raw["data"] = [x for d, x in rows if d in keep]
        (SEED / p.name).write_text(json.dumps(raw, separators=(",", ":")), encoding="utf-8")
    # AMFI NAV list: header and the tracked schemes' lines
    lines = (CACHE / "amfi_navall.txt").read_text(encoding="utf-8", errors="replace").splitlines()
    keep = [ln for ln in lines if ln.lower().startswith("scheme code") or ln.split(";")[0].strip() in codes]
    (SEED / "amfi_navall.txt").write_text("\n".join(keep) + "\n", encoding="utf-8")
    # as cached: NSE list, market caps, company profiles/statements, parsed AMC holdings
    for name in ["nse_equity_list.csv", "yahoo_mcap.json", "portfolios_applied.json"] + [p.name for p in CACHE.glob("yahoo_co_*.json")]:
        if (CACHE / name).exists():
            shutil.copy2(CACHE / name, SEED / name)
    n = len(list(SEED.iterdir()))
    size = sum(p.stat().st_size for p in SEED.iterdir())
    print(f"seed_cache: {n} files, {size / 1e6:.2f} MB")


if __name__ == "__main__":
    sys.exit(main())
