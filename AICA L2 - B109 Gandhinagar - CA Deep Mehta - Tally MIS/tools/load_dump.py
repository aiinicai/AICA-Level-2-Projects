"""Load XML files into the in-memory store and dump figures comparable with the Node importer (tools/node/load-dump.ts).

  python tools/load_dump.py out.json masters.xml daybook-2010.xml ...
  python tools/load_dump.py --compare node_dump.json out.json
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.model.store import Store  # noqa: E402
from app.sync import Runs, import_files  # noqa: E402

QUERIES = json.load(open(os.path.join(os.path.dirname(__file__), "dump_queries.json"), encoding="utf-8"))


def dump(store: Store, seconds: float) -> dict:
    from tools.benchmark import peak_rss_mb  # noqa
    out = {"impl": "python", "seconds": round(seconds, 3), "peak_rss_mb": round(peak_rss_mb(), 1), "counts": {}, "sums": {}, "groups": {}}
    for k, sql in QUERIES["counts"].items():
        out["counts"][k] = int(store.scalar(sql.replace(" v FROM", " AS v FROM")))
    for k, sql in QUERIES["sums"].items():
        out["sums"][k] = int(store.scalar(sql))
    for k, sql in QUERIES["groups"].items():
        out["groups"][k] = {str(r["k"]): int(r["v"]) for r in store.rows(sql)}
    return out


def compare(a: dict, b: dict) -> int:
    bad = 0
    for sec in ("counts", "sums"):
        for k in a[sec]:
            ok = a[sec][k] == b[sec].get(k)
            bad += not ok
            if not ok:
                print(f"DIFF {sec}.{k}: node={a[sec][k]} python={b[sec].get(k)}")
    for k in a["groups"]:
        ga, gb = a["groups"][k], b["groups"].get(k, {})
        diffs = [(x, ga.get(x), gb.get(x)) for x in set(ga) | set(gb) if ga.get(x) != gb.get(x)]
        bad += bool(diffs)
        if diffs:
            print(f"DIFF groups.{k}: {len(diffs)} differ, e.g. {diffs[:3]}")
    n = len(a["counts"]) + len(a["sums"]) + len(a["groups"])
    rows = sum(len(v) for v in a["groups"].values())
    print(f"checked {len(a['counts'])} counts, {len(a['sums'])} totals, {len(a['groups'])} breakdowns ({rows} values): "
          f"{'ALL MATCH' if not bad else str(bad) + ' DIFFERENCES'}")
    return bad


if __name__ == "__main__":
    if sys.argv[1] == "--compare":
        sys.exit(1 if compare(json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))) else 0)
    out_path, files = sys.argv[1], sys.argv[2:]
    store = Store()
    cid = store.ensure_company("Demo Trading Co (Sample Data)")
    runs = Runs()
    t0 = time.perf_counter()
    for f in files:
        run = import_files(store, runs.new(company_id=cid, mode="file"), cid, [f])
        if run.status != "succeeded":
            raise SystemExit(f"{f}: {run.status} {run.error}")
    d = dump(store, time.perf_counter() - t0)
    json.dump(d, open(out_path, "w"))
    print(json.dumps({"impl": "python", "seconds": d["seconds"], "peak_rss_mb": d["peak_rss_mb"], "vouchers": d["counts"]["vouchers"]}))
