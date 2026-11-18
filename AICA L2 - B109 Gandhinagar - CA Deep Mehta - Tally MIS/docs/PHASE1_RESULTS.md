# Phase 1 results: Tally reader and benchmark

All data is the Node project's built-in **fictional** "Demo Trading Co (Sample Data)" books. Same machine, same
mock Tally server (port 9000), 3 runs each. Node 24.21 vs Python 3.15.2.

| Test | Node | Python | Same data read? |
|---|---|---|---|
| A. Live sync, 39 requests (company list, 8 masters, 30 monthly voucher batches, Apr 2024 - Sep 2026): time | 0.75 s | 0.85-1.0 s | yes |
| A. peak memory | 89 MB | 37 MB | |
| B. Parse 63 MB of XML files (39,799 vouchers, 1.63 M XML elements): time | 2.85 s | 4.1 s | yes |
| B. peak memory | 91 MB | 51 MB | |

"Same data" means identical record counts per type, identical element count and an identical sum of all 242,608
amounts (-164,520,994,340 paise) in both programs. Test A matches too: 3,648 vouchers, 147,362 elements,
sum -12,684,807,790 paise.

The 12 request messages Python builds are byte-for-byte identical to the ones Node builds.

Reproduce: `python tools/benchmark.py live` / `python tools/benchmark.py files <xml...>`; Node side in `tools/node/`.
