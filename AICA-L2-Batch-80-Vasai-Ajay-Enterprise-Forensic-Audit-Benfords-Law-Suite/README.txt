================================================================================
ENTERPRISE FORENSIC AUDIT & BENFORD'S LAW SUITE
(INDIAN DIGITAL PERSONAL DATA PROTECTION ACT, 2023 COMPLIANT)
================================================================================

An elite, full-stack, standalone forensic audit platform engineered for senior
forensic auditors, chartered accountants, and fraud risk professionals in India.

--------------------------------------------------------------------------------
1. EXECUTIVE & FORENSIC METHODOLOGY OVERVIEW
--------------------------------------------------------------------------------

The suite pairs rigorous mathematical forensic accounting mechanics with an
airtight security, privacy, and governance shell strictly compliant with the
Indian Digital Personal Data Protection (DPDP) Act, 2023.

A. Benford's Law Statistical Mechanics (Nigrini Standards):
- First Digit (1D) Test: P(d1) = log10(1 + 1/d1) for d1 in {1, ..., 9}.
- Second Digit (2D) Test: P(d2) = sum_{d1=1..9} log10(1 + 1/(10*d1 + d2)) for d2 in {0, ..., 9}.
- First-Two Digits (F2D) Test: P(d12) = log10(1 + 1/d12) for d12 in {10, ..., 99} (Primary Forensic Audit Standard).
- First-Three Digits (F3D) Test: P(d123) = log10(1 + 1/d123) for d123 in {100, ..., 999}.
- Last-Two Digits (L2D / Number Uniformity) Test: Uniform P = 0.01 for d_last in {00, ..., 99} (Detects human fabrication & estimation heuristics).
- Mantissa Arc & Distribution Test: Fractional logarithm distribution with mean mantissa (~0.5000), variance (~0.08333), and center-of-gravity vector calculations.
- Nigrini Mean Absolute Deviation (MAD) Conformity Grading:
  * Close Conformity (<= 0.0012)
  * Acceptable Conformity (0.0012 - 0.0018)
  * Marginally Acceptable (0.0018 - 0.0022)
  * Non-Conforming / High Risk (> 0.0022)
- Statistical Goodness-of-Fit & Spike Alerts:
  * Yates Continuity Corrected Z-Score (Z > 1.96 at 95% confidence, Z > 2.576 at 99% confidence).
  * Chi-Square (chi2) statistic & p-value.
  * Kolmogorov-Smirnov (K-S) distance D vs. critical threshold D_crit = 1.36 / sqrt(N).
- Interactive Click-to-Drilldown: Clicking any digit bar instantly filters the underlying transaction table to those exact records.

B. Enterprise Forensic Anomaly Suite:
- Relative Size Factor (RSF): Ratio of largest payment to second-largest payment per vendor/account (RSF > 5.0 and > 10.0 flagged as high/critical outlier invoices).
- Duplicate Payment / Invoicing Finder: Exact match sets (Vendor + Amount + Invoice + Date) and fuzzy 30-day duplicates.
- Split Transactions / Smurfing Detector: Clustering within 10% below statutory limits (e.g. INR 45,000 - 49,999 for INR 50,000 PAN limit; INR 1,80,000 - 1,99,999 for INR 2,00,000 cash threshold; INR 9,50,000 - 9,99,999 for INR 10,00,000 TDS limit).
- Round Number Scanner: Multiples of INR 1,00,000, INR 50,000, INR 10,000, INR 1,000 provisions and estimates.
- Temporal Outliers: Weekend entries, Indian national statutory holidays (Jan 26, Aug 15, Oct 2), and March 31 fiscal year-end clustering.
- Multi-Factor Composite Risk Matrix: Synthesized 0-100 transaction risk scores with interactive drilldowns.

--------------------------------------------------------------------------------
2. INDIAN DPDP ACT, 2023 SECURITY & PRIVACY FRAMEWORK
--------------------------------------------------------------------------------

1. Role & Data Governance Mandate (Sec. 4 & 7):
   - Data Fiduciary & Data Processor structural separation.
   - Purpose Limitation: Processing restricted to statutory forensic audit & fraud detection.
   - Mandatory interactive legal disclaimer & consent agreement recorded prior to data ingest.
2. Data Minimisation, Pseudonymization & PII Scrubbing:
   - Aadhaar Numbers: 12-digit format verified with the authentic Verhoeff Checksum Algorithm (multiplication & permutation tables).
   - PAN (Permanent Account Number): Structure [A-Z]{5}[0-9]{4}[A-Z] with entity classification (Individual 'P', Company 'C', Firm 'F', etc.).
   - GSTIN: 15-character validation with 2-digit Indian State code mapping (01 to 38, 97, 99).
   - Bank Account & RBI IFSC Codes: Format verification.
   - Deterministic Salted HMAC-SHA256 Tokenization: Preserves relational grouping for RSF & duplicate analysis without exposing personal identities.
3. Human-In-The-Loop (HITL) External Gateway Policy:
   - Strict Air-Gapped / Zero-Egress execution by default.
   - All processing executed locally and in-memory.
