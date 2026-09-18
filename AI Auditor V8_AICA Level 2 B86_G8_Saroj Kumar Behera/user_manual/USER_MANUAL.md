# AI Auditor V8 — User Manual & Reference Guide

**AI Auditor V8** is an offline Windows desktop application engineered for Chartered Accountants, statutory auditors, internal audit teams, bank credit officers, and CFOs. It automates financial statement analysis and analytical audit procedures in strict accordance with standard accounting frameworks (Ind AS / AS / Schedule III) and **Standard on Auditing (SA 520 / ISA 520)**.

---

## Table of Contents
1. [Overview & Core Value](#1-overview--core-value)
2. [System Requirements](#2-system-requirements)
3. [Installation & Launching](#3-installation--launching)
4. [Step-by-Step Workflow Guide](#4-step-by-step-workflow-guide)
   - [Step 1: Uploading Financial Statements (Excel / PDF)](#step-1-uploading-financial-statements-excel--pdf)
   - [Step 2: Processing & Data Extraction](#step-2-processing--data-extraction)
   - [Step 3: Reviewing & Adjusting Extracted Data](#step-3-reviewing--adjusting-extracted-data)
   - [Step 4: Interpreting Financial Ratios](#step-4-interpreting-financial-ratios)
   - [Step 5: Reviewing Trend & Horizontal Analysis](#step-5-reviewing-trend--horizontal-analysis)
   - [Step 6: Analyzing Significant Variations (>= 5%)](#step-6-analyzing-significant-variations--5)
   - [Step 7: Understanding "Possible Reasons"](#step-7-understanding-possible-reasons)
   - [Step 8: Substantive Audit Verification Checklist](#step-8-substantive-audit-verification-checklist)
   - [Step 9: Reviewing Potential Risk Areas](#step-9-reviewing-potential-risk-areas)
   - [Step 10: Exporting Excel & Word Audit Reports](#step-10-exporting-excel--word-audit-reports)
5. [Configuring Variance & Materiality Thresholds](#5-configuring-variance--materiality-thresholds)
6. [Key Accounting & Audit Distinctions](#6-key-accounting--audit-distinctions)
7. [Common Errors & Troubleshooting](#7-common-errors--troubleshooting)
8. [Statutory Disclaimer & Limitations](#8-statutory-disclaimer--limitations)

---

## 1. Overview & Core Value

Auditing standards require auditors to apply analytical procedures at both the planning and substantive stages of an audit (SA 520). Traditionally, preparing comparative financial models, computing dozens of ratios, and drafting variance justifications consumes hours of manual work in spreadsheets.

**AI Auditor V8** completely automates this workflow:
- **Instant Ingestion**: Parses multi-year Excel spreadsheets (.xlsx, .xls) and PDF annual reports (including scanned PDFs via OCR).
- **Automated Taxonomy Mapping**: Employs fuzzy heuristics to map custom line items into standardized Schedule III / Ind AS heads.
- **30 Financial Ratios**: Computes comprehensive Liquidity, Profitability, Solvency, Activity, and Cash Flow metrics with formula transparency.
- **Objective Variance Screening**: Automatically isolates line items moving $\ge 5\%$ (customizable) and attaches plausible non-conclusive **Possible Reasons**.
- **Evidence-Based Audit Checklist**: Specifies the exact primary accounting records (e.g. GSTR-3B reconciliation, debtor ageing, bank confirmations, physical stock sheets) and explains **WHY** each document is necessary.
- **Executive Reporting**: Generates a 12-worksheet formatted Excel model and an executive-ready Word (.docx) audit diagnostic report.
- **100% Offline**: Requires no internet access or third-party cloud AI subscriptions.

---

## 2. System Requirements

- **Operating System**: Windows 10 or Windows 11 (64-bit).
- **RAM**: Minimum 4 GB (8 GB recommended for large scanned PDF OCR).
- **Storage**: 250 MB free disk space.
- **Office Compatibility**: Microsoft Office (Excel / Word), LibreOffice, or Kingsoft WPS to view exported reports.
- **Optional OCR Engine**: Tesseract OCR (if processing image-based/scanned PDFs).

---

## 3. Installation & Launching

### Standalone Executable (No Python Required)
1. Download or locate the `AI Auditor V8` folder.
2. Double-click `AI Auditor V8.exe` inside `dist/AI Auditor V8/` (or run `build_exe.bat` to compile).
3. The application will launch immediately.

### Running from Python Source Code
If running from source:
```powershell
python -m pip install -r requirements.txt
python main.py
```

---

## 4. Step-by-Step Workflow Guide

### Step 1: Uploading Financial Statements (Excel / PDF)
1. Launch **AI Auditor V8** and navigate to **Upload Financials** on the sidebar.
2. Drag and drop your file into the dashed drop zone, or click **Browse File from Computer**.
3. Select your reporting unit scale from the dropdown (e.g. *₹ in Lakhs*, *₹ in Crores*, *₹ Exact*, *$ in Millions*).
4. If uploading a scanned PDF, ensure the **Enable OCR** checkbox is checked.

### Step 2: Processing & Data Extraction
1. Click the green **Extract & Analyze Statement** button.
2. The background worker will read the file structure, extract Balance Sheet, P&L, and Cash Flow figures, calculate all ratios, and run the variance and risk algorithms.
3. Upon completion, a success notification appears, and the app automatically switches to the **Dashboard**.

### Step 3: Reviewing & Adjusting Extracted Data
1. Navigate to **Data Review & Mapping**.
2. Three tabs are provided: *Balance Sheet*, *Profit & Loss*, and *Cash Flow Statement*.
3. Verify that extracted figures match your audited statements. You can double-click any cell to edit amounts directly.
4. If an unusual line item was categorized incorrectly, select the correct classification from the **Standard Classification (Taxonomy)** dropdown.
5. To add custom unlisted schedules, click **+ Add Custom Line Item**.
6. Click **Save Adjustments & Recalculate** to refresh all ratios, variances, and checklists.

### Step 4: Interpreting Financial Ratios
1. Navigate to **Financial Ratios**.
2. Explore the five categorized tabs:
   - **Liquidity Ratios**: Current Ratio, Quick Ratio, Cash Ratio, Net Working Capital.
   - **Profitability Ratios**: Gross Margin, EBITDA Margin, EBIT Margin, PAT Margin, ROE, ROCE, ROA.
   - **Solvency & Leverage**: Debt-Equity, Debt to Assets, Interest Coverage (ICR), DSCR, Proprietary Ratio.
   - **Activity & Efficiency**: Inventory Turnover & DSI, Receivables Turnover & DSO, Payables Turnover & DPO, Working Capital Turnover, Asset Turnover.
   - **Cash Flow & Key Metrics**: Net Debt, Cash Conversion Cycle (CCC), OCF to Total Debt, OCF to Net Profit (Quality of Earnings).
3. Each ratio card displays the mathematical formula, current vs previous period figures, benchmark ranges, health tags (*Healthy*, *Moderate*, *Attention*, *Critical*), and professional CA interpretations.

### Step 5: Reviewing Trend & Horizontal Analysis
1. Navigate to **Trend Analysis**.
2. Inspect horizontal YoY changes (absolute amounts and percentage differences).
3. Review **Common-Size Statements** showing each P&L item as a percentage of Revenue from Operations, and each Balance Sheet item as a percentage of Total Assets.

### Step 6: Analyzing Significant Variations (>= 5%)
1. Navigate to **Significant Variations**.
2. Line items with period-over-period movements exceeding the active threshold are listed with their direction and risk level.
3. Click any row in the upper table to load the detailed breakdown in the lower panel.

### Step 7: Understanding "Possible Reasons"
- For every material variance, AI Auditor V8 provides professional explanations (e.g. *expansion of customer base*, *discounting to clear inventory*, *utilization of working capital overdraft limits*).
- **Rule of Professional Conduct**: These are explicitly labeled **POSSIBLE REASONS** and represent audit hypotheses. They are not confirmed facts until primary vouchers are examined.

### Step 8: Substantive Audit Verification Checklist
1. Navigate to **Audit Verification**.
2. Review the structured matrix of primary audit documents required for each significant variance (e.g. *Sales Ledger & GSTR-1 Reconciliation*, *Debtor Ageing*, *Bank Confirmations under SA 505*, *Fixed Asset Register*).
3. Read the **WHY Required** column to understand the specific audit objective (e.g. verifying revenue cut-off, testing for inventory obsolescence, or verifying ROC charge registration).
4. Use the checkboxes to mark documents as *Verified* as your audit testing progresses.

### Step 9: Reviewing Potential Risk Areas
1. Navigate to **Potential Risk Areas**.
2. Inspect flagged financial distress indicators (e.g. *Positive Net Profit with Negative Operating Cash Flow*, *Receivables Growth outstripping Sales*, *Negative Working Capital*, *High Financial Leverage*).
3. Review the severity rating and recommended audit response for each alert.

### Step 10: Exporting Excel & Word Audit Reports
1. Navigate to **Export Reports**.
2. **Excel Audit Workbook (.xlsx)**: Generates a complete 12-sheet workbook complete with freeze panes, borders, number formats (`#,##0.00`), and formatted summary tables.
3. **Word Audit Report (.docx)**: Generates a document containing a title page, executive summary, diagnostic tables, ratio scorecards, variance analyses, and the substantive audit checklist.
4. Click **Export**, select your destination folder, and open the file immediately upon completion.

---

## 5. Configuring Variance & Materiality Thresholds

You can customize the sensitivity of the analysis:
1. **Dynamic Filter**: On the *Significant Variations* page, adjust the **Variance Threshold** spinbox (e.g. change from 5.0% to 10.0%). The table and reasons will update instantly.
2. **Global Default Settings**: Navigate to **Settings** to update the default variance percentage, minimum materiality amount, and preferred currency unit.

---

## 6. Key Accounting & Audit Distinctions

To ensure compliance with statutory auditing standards, AI Auditor V8 maintains strict separation between four classes of information:

| Data Category | Definition | Presentation in AI Auditor V8 |
| :--- | :--- | :--- |
| **ACTUAL DATA** | Primary accounting numbers extracted from financial statements. | Displayed in black/bold in statements & data review grid. |
| **CALCULATED RESULTS** | Mathematically derived ratios, trends, and variances. | Displayed with formula transparency and units (%, x, days). |
| **POSSIBLE REASONS** | Objective hypotheses of operational or accounting causes. | Labeled *"Possible reasons may include..."* (non-conclusive). |
| **AUDIT VERIFICATION** | Documentary evidence required under SAs to confirm balances. | Formatted as a document checklist with *WHY Required* justifications. |

---

## 7. Common Errors & Troubleshooting

### 1. Excel File Header Not Detected
- **Cause**: The Excel file has extensive introductory notes or merged title banners.
- **Solution**: Open the file in Excel, ensure header labels like *Particulars*, *FY 2023-24*, *FY 2022-23* appear within the first 10 rows, or use the *Financial Data Review* page to verify extracted figures.

### 2. Scanned PDF Text Appears Garbled
- **Cause**: Low scan resolution (< 150 DPI) or skewed orientation.
- **Solution**: Ensure Tesseract OCR is installed on your Windows machine (`C:\Program Files\Tesseract-OCR\tesseract.exe`). Alternatively, review and correct the figures directly on the *Data Review & Mapping* page.

### 3. Missing Comparative Period
- **Cause**: Financial statement contains single-year figures only.
- **Solution**: The application will compute all standalone ratios for the single year. Variance and trend analysis will indicate that comparative prior-period data is required.

---

## 8. Statutory Disclaimer & Limitations

> **DISCLAIMER & LIMITATIONS:** This analytical report is generated by **AI Auditor V8** based strictly upon financial figures uploaded by the user and mathematical / financial calculations. All identified variations, interpretations, possible reasons, and suggested audit verification requirements are designed to assist in professional audit planning, credit appraisal, and financial review. They do **NOT** constitute a conclusive statutory audit opinion, proof of fraud, or legal finding. Independent verification of physical records, primary vouchers, bank statements, and statutory filings by a qualified Chartered Accountant or auditor is mandatory.
