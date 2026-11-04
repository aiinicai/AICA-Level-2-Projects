# MSME Payables Compliance Tracker (Section 43B(h) + MSME Form 1)

Company-agnostic Streamlit app. Pick a company, keep its Vendor Master, upload Bills (+ Payments), get the dashboard, 43B(h) disallowance and Form 1.

## Run
Windows: double-click `Start_MSME_Tracker.bat` (installs packages on first run, then opens the app).
Or from a terminal:
```
pip install -r requirements.txt
streamlit run app.py
```
Company data is stored in `data/companies/<company>/` (set `MSME_DATA_DIR` to move it).

## Try it with demo data
```
python make_demo_data.py demo_data     # vendor_master.csv, bills.csv, payments.csv
```
Create a company in the sidebar, upload `vendor_master.csv` in tab 1, then bills/payments in tab 2 (as-of 30-09-2026, FY 2025).

## Inputs (download templates from the sidebar; .xlsx / .xls / .csv accepted)
- **Vendor Master** (stored per company): Vendor Name*, MSME Category*, Vendor ID, PAN, GSTIN, Udyam Number, Udyam Registration Date, Agreed Credit Days
- **Bills**: Bill No*, Vendor Name*, Bill Date*, Bill Amount*, Acceptance Date, Description, Branch
- **Payments**: Vendor Name*, Payment Date*, Amount Paid*, Bill No (blank = on-account, FIFO), Reference, Payment Mode (TReDS / Other; blank = Other)

## Rules implemented
- Due date = acceptance date (else bill date) + agreed days (written agreement, capped at 45); no agreement = 15 days.
- Covered = Micro/Small, and accepted on/after the vendor's Udyam registration date (if given).
- 43B(h): covered bills accepted in the FY, unpaid at 31-Mar and past due date = disallowed; prior-year disallowances paid this FY = deductible now.
- Form 1 (columns a–h): per Micro/Small supplier, No. of bills and Amount for (d) paid within 45 days of acceptance – (i) TReDS, (ii) other mode; (e) paid after 45 days; (f) outstanding ≤45 days; (g) outstanding >45 days. Paid columns use payments made in the period (default: current half-year); outstanding is as at the as-of date. Excel export has the two-level form header, totals row and a bill annexure.

## Tests
`python -m pytest -q`

## Saved runs
In tab 2, **Save run** stores the inputs, the vendor master used and (from tab 5) the Form 1 reasons under `data/companies/<company>/runs/`. Reopen from *Saved runs*; by default the saved vendor-master snapshot is used so a filed return reproduces exactly (tick the box to recalculate with the current master).

## Importing vendor statements / software exports (tab 2 → "Vendor statements / software exports")
Upload `.xlsx`, `.xls`, `.csv` or a **text-based** PDF (scanned PDFs need OCR). The importer finds the header row, maps the columns,
classes each row as Bill / Payment (Debit–Credit side, wording such as invoice/receipt/NEFT/credit note, running-balance movement, or
amount sign), skips opening balances and totals, matches vendor names to the vendor master (exact, then close match) and links payments
to the invoice named in the narration. You review the preview, can change any row's Kind, then **Add to this run**. Sample files:
`demo_data/import_samples/`.
Notes: statements have no acceptance date (bill date is used); credit notes count as payments/adjustments; payments with no invoice
reference are applied oldest-bill-first.

## MSME interest (tab 6)
Section 16 MSMED Act: 3 × RBI Bank Rate, compounded with monthly rests, from the day after the due date until payment / as-of date.
Payments reduce principal only; interest stops when principal is cleared. The Bank Rate table (stored in `data/bank_rates.csv`) is
editable – verify it against RBI notifications.