4. Deterministic Telemetry & Audit Integrity:
   - SHA-256 dataset ingest fingerprinting.
   - Blockchain-style tamper-evident chained audit ledger with on-demand cryptographic verification.
   - Multi-format Courtroom & Audit Committee grade PDF report, detailed multi-tab Excel outcomes, Word dossier, and JSON DPDP certificate export.

--------------------------------------------------------------------------------
3. SUPPORTED INGESTION FORMATS
--------------------------------------------------------------------------------

The suite processes files or directories from anywhere on local drives or connected network UNC server paths (\\server\share\...):
- Spreadsheets: Excel (.xlsx, .xls, .xlsm)
- Word Documents: (.docx - structured tables & delimited paragraphs)
- PDF Documents: (.pdf - vector tables and digital text)
- Delimited Text: (.csv, .tsv, .psv, .txt, .log, .dat)
- Semi-Structured: (.json, .jsonl, .xml)
- High-Performance & DB: (.parquet, .sqlite, .db)

Diagnostic Limitation Handling: If a file is password-protected or contains image-only scanned pages without digital text/OCR, the suite presents an informative diagnostic banner with clear format recommendations.

--------------------------------------------------------------------------------
4. MULTI-TAB EXCEL OUTCOME WORKBOOK & AUDITOR SAMPLING GUIDE
--------------------------------------------------------------------------------

The Excel outcome workbook (/api/report/excel) is structured into dedicated institutional sheets:
1. Executive Summary & DPDP: Core metrics, dataset SHA-256 fingerprint, MAD rating, and DPDP compliance certifications.
2. Auditor Sampling Guide: Dedicated strategic manual grounding sampling rules in ICAI FAFD and AICPA standards (Tier 1 Mandatory 100% Review, Tier 2 Targeted Forensic Sample, Tier 3 Stratified Substantive Sample, with audit document checklists).
3. Master Sample Ledger: Consolidated, prioritized sampling list of all flagged transactions with Composite Risk Scores (0-100), primary triggers, and specific audit verification procedures.
4. Sampled - RSF Outliers: Complete list of highest-outlier payments for flagged vendors (RSF >= 5.0x and >= 10.0x).
5. Sampled - Duplicate Payments: Detailed transaction pairs for all exact and fuzzy 30-day duplicate invoices.
6. Sampled - Split Smurfing: All transactions clustered within 10% below statutory limits (PAN Rs.50k, Cash Rs.2L, TDS Rs.10L).
7. Benford F2D Digits Table: Complete 10-99 mathematical distribution table.
8. Chained Audit Trail: Complete cryptographic SHA-256 block chain journal with full timestamps, audit actions, user roles, event parameters, block hashes, previous block hashes, and validity status (only generated when audit blocks exist; never empty).

--------------------------------------------------------------------------------
5. HOW TO LAUNCH THE APPLICATION
--------------------------------------------------------------------------------

Executable Binary (.exe):
The compiled standalone Windows executable is named:
Enterprise_Forensic_Audit_and_Benfords_Law_Suite_v1.exe
Located at: dist\Enterprise_Forensic_Audit_and_Benfords_Law_Suite_v1\Enterprise_Forensic_Audit_and_Benfords_Law_Suite_v1.exe

One-Click Launch (Windows Batch):
Double click run_app.bat in the project root, or execute:
python run_app.py

The launcher initializes the air-gapped backend server and automatically opens the executive interface in your default web browser at http://127.0.0.1:8000.

--------------------------------------------------------------------------------
6. VERIFICATION & AUTOMATED TEST SUITE
--------------------------------------------------------------------------------

Run the complete test suite with pytest:
python -m pytest backend/tests -v

Verified Test Modules (22/22 Passed):
1. test_benford.py: Theoretical probabilities, geometric series back-test, uniform distribution rejection, Z-score spike detection, and Mantissa arc statistics.
2. test_dpdp.py: Aadhaar Verhoeff checksum algorithm, PAN entity parsing, GSTIN state mapping, Bank A/C & IFSC masking, HMAC-SHA256 tokenization, and HITL air-gap gateway.
3. test_forensic_tests.py: Relative Size Factor (RSF) outlier vendor detection, exact & fuzzy duplicates, split transaction smurfing below INR 50k, and round number anomalies.
4. test_audit_ledger.py: Genesis block creation, hash chaining continuity, and mathematical tamper detection.
5. test_data_loader.py: CSV, Excel, Word, PDF, JSON, XML, Parquet, and SQLite multi-format loading with column auto-discovery.
6. test_e2e_integration.py: End-to-end full audit pipeline back-test from consent declaration to PDF, Excel, and Word report generation, asserting all Excel sheets and populated audit trail blocks.

--------------------------------------------------------------------------------
7. COMPREHENSIVE PROJECT WORD DOCUMENTATION
--------------------------------------------------------------------------------

The root directory includes two comprehensive executive Word (.docx) documents:
1. Enterprise_Forensic_Audit_Implementation_Plan_Executed.docx: Complete detailed implementation plan and full technical lifecycle execution history.
2. Enterprise_Forensic_Audit_Tools_Libraries_Skills_Inventory.docx: Exhaustive inventory of all tools, backend/frontend libraries, agent skills, scripts, versions, update dates, and distribution sources.
================================================================================
