# AIS BROKER RECO — Master v5 (Consolidated Build)

**Prepared by: CA Pushkar Hemant Das**

## Project Description

AIS BROKER RECO is a desktop reconciliation utility built for Chartered Accountants and tax professionals to automate the tedious process of cross-verifying capital gains data between the Income Tax Department's **Annual Information Statement (AIS)** and a broker's **Realised Profit & Loss / Tax P&L report**. Manual reconciliation of these two data sources is time-consuming and error-prone — security names differ between the two systems, dates can be off by a day or two due to settlement cycles, and brokerage/transaction charges cause small but non-substantive value mismatches. This tool automates matching, applies the correct Indian Income Tax Act provisions to classify each transaction as Long-Term or Short-Term Capital Gain, filters out nominal cost-driven differences from genuine discrepancies, and produces a polished, auditor-ready Excel workbook with full sheet-to-sheet navigation — significantly reducing the manual effort involved in capital gains reconciliation and tax return preparation.

---

## Overview

**AIS BROKER RECO** is a desktop reconciliation tool that compares capital-gains transactions reported in the **Annual Information Statement (AIS)** against a **Broker Realised P&L / Tax P&L report**, classifies each transaction as **LTCG/STCG** as per applicable Indian tax law, and produces a fully formatted, cross-linked Excel workbook highlighting matches, mismatches, duplicates, and items needing manual review.

This **Master v5** build consolidates every previous incremental version into a **single Python file** — no separate launcher scripts or patch modules are required anymore.

---

## What's Included in This Consolidated Build

This single file (`ais_broker_reco_master_v5.py`) merges the logic previously spread across:

| Legacy file | Functionality folded in |
|---|---|
| `ais_broker_reco_final.py` | Core engine, workbook parser, matching passes, Tkinter GUI |
| `ais_broker_reco_modified.py` | Tax Software Output sheet, nominal sale-value tolerance |
| `ais_broker_reco_report_v2.py` | STT-sheet inference, enhanced name matching, value dashboard |
| `ais_broker_reco_report_v3.py` | Font/PatternFill import fix (built-in from the start here) |
| `ais_broker_reco_isin_v4.py` | ISIN auto-fill for blank Broker ISINs (Equity + Mutual Fund) |

You only need **one script** going forward, plus the optional ISIN master workbook.

---

## Key Features

### 1. Tax Classification (LTCG / STCG)
- Determines **`Is it LTCG ?`** as **Yes / No / Review Required**, based on:
  - Period of holding (purchase date → sale date)
  - Type of asset (Listed Equity / Equity MF / Debt MF / Bonds-Debentures)
  - Section 50AA treatment for debt mutual funds acquired on/after 1 April 2023
- STT-paid status is inferred from the **source sheet name** (e.g., a sheet titled *"Gain arising of STT Paid"* is treated as `STT Paid: Yes`) and shown only as a **supporting remark** — it is not used as the sole classification test.

### 2. Value Dashboard on Summary Sheet
The Summary sheet now shows, in addition to record counts:

| Reconciliation Category | Value as per AIS | Value as per Broker Report | Actual Difference |
|---|---|---|---|
| Matched Transactions (Gross) | ✓ | ✓ | ✓ |
| Material Differences (Above Tolerance) | ✓ | ✓ | ✓ |
| Ignored Transaction-Cost Variances (Within Tolerance) | ✓ | ✓ | ✓ |
| Missing in Broker (present only in AIS) | ✓ | — | ✓ |
| Missing in AIS (present only in Broker) | — | ✓ | ✓ |
| Grand Total (All Records) | ✓ | ✓ | ✓ |

### 3. Full Two-Way Navigation
- Every metric row on the **Summary** sheet has an **"Open … ➜"** hyperlink that jumps straight to the relevant detail sheet.
- Every detail sheet has a **"⬅ Back to Summary"** link in cell A1.
- The sheet name **"Other Financial Differences"** and its Summary link label are now identical (previously mismatched).

### 4. Smarter Nominal-Variance Handling
- A **dynamic tolerance** (greater of Rs 100 or 0.75% of the transaction value, capped at Rs 2,500) is applied to Sale Value comparisons.
- If the **Qty sold/redeemed matches** between AIS and Broker, small Sale Value gaps (typically caused by brokerage/other transaction charges, since AIS reports gross/net consideration differently from the broker) are automatically moved to an **"Ignored Sales Variances"** sheet instead of cluttering the genuine difference sheets.

### 5. Enhanced Name / Symbol Matching
Matching now uses multiple layers before falling back to "Review Required":
1. Exact ISIN match (highest priority)
2. Cleaned substring/exact name match
3. NSE trading **symbol ↔ company name** cross-reference (via `ISIN_Code_List.xlsx`, if present) — e.g. recognises a broker row using `RIL` against AIS's *"Reliance Industries Limited"*
4. Generated-acronym check (first letters of each significant word)
5. Fuzzy string-similarity fallback (≥ 72% match ratio)

