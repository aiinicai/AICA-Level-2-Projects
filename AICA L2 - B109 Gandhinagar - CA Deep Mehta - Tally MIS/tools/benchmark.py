"""Benchmark harness (Python side). Same workload as the Node harness (scripts/bench.ts in the Node copy).

  python tools/benchmark.py live            # masters + month-by-month vouchers from a Tally (or mock) on port 9000
  python tools/benchmark.py files a.xml ... # parse exported XML files

Prints one JSON line: time, peak memory, record counts and a checksum (sum of every <AMOUNT>) to prove both
implementations read exactly the same data.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tally import requests as R  # noqa: E402
from app.tally.client import Endpoint, TallyConfig, map_company, post_and_stream  # noqa: E402
from app.tally.values import canonical_paise  # noqa: E402
from app.tally.xmlstream import stream_file  # noqa: E402


def peak_rss_mb() -> float:
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    k32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
    k32.GetCurrentProcess.restype = wt.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD]
    psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
    return pmc.PeakWorkingSetSize / 1048576


counts: dict[str, int] = {}
stats = {"nodes": 0, "amounts": 0, "amountSum": 0}


def take(rec) -> None:
    counts[rec.tag] = counts.get(rec.tag, 0) + 1
    stats["nodes"] += int(rec.xpath("count(descendant-or-self::*)"))
    for el in rec.iter("AMOUNT"):
        stats["amounts"] += 1
        stats["amountSum"] += canonical_paise(el.text)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "live"
    extra: dict = {}
    t0 = time.perf_counter()
    if mode == "live":
        cfg = TallyConfig(allowed_ports=((1, 65535),), retries=0)
        ep = Endpoint("127.0.0.1", int(os.environ.get("PORT", 9000)))
        to, frm = os.environ.get("TO", "2026-09-30"), os.environ.get("FROM", "2024-04-01")
        comp = [map_company(r) for r in post_and_stream(cfg, ep, R.company_list_request()) if r.tag == "COMPANY"][0]
        requests = 1
        for xml in R.master_requests(comp.name, to, comp.books_from).values():
            requests += 1
            for r in post_and_stream(cfg, ep, xml):
                take(r)
        for m in R.months_between(frm, to):
            requests += 1
            for r in post_and_stream(cfg, ep, R.voucher_range_request(comp.name, m, R.month_end(m))):
                take(r)
        extra["requests"] = requests
    else:
        files = sys.argv[2:]
        extra["files"] = len(files)
        for f in files:
            for r in stream_file(f):
                take(r)
    seconds = time.perf_counter() - t0
    print(json.dumps({"impl": "python", "mode": mode, "seconds": round(seconds, 3), "peak_rss_mb": round(peak_rss_mb(), 1),
                      "counts": counts, **stats, **extra}))


if __name__ == "__main__":
    main()
