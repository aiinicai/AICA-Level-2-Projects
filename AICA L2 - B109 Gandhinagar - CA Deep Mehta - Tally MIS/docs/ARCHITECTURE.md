# Architecture

```
 TallyPrime (XML over HTTP, 127.0.0.1:9000-9010)        exported Tally XML files / fictional demo zip
            \                                                  /
             app/tally   lxml streaming reader, request builders, safe HTTP client (this PC only, read-only)
                              |
             app/sync.py  one request per chosen month -> staged in memory -> one short transaction
                              |
             app/model    DuckDB ":memory:" (no disk, no spill, no file access).  Rows loaded through Apache Arrow.
                              |
             app/engine   classification, P&L, balance figures, stock valuation, cash flow, KPIs (safe formula language),
                          ageing, revenue/cost/product analysis, drill-down.   reports.py = the JSON the screens need
                              |
             app/api      FastAPI on 127.0.0.1 : same URLs as the Node app + sync, demo, assistant, close
                              |                                  \
             web/ (React, built to app/static)                    app/assistant : LM Studio client, FACTS builder, number checker
                              |
             app/main.py  pywebview window (Edge WebView2); closing it wipes the store and stops the server
```

## Key decisions
| Decision | Why |
|---|---|
| Reuse the Node project's screens; port the server | The screens do no maths, so identical JSON = identical screens. |
| Money as whole paise, debit-positive | Exact sums; one sign convention (Tally's reversed once, in the reader). |
| Prove equality with the Node app | Saved Node answers ("golden" files) compared figure by figure; Python must match to 1e-9. |
| DuckDB in memory + Arrow bulk load | "Data wiped on close" is guaranteed by design; SQL row inserts were ~100× slower. |
| Stage a month in Python, write in one transaction | A cancelled or failed month leaves nothing half-written. |
| No SQL foreign keys or unique constraints | Faster loading; the importer keeps names and ids unique (a name → id map per company). |
| Safe formula parser, no `eval` | KPI formulas cannot run code. |
| The AI never calculates | Facts are computed by the engine; every number in a reply is checked against them. |
| Local only | Server bound to 127.0.0.1; Host header check; Tally and LM Studio addresses must be loopback. |
| Hash routing in the UI | The built screens work from any base path inside the EXE. |

## Differences from the Node app
Dropped: sign-in, users, audit log, saved views, SQLite, live-connection records. Added: month picker, five themes,
assistant, demo zip, wipe-on-close window. Deferred: balance sheet, inventory, insights, data quality, custom KPIs, export.

## Data status vocabulary (unchanged)
Every important figure is **Actual**, **Calculated**, **Estimated** (with the assumption stated) or **Unavailable** (never guessed).
