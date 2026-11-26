# Tally Purchase Register vs GSTR-2B Reconciliation

**AICA Level 2 – Capstone Project | Batch L2B111 – Pimpri Chinchwad**
**Author:** CA Ganesh R Kankate (ICAI Membership No. 137798)

A one-file Streamlit web app that cleans a Tally Prime Purchase Register export and reconciles it with the GSTR-2B (B2B) downloaded from the GST portal. It produces a formatted, multi-tab Excel workbook in one click.

---

## 1. Problem statement

Every month, a CA firm or accounts team has to confirm that each purchase invoice booked in Tally shows up in the supplier's GSTR-1, and so in the buyer's GSTR-2B, before Input Tax Credit is claimed (Section 16(2)(aa), CGST Act). Doing this by hand is slow and error-prone:

- Tally exports contain title rows, Grand Total rows and one column per ledger, and ledger names vary from client to client ("Purchase IGST 18%", "Input IGST", "IGST Purchases", ...).
- Supplier invoice numbers are typed differently in the books and on the portal (`inv-0005` vs `INV/5`).
- The portal repeats an invoice once per tax rate and uses a merged two-row header.
- TDS deducted on the purchase lowers the Gross Total in Tally, but the 2B shows the full invoice value.

## 2. What the app does

| Stage | Work done |
|---|---|
| **1. Standardise Tally register** | Finds the header row, removes junk rows, sorts every ledger column into Taxable / IGST / CGST / SGST / SEZ / TDS / Other (purchase-ledger words beat GST words, and "Input/ITC/Payable" words beat purchase words), and computes **Diff** and **Books Invoice Value** (Gross + TDS added back) |
| **GST rate check** | Effective rate = tax ÷ taxable, compared with the standard slabs (0.1 … 40 %). Flags mixed IGST + CGST/SGST, CGST ≠ SGST and non-standard rates |
| **2. Segregate** | Rows with a blank or invalid GSTIN go to *Unregistered / Non-2B* |
| **3. Parse GSTR-2B** | Reads the portal B2B sheet (two-row or flat header) and consolidates rate-wise rows into one row per invoice |
| **4. Multi-tier match** (one-to-one) | **Tier 1** GSTIN + exact invoice no. → **Tier 2** GSTIN + normalised invoice no. → **Tier 3** GSTIN totals within ₹ tolerance → **Tier 4** unmatched, with remarks (possible duplicate, probable match, ITC at risk, not booked in Tally) |
| **5. Excel output** | 8 formatted sheets: summary, cleaned register, Tiers 1–3, unregistered, unmatched, cleaned 2B |

## 3. Folder contents

```
app.py                      Streamlit application (single file)
requirements.txt            Python libraries
Run_App.bat                 Double-click launcher (Windows)
STEPS.txt                   Full user guide: setup, Tally export, output tabs, troubleshooting
MASTER_PROMPT.txt           The prompt used to build the app with AI
sample_data/
  make_samples.py           Builds the dummy input files
  Sample_Tally_Purchase_Register.xlsx
  Sample_GSTR2B.xlsx
  Sample_Output_GSTR2B_Reconciliation.xlsx
tests/
  self_test.py              56 automated checks on the sample data
```

All party names and GSTINs in `sample_data` are fictitious. No client data is included.

## 4. How to run

```
pip install -r requirements.txt
python -m streamlit run app.py
```

You can also double-click `Run_App.bat`, or open `app.py` in IDLE and press F5. The browser opens at http://localhost:8501. Upload the two Excel files and click **Run Reconciliation**.

To try it without real data, upload the two files in `sample_data/`.

## 5. Testing

```
python tests/self_test.py
```

The test regenerates the sample files and checks the following:
- ledger classification (22 ledger names)
- amount and date parsing (`100.00 Cr`, `(1,000)`, ISO `2026-10-03` read as 3-Oct-2026)
- junk-row removal and column order
- TDS add-back and the 16 % rate flag
- 2B rate-row consolidation
- every reconciliation tier, including the duplicate and 2B-only cases
- the Excel sheet order

Current result: **56 passed, 0 failed** (Python 3.12, pandas 3.1.1, Streamlit 1.67).

## 6. Scope and limitations

- Only the GSTR-2B **B2B** sheet is reconciled. Credit/debit notes, ISD and import (IMPG) entries are out of scope.
- Matching relies on the **Supplier Invoice No.** and **GSTIN/UIN** columns being switched on in the Tally export.
- Ledger classification is rule-based. Check the *Ledger mapping* tab in the app for any unusual ledger names.

## 7. Tech stack

Python 3.10+, Streamlit, pandas (2.x and 3.x), NumPy, openpyxl.
