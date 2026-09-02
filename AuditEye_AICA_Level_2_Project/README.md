# AuditEye - AI Assisted Audit Red Flag Analyzer

## AICA Level 2 Project

AuditEye is a Python and Streamlit based audit analytics application designed to assist Chartered Accountants in reviewing transaction-level accounting data.

The application analyses the complete Transaction Ledger / Day Book and highlights transactions and patterns that may require higher auditor attention.

## Problem Addressed

In large accounting datasets, auditors may have hundreds or thousands of transactions to review. Traditional sampling and spreadsheet filtering are useful, but unusual transactions or cross-transaction patterns may still be missed.

AuditEye helps by analysing the complete transaction ledger and prioritising items for auditor review.

## Key Features

- Upload Tally, Zoho Books and Excel / Google Sheets style ledgers
- Automatic column mapping
- Ledger validation
- Voucher-level analysis
- High-value transaction detection
- Year-end transaction detection
- Round-figure transaction detection
- Duplicate / near-duplicate transaction detection
- Possible split-payment detection
- Related-party transaction analysis
- New / dormant party detection
- Unusual party amount analysis
- Manual journal detection
- Cash and borrowing end-use pattern analysis
- Reversal detection
- Explainable Audit Risk Score
- Statistical anomaly detection using Scikit-learn
- Fuzzy related-party matching using RapidFuzz
- Monthly ledger spike analysis
- Risk dashboard
- Transaction investigation screen
- Suggested auditor procedures
- Excel export of audit findings

## Technologies Used

- Python
- Streamlit
- Pandas
- OpenPyXL
- RapidFuzz
- Scikit-learn
- Plotly

## Install Required Libraries

Run:

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install streamlit pandas openpyxl rapidfuzz scikit-learn plotly
```

## Run the Application

From the project folder, run:

```bash
python -m streamlit run AuditEye_No_License.py
```

Streamlit will display a local browser URL such as:

```text
http://localhost:8501
```

Open that URL in your web browser.

## Demo Files Included

The project includes three fictional demonstration ledgers:

1. AuditEye_Tally_DayBook_Final.xlsx
2. AuditEye_ZohoBooks_GeneralLedger_Final.xlsx
3. AuditEye_GoogleSheets_Ledger_Final.xlsx

These files are intended only for demonstration and classroom use.

## Suggested Demo Flow

1. Enter the company profile.
2. Upload one of the demo ledgers.
3. Confirm the automatic column mapping.
4. Validate the ledger.
5. Run the audit red-flag analysis.
6. Run the AI / anomaly analysis.
7. Review the dashboard.
8. Investigate a high-risk transaction.
9. Export the audit findings to Excel.

## Important Audit Disclaimer

AuditEye identifies risk indicators for auditor review. A red flag is not evidence or a conclusion of fraud. Professional judgement and sufficient appropriate audit evidence remain necessary.

## Project Philosophy

**From Sampling Transactions to Auditing Patterns**

**AI finds the signal. The auditor makes the judgement.**
