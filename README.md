# Audit Support Tool — Stage 1

A local Streamlit tool for SAP Day Book and Trial Balance analysis. It has no cloud-storage or data-upload feature: the app runs on your Windows PC and opens in your normal browser.

## Folder structure

```text
audit_support_stage1/
├── app.py                     Main application screen
├── loaders.py                 Excel reading, cleanup, mapping and validation
├── analysis.py                Dashboard calculations and charts
├── sampling.py                Reproducible random sampling
├── generate_dummy_data.py     Makes safe test Excel files
├── requirements.txt           Libraries to install
├── run_audit_tool.bat         Double-click Windows launcher
└── README.md                  Instructions
```

## Beginner setup on Windows

1. Install Python 3.11 or newer from https://www.python.org/downloads/windows/. During installation, tick **Add Python to PATH**. Close and reopen Command Prompt afterwards.
2. Create `C:\AuditSupportTool` and copy all files from this folder into it.
3. Open Command Prompt (Windows key, type `cmd`, Enter), then run:
   ```bat
   cd /d C:\AuditSupportTool
   ```
4. Install the needed libraries once:
   ```bat
   py -3.11 -m pip install -r requirements.txt
   ```
   If Windows cannot find `py -3.11`, use:
   ```bat
   python -m pip install -r requirements.txt
   ```
5. Start the app:
   ```bat
   py -3.11 -m streamlit run app.py
   ```
   Your browser should open. Otherwise, copy the Local URL shown in Command Prompt (normally `http://localhost:8501`) into your browser.
6. Stop the tool with `Ctrl` + `C` in Command Prompt.

### Double-click launch

After the one-time library-install step, double-click `run_audit_tool.bat`. Keep its Command Prompt window open while using the app.

## Test it first

From the app folder run:
```bat
py -3.11 generate_dummy_data.py
```
This creates safe test files in `dummy_data`. Upload them in **Upload & Validate**.

## How to use Stage 1

1. Open **Upload & Validate** in the sidebar.
2. Set the period under review, normally 1 April to 31 March.
3. Upload your Day Book and, where available, the current and previous Trial Balance files.
4. Confirm the detected sheet, header row and column mapping. The mapping is retained in `audit_column_mapping.json` in the same folder, on your PC only.
5. Select **Process files and run validation** and review every item marked “Review”. A flag is an audit prompt, not proof of an error.
6. Open **Comparative Dashboard** for transaction trends, top ledgers and parties, voucher mix, group view and TB comparison. Periods are compared exactly as uploaded—there is no annualising.
7. Open **Sampling**, select a size and retain the displayed seed and method note. Same population plus same seed produces the same sample.

## SAP handling included

- SAP `S` is debit and `H` is credit.
- Excel serial dates and DD-MM-YYYY text dates are recognised.
- SAP trailing-minus values, such as `1,096,358.00-`, are treated as negative.
- Report headers and TB total rows are ignored.
- Voucher codes show friendly labels (for example, `KR – Vendor Invoice`).
- Provisional grouping is 1 assets, 2 liabilities, 3 equity, 4 income and 5–6 expenses.

## Common problems

| Problem | Fix |
|---|---|
| `py is not recognized` | Reinstall Python with **Add Python to PATH**, or use `python` in place of `py -3.11`. |
| `No module named streamlit` | Run `py -3.11 -m pip install -r requirements.txt` in the app folder. |
| Wrong preview / “Column Date not found” | Choose the correct worksheet and heading row; then remap the columns. |
| Dates invalid or outside the period | Confirm Posting Date is mapped and check the selected period. |
| TB values are zero | Set the TB header row to the row containing `G/L Account`, `Debit (Report Period)`, etc. |
| Day Book and TB do not reconcile | Ensure both files cover the same company, dates, ledger scope and source filters. |
| Browser does not open | Use the Local URL shown in Command Prompt, normally `http://localhost:8501`. |

## Audit note

This is an audit-support aid. All validation flags, analyses and samples require professional review and do not replace audit judgement or your firm’s methodology.
