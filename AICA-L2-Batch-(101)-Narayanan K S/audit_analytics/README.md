# Audit Analytics & Journal Entry Testing Tool

A local, offline Python web application built for Indian Chartered Accountant (CA) firms to automate Journal Entry (JE) and voucher testing under **ICAI Standards on Auditing (SA 240, SA 315, SA 330, SA 500, SA 530)** and **CARO 2020**.

---

## 🏛️ Regulatory & Auditing Standards Addressed

1. **SA 240 (Auditor's Responsibilities Relating to Fraud in an Audit of Financial Statements)**
   - Mandatory management override testing procedures.
   - Analysis of high-risk, non-standard, post-closing, and round-sum journal entries.
2. **SA 315 & SA 330 (Risk Assessment & Audit Responses)**
   - Evaluation of IT general controls (ITGC), Segregation of Duties (SoD), and maker-checker anomalies.
   - Targeted substantive procedures for identified risk exceptions.
3. **SA 530 (Audit Sampling)**
   - Clear partitioning between non-statistical targeted testing (Stratum 1 & 2) and representative sampling (Stratum 3).
4. **CARO 2020 Reporting Considerations**
   - Clause 3(ix): Scrutiny of borrowings and fund diversion.
   - Clause 3(viii): Surrendered undisclosed transactions.
   - Clause 3(ii): Inventory / working capital book entry discrepancies.
   - Clause 3(xi): Whistle-blower complaints and fraud reporting.

---

## 🚀 Quick Start Guide (Windows)

Launch the application with the following standard commands:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

*Note: The application executes entirely offline on your local Windows workstation. No client data, trial balances, or general ledgers are transmitted to any cloud API or external service.*

---

## 🛠️ Key Capabilities & Features

### A. Engagement Setup & Materiality Configuration
- Configures Entity Name, Financial Year (April - March cycle), Preparer, and Reviewer.
- Sets and strictly validates the **SA 320 Materiality Hierarchy**:
  - **Overall Materiality (OM)**: Financial statements as a whole.
  - **Performance Materiality (PM)**: High-value JE cutoff benchmark (50% - 75% of OM).
  - **Clearly Trivial Threshold (CTT)**: De-minimis threshold (1% - 5% of OM).

### B. Intelligent Ingestion & Data Reconciliation
- Imports client GL / JV dumps from **Tally Prime, Zoho Books, SAP, Oracle, Busy**, etc. (CSV, XLSX, XLS).
- Built-in heuristic auto-mapping with interactive verification.
- **Strict Data Integrity Diagnostics**:
  - Source Row Reference tracking (Row index in client spreadsheet).
  - Debit-Credit trial balance reconciliation with unbalanced voucher detection.
  - Missing account heads, invalid dates, and out-of-period entries detection.
  - **Zero silent data alteration**: Missing numbers or invalid values are never silently coerced to zero.
- **Synthetic Indian GL Dataset Generator**: Generate 350+ authentic entries with one click for testing and demo.

### C. 10 Automated Red-Flag Journal Entry Tests
1. **Sunday Postings**: Entries passed on weekly non-business days.
2. **Off-Hours Postings**: Entries keyed outside standard office hours.
3. **Post-Year-End Backdated Cutoff**: Entries dated $\le$ 31 March posted post balance-sheet date.
4. **Round-Value Transactions**: Lump-sum multiples of ₹1,00,000, ₹5,00,000, etc.
5. **Below Authorization Ceiling**: Transactions structured just below approval thresholds (e.g. within 5% of ₹5L, ₹10L).
6. **Blank or Generic Narrations**: Entries with non-descriptive remarks ("Being entry passed", "Misc").
7. **Suspicious Audit Keywords**: Flags terms like *adjustment, rectification, dummy, urgent, suspense, plug, verbal instruction*.
8. **Exceeding Performance Materiality (PM)**: 100% substantive sample candidate for material entries.
9. **Sensitive / Suspense Account Impacts**: Scrutinizes Cash, Bank, Suspense, Director Loan/Advance accounts.
10. **Admin / Segregation of Duties (SoD) Anomalies**: Privileged system postings or Maker == Checker entries.

### D. Benford's Law First-Digit Analysis (Digits 1–9)
- Evaluates empirical first-digit frequencies against the theoretical logarithmic distribution $P(d) = \log_{10}(1 + 1/d)$.
- Calculates $\chi^2$ (Chi-square) goodness-of-fit statistic and $p$-value at $\alpha = 0.05$.
- Highlights ICAI auditor cautionary notes emphasizing that deviations guide targeted scrutiny and do not constitute proof of fraud.

### E. Stratified Audit Sampling & Auditor Review Schedule
- **Stratum 1**: 100% of items exceeding PM (Material items).
- **Stratum 2**: Targeted high-risk anomalies flagged by testing.
- **Stratum 3**: Representative random sample from remaining population without duplicates.
- Editable audit review fields for **Auditor Observations, Management Explanation, Supporting Document Ref, Tick Marks (`^, V, B, A, C, T`), and Review Status**.

### F. Professional CA Deliverables
1. **Excel Work Paper Package (`WP_JE_Testing_FY202X-XX.xlsx`)**:
   - `Index & Objective`: Engagement meta, materiality table, SA 240 mandate, tick mark legend.
   - `Methodology & Criteria`: Red-flag logic and mandated audit procedures.
   - `Testing Summary`: Population reconciliation and risk classification summary.
   - `Sample Testing Schedule`: Formatted vouching schedule with freeze panes, auto-filters, INR formatting (`₹ #,##,##0.00`), and Excel `=SUM()` formulas.
   - `Benford Analysis`: Tabular digit counts, deviations, and statistical test parameters.
2. **PDF Audit Conclusion Memo (`Audit_Conclusion_Memo_JE_FY202X-XX.pdf`)**:
   - Formal memo with running headers/footers (`NumberedCanvas` Page X of Y), confidentiality banners, CARO 2020 clause assessment, and auditor sign-off section.
   - Auditor conclusion choices: *Satisfactory, Unresolved Exceptions, Potential Material Misstatement, Inconclusive*.

---

## 🧪 Running Automated Tests

```bash
python -m pytest audit_analytics/tests/test_analytics.py -v
```
All unit tests validate data parsing, materiality checks, 10 JE test scenarios, Benford distribution, sampling mechanics, Excel generation, and PDF compilation.
