"""Compare the Python engine's answers with the Node app's saved answers ("golden" files), figure by figure.

  python tools/compare_golden.py <golden_dir> <xml files...>

Numbers must agree to 1e-9 relative (or 0.005 rupee absolute); text, lists and keys must match exactly.
Keys the lean version does not build yet (insights, data-quality counts) are skipped and listed.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.engine.dispatch import handle  # noqa: E402
from app.model.store import Store  # noqa: E402
from app.sync import Runs, import_files  # noqa: E402

SKIP = {"insights", "insightCount", "dq"}  # built in a later phase (Insights, Data quality screens)
stats = {"values": 0, "diffs": 0}


def same_num(a, b) -> bool:
    if a == b:
        return True
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-6)


def cmp(a, b, path: str, out: list[str]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) | set(b):
            if k in SKIP and path.count(".") < 1:
                continue
            ka, kb = a.get(k), b.get(k)
            if k not in a and kb is None or k not in b and ka is None:
                continue  # JSON drops undefined; Python writes None
            cmp(ka, kb, f"{path}.{k}", out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: list length node={len(a)} python={len(b)}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            cmp(x, y, f"{path}[{i}]", out)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        stats["values"] += 1
        if not same_num(a, b):
            out.append(f"{path}: node={a!r} python={b!r}")
    else:
        stats["values"] += 1
        if a != b:
            out.append(f"{path}: node={str(a)[:80]!r} python={str(b)[:80]!r}")


def run(gdir: str, files: list[str], verbose: bool = True, reqs_path: str | None = None) -> tuple[int, dict]:
    stats.update(values=0, diffs=0)
    reqs = json.load(open(reqs_path or os.path.join(os.path.dirname(__file__), "..", "tests", "golden", "golden_requests.json"), encoding="utf-8"))
    store = Store()
    cid = store.ensure_company("Demo Trading Co (Sample Data)")
    runs = Runs()
    for f in files:
        imp = import_files(store, runs.new(company_id=cid, mode="file"), cid, [f])
        assert imp.status == "succeeded", imp.error
    bad = 0
    t_py = 0.0
    failures: list[str] = []
    times = json.load(open(os.path.join(gdir, "_times.json")))
    for q in reqs:
        gold = json.load(open(os.path.join(gdir, q["name"] + ".json"), encoding="utf-8"))
        t0 = time.perf_counter()
        status, body = handle(store, q["url"])
        t_py += time.perf_counter() - t0
        body = json.loads(json.dumps(body, default=str))
        diffs: list[str] = []
        if status != gold["status"]:
            diffs.append(f"status node={gold['status']} python={status}")
        cmp(gold["body"], body, "$", diffs)
        stats["diffs"] += len(diffs)
        if verbose:
            print(f"{'OK  ' if not diffs else 'DIFF'} {q['name']:<22} node {times[q['name']]:>5} ms")
            for d in diffs[:6]:
                print("      ", d)
            if len(diffs) > 6:
                print(f"       ... and {len(diffs) - 6} more")
        else:
            failures.extend(f"{q['name']}: {d}" for d in diffs[:3])
        bad += bool(diffs)
    if verbose:
        print(f"\n{len(reqs) - bad}/{len(reqs)} answers identical; {stats['values']} values compared, {stats['diffs']} differences. "
              f"Python total {t_py * 1000:.0f} ms vs Node {sum(times.values())} ms")
    return bad, {**stats, "answers": len(reqs), "failures": failures}


def main() -> int:
    return 1 if run(sys.argv[1], sys.argv[2:])[0] else 0


if __name__ == "__main__":
    sys.exit(main())
