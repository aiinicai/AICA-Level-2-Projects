# Phase 3 results: calculations match the Node app

The Python engine (`app/engine/`) answers the same questions as the Node app's routes. To prove it, the original Node
app was run on **fictional** demo books (never real data) through its real API routes, and every JSON answer was saved.
The Python engine loaded the same XML files and had to produce the same answers.

| Scenario (fictional books) | What it exercises | Answers | Values compared | Differences |
|---|---|---|---|---|
| `small` - 30 months, Tally stock valuations | Tally closing stock, bill-wise ageing, cost centres | 33/33 identical | 25,788 | **0** |
| `manual` - same books + manual Stock-in-Hand ledger | manual closing-stock path | 33/33 identical | 27,790 | **0** |
| `big` - 16 years, 39,799 vouchers, no valuations | estimated (moving-average) stock path, long history | 25/25 identical | 26,974 | **0** |

The 33 answers per scenario (the 16-year `big` run was made earlier and covers the first 25): dashboard (default, FY, no comparison, previous period, part-month, one cost centre),
KPIs (with 12-month trends; ROCE, runway, interest cover, inventory days), P&L (compare/monthly/quarterly/default,
revenue analysis, cost analysis), receivables and payables ageing (default, as-at date, custom buckets), ledger list and
search, ledger statements (incl. page 2), voucher details, and an error case. A number must match to 1e-9 relative;
text, list lengths and keys must match exactly. A deliberately changed number (+0.01) is caught (checked).

Speed (same questions, includes the first cold calculation): small 4.7 s vs Node 2.8 s; big dataset 13-31 s vs Node 38-78 s.

## What is ported
Classification of ledgers, P&L (all lines and sub-totals), balance-sheet figures used by the KPIs, stock valuation
(Tally snapshot / manual / estimated), cash flow (operating cash flow KPI), 43 built-in KPIs through the same safe
formula language, ageing (buckets, priority list, trend, upcoming), revenue and cost analysis, ledger and voucher drill-down.

## Not yet (later phases / later version)
Inventory screen, insights, data quality, custom KPI formulas and
ledger mapping editors. The dashboard answer returns empty `insights` and zero data-quality counts for now.

Re-run: `python -m pytest` (uses stored answers) or `python tools/compare_golden.py <answers dir> <xml...>`.
Regenerate answers from Node: `tools/node/golden.ts` (needs the original project copy).
