# AI-Powered Bank Reconciliation and Audit Assistant

**ICAI AICA Level 2 – Individual Capstone Project**
**Batch:** 98, Ernakulam  |  **Author:** CA Somarajan PK (M.No 235612)

A local application that takes bank books from Tally, matches them against a bank statement, flags audit exceptions, and exports an Excel reconciliation **only after the Chartered Accountant approves**.

## Problem
Monthly bank reconciliation is repetitive, and the risky items (duplicate payments, transposed digits, keying errors, stale cheques) hide among entries that nearly match. Reviewer sign-off is often not recorded anywhere.

## Solution – five guided steps
1. Pull bank books from Tally (Current Assets > Bank Accounts) and select the bank
2. Add the bank statement (CSV)
3. Run the reconciliation
4. Review results in the app: dashboard, matches, reconciling items, BRS, exceptions, proposed journal entries
5. Approve (decide each entry, reviewer name, remarks) and export to Excel – export is locked until approval

## How it works
- **Tally connector** (`tally_extract.py`): Tally Prime XML server on localhost:9000; bank ledgers plus Day Book vouchers; cancelled/optional vouchers skipped; opening balance rolled forward.
- **Matching engine** (`recon_engine.py`): exact → reference with date lag → near match → transposition/amount error → many-to-one/one-to-many. Every match records its rule and confidence.
- **Audit flags (10):** duplicate payment, transposition, amount error, unidentified bank item, stale cheque, round sum, near approval limit, weekend posting, split payment, missing narration/reference.
- **Human in the loop:** per-entry Approve/Reject, named reviewer, mandatory remarks if a difference remains; enforced by the server, not only the screen.
- **Privacy:** runs on 127.0.0.1; data never leaves the machine.

## Run it (Windows 11, Python 3.10+)
Double-click `run_project.bat`. The app opens in the browser.
No Tally? Use **Load demo data** in step 1. To demo the Pull button, run `start_mock_tally.bat` first.
Tests: `python test_tool.py`, `python test_engine.py`, `python test_tally_extract.py`.
More detail: [docs/USAGE.md](docs/USAGE.md)

## Results (synthetic data, seed 2026)
| | Bank A | Bank B |
|---|---|---|
| Entries auto-matched | 32 of 36 | 4 of 5 |
| Reconciling items | 11 | 3 |
| Exceptions | 10 (1 High) | – |
| Final difference | ₹0.00 | ₹0.00 |
| Planted issues detected | 19 of 19 | – |

The 19 planted issues are an answer key created with the test data, so these figures show the logic works on that data. They are **not** an accuracy claim for real books.

## Data and AI-use statement
All data in this repository is **synthetic** (fictional entity "ABC Traders Pvt Ltd"). No confidential, personal, client-related or sensitive information was entered into any AI platform, in line with the AICA course rule. Live Tally data was never shared with the AI. See [AI_USAGE.md](AI_USAGE.md).

## Limitations
- Tally connector validated on mock Tally XML only, not a live company
- Bank statements must be CSV
- Exact reference matching: `CHQ000123` will not match `000123` by reference alone
- Approval is a recorded sign-off, not a digital signature

## Next steps
Pilot on anonymised live Tally data; Excel/PDF statement import; reference normalisation; post approved entries back to Tally after sign-off.

## Project files
| File | Purpose |
|---|---|
| `run_project.bat` | One-click launcher |
| `tool_server.py` | Local server and API |
| `recon_engine.py` | Matching, flags, entries, Excel export |
| `tally_extract.py` | Tally XML connector |
| `webapp/` | Browser interface |
| `generate_data.py`, `sample_data/` | Synthetic data and answer key |
| `mock_tally.py`, `start_mock_tally.bat` | Demo Tally server |
| `test_*.py` | Tests |
| `claude_commentary_prompt.md` | Optional AI audit-memo prompt |

Presentation: [add link]  |  Video: [add YouTube unlisted / Drive link]