### 6. Blank ISIN Auto-Fill (Broker sheet only)
- **Equity:** exact trading-symbol match first, then fuzzy company-name match.
- **Mutual Funds:** fuzzy scheme-name match, checked separately against Growth/Payout vs Dividend-Reinvestment/IDCW ISINs. If the plan type can't be determined and both exist, the ISIN is **left blank and flagged "Manual Review"** — never guessed.
- Every fill/flag decision is logged to a new **"ISIN Auto-Fill Log"** sheet in the output workbook.

### 7. Removed Columns
Since neither AIS nor Broker files reliably report these, the following columns have been **removed** from all output sheets to avoid clutter:
- **STT Paid Amount**
- **Holding Period (days)**

(Holding period is still calculated internally for classification purposes — it's just not printed as a column.)

### 8. Date-Window Tolerance
- AIS-vs-Broker date matching allows a **2-day window** (T+1/T+2 settlement offset).

---

## Files Needed

| File | Required? |
|---|---|
| `ais_broker_reco_master_v5.py` | **Yes** — the only script you need to run |
| `ISIN_Code_List.xlsx` | Optional — enables ISIN auto-fill and symbol-based name matching. Place it next to the script, or point to it via the `ISIN_MASTER_FILE` environment variable |

All older files (`ais_broker_reco_final.py`, `ais_broker_reco_modified.py`, `ais_broker_reco_report_v2.py`, `ais_broker_reco_report_v3.py`, `ais_broker_reco_isin_v4.py`) are **superseded** and no longer needed.

---

## Installation

```bash
python -m pip install pandas openpyxl
```

Optional (only if you need to read legacy `.xls` files):

```bash
python -m pip install xlrd
```

---

## Running the App

```bash
python ais_broker_reco_master_v5.py
```

1. Browse and select the **AIS Data Sheet** (Excel).
2. Browse and select the **Broker Realised P&L Account** (Excel).
3. Choose the **Financial Year / Tax Rules**.
4. Click **START RECONCILIATION**.
5. Choose where to save the output workbook (a `_TECHNICAL_LOG.txt` file is written alongside it automatically).

If a file with the same name already exists at the chosen location, the app automatically appends `_1`, `_2`, etc. to avoid overwriting.

---

## ISIN Master File (Optional)

If you want ISIN auto-fill and symbol-based matching:

- Place `ISIN_Code_List.xlsx` in the same folder as the script, **or**
- Set an environment variable pointing to it:

```bash
# Windows
set ISIN_MASTER_FILE=C:\path\to\ISIN_Code_List.xlsx

# macOS/Linux
export ISIN_MASTER_FILE=/path/to/ISIN_Code_List.xlsx
```

If the master file isn't found, the app still runs normally — ISIN auto-fill and symbol-based matching are simply skipped for that run, and a note is written to the log.

---

## Output Workbook — Sheet List

| Sheet | Purpose |
|---|---|
| Summary | Metrics + navigation links + value dashboard |
| Tax Software Output | Final Yes/No LTCG classification per matched transaction |
| Difference in Long Term | LTCG classification mismatches |
| Difference in Short Term | STCG classification mismatches |
| Other Financial Differences | Material sale-value/cost mismatches (name unified with Summary link) |
| Ignored Sales Variances | Nominal gaps absorbed by brokerage/transaction charges |
| Duplicate Entries in AIS | AIS rows flagged as duplicates vs Broker |
| Missing Entries in AIS | Broker-only records |
| Missing Entries in Broker | AIS-only records |
| Matched Transactions | All successfully matched pairs, side-by-side |
| Review Required | Records needing manual attention |
| ISIN Auto-Fill Log | Every ISIN fill/flag decision (only if master file used) |

---

## Building a Desktop Executable

Once the script runs correctly from the command line:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed ais_broker_reco_master_v5.py
```

The resulting executable will be in the `dist/` folder. Keep `ISIN_Code_List.xlsx` alongside the `.exe` if you want ISIN auto-fill/symbol matching to work in the packaged app.

---

## Known Limitations

- AMFI mutual fund master also distinguishes **Direct vs Regular** plans (not just Growth vs Dividend). Unless the broker's security name states the plan variant, MF auto-fill/matching may correctly leave the ISIN blank rather than guess — this is intentional.
- STT-paid status is inferred **only from the source sheet's name/label**, since neither file reports a reliable STT amount column; it is used as supporting evidence, not the primary classification test.
- Classification of "Other Securities" (bonds/debentures/unlisted shares) uses simplified keyword heuristics and may require manual confirmation for edge cases.