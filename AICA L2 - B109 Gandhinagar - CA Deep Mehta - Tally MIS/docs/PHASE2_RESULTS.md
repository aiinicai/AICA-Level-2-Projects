# Phase 2 results: in-memory data model

**What it is:** DuckDB held in RAM only (`app/model/`). Tables mirror the Node app's model (same amounts in paise,
debit-positive; same voucher-type rules). Tally records are staged in memory and written in one short transaction per
step (masters, one month of vouchers, one month-end stock value), so a failed or cancelled sync never leaves half a month.

## Same data as Node? (fictional demo books, 63 MB, 16.5 years)
Both programs loaded the same 18 XML files. 17 row counts, 27 totals and 9 detailed breakdowns (40,271 individual
values: every ledger's movement, every stock item's net quantity, every bill total, every voucher's balance, vouchers per
month and per type...) were compared. **All identical.**

| | Node (SQLite) | Python (DuckDB) |
|---|---|---|
| Load 39,799 vouchers / 127,928 ledger lines / 29,651 stock lines | 15.9 s | 20.7 s |
| Peak memory | 240 MB | 138 MB |

Live sync of 33 months from the (fictional) mock Tally: 68 steps, 6.3 s, 3,648 vouchers, identical to the file load.
Only difference, by design: the file import skips closing balances when the file has no "as at" date, while the live sync
knows the date and keeps them.

## Nothing left behind
Tests (`tests/test_store.py`) prove: SQL cannot read/write files, DuckDB spill-to-disk is off, no `.wal/.tmp/.duckdb`
files appear in the working or temp folder, `wipe()` drops all tables and closes the database, and a cancelled or
broken import changes nothing.

## Notes
* Bulk loading uses Apache Arrow (`pyarrow`): inserting rows through SQL was ~100x slower in DuckDB 2.0 on this setup.
  This adds roughly 40 MB to the EXE.
* Month re-sync replaces that month's vouchers (including ones deleted in Tally).
