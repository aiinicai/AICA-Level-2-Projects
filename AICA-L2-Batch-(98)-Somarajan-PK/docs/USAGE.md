# AI-Powered Bank Reconciliation and Audit Assistant (AICA Level 2 Capstone)
One application, one guided flow. Double-click **run_project.bat** - it only starts the application (nothing is calculated or opened automatically).

| Step | In the app |
|---|---|
| 1 | Pull bank books from Tally (Current Assets > Bank Accounts) and **select the bank** |
| 2 | Add the bank statement (CSV) for that bank |
| 3 | Run the reconciliation (only starts when you press the button) |
| 4 | Review the results in the app: dashboard, matches, reconciling items, BRS, exceptions, proposed entries |
| 5 | Approve (decide each journal entry, reviewer name, remarks), then **export to Excel** - export is locked until approval |

No Tally? Use **Load demo data** in step 1 (synthetic, 2 banks). To demo the Pull button itself, run `start_mock_tally.bat` first.

## Files
- `run_project.bat` - starts the app (installs pandas/openpyxl on first run)
- `tool_server.py` - local server: web app + Tally connector + engine API (127.0.0.1 only)
- `recon_engine.py` - matching, BRS, audit rules, journal-entry proposals, Excel writer (also usable from the command line)
- `tally_extract.py` - Tally XML pull logic (also usable from the command line)
- `webapp/index.html` - the application UI
- `generate_data.py`, `mock_tally.py`, `sample_data/` - synthetic data, mock Tally, answer key
- `claude_commentary_prompt.md` - optional AI audit-memo step (paste the summary from step 4)
- `test_engine.py`, `test_tally_extract.py`, `test_tool.py` - tests (`python test_tool.py` covers the whole flow)
- Approved Excel files are saved in `exports/`; pulled Tally data in `tally_export/`

## Command line (optional)
    python recon_engine.py --data sample_data --bank "Bank A"
    python tally_extract.py --from 01-10-2026 --to 31-10-2026 --out tally_export

## Result on sample data
Bank A: difference Rs 0.00, 19/19 planted issues detected. Bank B: difference Rs 0.00.

## Limitations
- Tally extraction was tested against synthetic XML in Tally's documented format, not a live Tally: confirm each bank's opening/closing balance against Tally (Display > Account Books > Bank Books).
- References are matched exactly (cheque no./UTR); "CHQ000123" will not match "000123" by reference alone (falls back to amount + date + narration).
- Bank statements must be CSV (common header variants are recognised). The AI commentary step is manual and optional; AI never calculates.
- Approval is recorded in the exported workbook (reviewer name, time, remarks, entry decisions); it is not a digital signature.
