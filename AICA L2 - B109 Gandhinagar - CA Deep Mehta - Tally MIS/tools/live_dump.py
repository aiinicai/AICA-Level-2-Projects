"""Live-sync the mock Tally (port 9000) into the in-memory store and dump comparable figures."""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.model.store import Store
from app.sync import Runs, live_sync, list_months
from app.tally.client import Endpoint, TallyConfig, find_open_companies
from tools.load_dump import dump

cfg = TallyConfig(allowed_ports=((9000, 9010),))
found = find_open_companies(cfg)
print(found)
name = found.companies[0].name
store = Store()
cid = store.ensure_company(name)
frm, to = sys.argv[2] if len(sys.argv) > 2 else "2024-04-01", sys.argv[3] if len(sys.argv) > 3 else "2026-09-30"
t0 = time.perf_counter()
run = live_sync(store, cfg, Endpoint("127.0.0.1", found.port), Runs().new(company_id=cid, mode="full"), cid, name, list_months(frm, to))
secs = time.perf_counter() - t0
print(run.status, run.error, len(run.batches), "steps", run.warnings[:2])
d = dump(store, secs)
json.dump(d, open(sys.argv[1], "w"))
print(json.dumps({"seconds": d["seconds"], "peak_rss_mb": d["peak_rss_mb"], "vouchers": d["counts"]["vouchers"]}))
