"""
Offline-rebuild check: a fresh clone, with no internet, rebuilds exactly the committed snapshot.

data/cache (raw downloads) and data/live (the built dataset) are never committed. A clone therefore starts from
data/snapshot/dataset.json and data/seed_cache (see tools/make_seed_cache.py). This check copies the committed files
(no cache, no live data) to a temporary folder, blocks every network call, rebuilds with `build` (no fetch), and
compares the result with the snapshot field by field (only the build time may differ). It also proves the valuation
date does not move with today's date on an offline rebuild.

Usage:  python verify/offline_rebuild_check.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {str(detail)[:600]}"))


tmp = Path(tempfile.mkdtemp(prefix="lt_clone_"))
files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
for f in files:
    if (ROOT / f).is_file():
        (tmp / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, tmp / f)
check("The copy has no data/live dataset and no cached downloads (as a clone)",
      not (tmp / "data/live/dataset.json").exists() and not any(p.name != "_README.txt" for p in (tmp / "data/cache").glob("*")))

PROBE = r"""
import json, socket, sys
from datetime import date
def _blocked(*a, **k): raise OSError("network blocked by offline_rebuild_check")
socket.socket.connect = _blocked; socket.create_connection = _blocked
sys.path.insert(0, "bridge")
import common
class _D(date):
    @classmethod
    def today(cls): return date(2026, 11, 15)  # two month-ends after the snapshot: an offline rebuild must not move
common.date = _D
import build_dataset as B
ds = B.build(fetch=False)
print(json.dumps({"as_on": ds["meta"]["as_on"]}))
"""
r = subprocess.run([sys.executable, "-c", PROBE], cwd=tmp, capture_output=True, text=True, encoding="utf-8")
check("Offline rebuild runs with every network call blocked", r.returncode == 0, r.stderr[-1500:])
if r.returncode == 0:
    snap = json.loads((ROOT / "data/snapshot/dataset.json").read_text(encoding="utf-8"))
    got = json.loads((tmp / "data/live/dataset.json").read_text(encoding="utf-8"))
    check("The valuation date stays at the data's own month-end (not today's)", got["meta"]["as_on"] == snap["meta"]["as_on"], (got["meta"]["as_on"], snap["meta"]["as_on"]))
    for m in (snap, got):
        for k in ("built_at", "started_at"):
            m["meta"].pop(k, None)
    diff = [k for k in sorted(set(snap) | set(got)) if snap.get(k) != got.get(k)]
    detail = {k: (len(snap.get(k) or []), len(got.get(k) or [])) if isinstance(snap.get(k), list) else "differs" for k in diff}
    if "meta" in diff:
        detail["meta"] = [k for k in set(snap["meta"]) | set(got["meta"]) if snap["meta"].get(k) != got["meta"].get(k)]
    check("The rebuilt dataset equals the committed snapshot, field by field (except the build times)", not diff, detail)
    check("The rebuilt app embeds it", (tmp / "app/LookThrough.html").stat().st_size > 1_000_000)
shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{sum(results)}/{len(results)} offline-rebuild checks passed")
sys.exit(0 if all(results) else 1)
