# Red Flag Engine — Forensic Accounting & Fraud Risk Engine

A deterministic forensic accounting fraud-risk engine for Indian statutory and internal audit, grounded in the Institute of Chartered Accountants of India (ICAI) Board of Studies curriculum and Forensic Accounting and Investigation Standards (FAIS).

---

## 1. What This Is

Red Flag Engine is an analytical platform for statutory auditors, forensic practitioners, and internal audit teams examining Indian corporate entities. The auditor ingests three or more years of a company's trial balance in Excel or PDF format; the engine validates arithmetic integrity, derives standardized Balance Sheet, Profit & Loss, and Indirect Cash Flow statements, and executes 44 deterministic risk rules and 4 published forensic models (Beneish M-Score, Altman Z"-Score, Sloan Accrual Ratio, and Piotroski F-Score). Results are scored, weighted by materiality and governance factors, categorized into Red / Yellow / Green risk buckets, and exported as an eleven-sheet audit working paper and a formal client Evidence Requisition List. **It establishes predication, not findings.**

---

## 2. Running It

### Windows — one click

Double-click **`run_app.bat`**. The app opens in your browser at
`http://localhost:8501`.

The window that stays open **is the server** — it prints an ordinary startup
log, not an error, and the app stops when you close it. Press Ctrl+C there when
you have finished.

The batch file does one thing only: find a Python that starts, and hand over to
`scripts/launch.py`, which handles everything else:

* **Interpreter choice is by capability, never by version.** If the Python you
  already have can import the dependencies, it launches straight away. If
  nothing can, it builds a private `.venv`, installs into it, verifies every
  package imports, and only then starts the server.
* **It opens the browser itself**, after polling until the server actually
  answers. Streamlit's own auto-open does not always fire, and when it does not
  you are left looking at a console log with no window.
* **It picks a free port.** If 8501 is occupied — usually a Streamlit left
  running from an earlier attempt — it moves to the next one and tells you.
* **It writes `~/.streamlit/credentials.toml`** on first run if that file is
  missing. Streamlit otherwise prints a welcome banner and blocks on standard
  input asking for an email address, which in a double-clicked window looks
  exactly like a hang. Note that Streamlit reads that file from your home
  directory, not from the project's own `.streamlit` folder.

Every run writes `launch_log.txt`, and the window never closes on an error.

### If it will not start

Double-click **`diagnose.bat`** (or run `python scripts/doctor.py`). It reports
the interpreter, every missing or broken dependency, missing project files,
engine import failures, whether Streamlit can serialise a dataframe for
display, and an end-to-end analysis of the sample data. The report is written
to `diagnostic_report.txt`. Send that file along with `launch_log.txt`.

### Any platform

```bash
pip install -r requirements.txt          # core; camelot is deliberately excluded
python scripts/launch.py                 # or: python -m streamlit run app.py
```

`requirements-optional.txt` holds `camelot-py`, a secondary PDF table-extraction
path that needs OpenCV and Ghostscript. It is optional by design — a camelot
build failure must never stop the application from launching.

### Python versions

Verified on **Python 3.10** (Linux) and **Python 3.14.4** (Windows 11), with
Streamlit 1.62, pandas 3.0 and numpy 2.5. There is no version gate. An earlier
launcher rejected 3.14 on the assumption that Streamlit's wheel chain did not
support it; that assumption was wrong and the gate stopped the app from
starting on a machine where everything worked. Capability is tested, not
inferred.

### Walking through the app

1. **Engagement Setup** — client, materiality, predication note. *Load demo
   engagement* pre-fills a worked example.
2. **Upload & Verify** — upload the trial balances, or *Load sample trial
   balance*. Files are SHA-256 hashed; each year's Dr = Cr is verified.
3. **Governance Assessment** — 15 fraud-risk factors, or skip and record
   "not assessed".
4. **Findings & Audit Leads** — the lead sheet, grouped by ledger.
5. **Export & Requisition** — Excel working paper, Evidence Requisition List,
   chain-of-custody JSON, saved engagement parameters.

---

## 3. How Findings Are Presented and Scored

### The lead sheet

Exceptions are **de-duplicated** on (rule × subject) — the same rule firing on
the same ledger in FY22, FY23 and FY24 is one audit finding with a recurrence
count, not three. Rules that fire on very many ledgers are **systemic
observations**, so only the highest-scoring subjects per rule reach the lead
sheet (default 15, adjustable on Screen 1); the remainder are counted,
disclosed on screen and exported in full to the working paper's `Suppressed`
sheet. Nothing is silently dropped.

On the reference dataset this takes **1,103 raw instances → 424 de-duplicated
findings → 125 audit leads across 110 ledgers**, presented one row per ledger
and paginated 20 at a time.

### The entity risk score

The score is the weighted proportion of the executed rule battery that fired,
scaled by monetary materiality and pervasiveness:

```
entity_score = 100 × Σ(weight × confidence × materiality × pervasiveness)
                     ─────────────────────────────────────────────────────
                            Σ(weight × confidence) over executed rules
```

* **materiality** = min(1, exception value ÷ performance materiality). Structural,
  non-monetary exceptions carry a fixed 0.5.
* **pervasiveness** ∈ [0.70, 1.00] — a rule hitting many distinct ledgers weighs
  more than one isolated hit.
* **governance overlay** — a bounded ×0.85 – ×1.15 multiplier from the Screen 3
  questionnaire. It never creates or removes a finding.

Buckets: **≥ 40 RED · 18 – 40 YELLOW · < 18 GREEN**.

Because the score is a bounded proportion rather than an unbounded sum, it is
comparable between engagements and between years, and every component is
reproduced in the working paper's `Rule_Contributions` sheet.

### Green flags

Positive indicators are scored on their own 0 – 100 scale and are **never
netted** against the risk score.

---

## 4. Input Requirements

The engine enforces strict data integrity constraints:
- **File Format**: Strictly `.xlsx`, `.xls`, and text-based `.pdf`. (CSV, JSON, and XML upload paths are disallowed).
- **Time Horizon**: **3 financial years minimum** (e.g. FY22, FY23, FY24). The engine refuses to score fewer than 3 years to preserve longitudinal validity.
- **Mandatory Opening Balances**: Opening debit and credit balances are mandatory to derive Indirect Operating Cash Flow (`cfo_indirect`).
- **Schedule III Classification**: Every ledger must have an assigned Schedule III Primary Group (or standard Tally hierarchy).
- **Chain of Custody**: The original file is hashed (SHA-256) on arrival and never modified.

---

## 5. Coverage Table

Generated from `rules/methods_registry.yaml` via `scripts/gen_coverage_doc.py`:

| Method ID | Method Name | Status | Prerequisites | Min Years | Min Records | Associated Rules |
|---|---|---|---|---|---|---|
| **M-01** | Benford's Law (first digit) | `implemented` | `trial_balance` | 1 | 300 | TB-12 |
| **M-02** | Round-number test | `implemented` | `trial_balance` | 1 | — | TB-04 |
| **M-03** | Relative size factor | `implemented` | `trial_balance` | 1 | — | TB-13 |
| **M-04** | Z-score outlier analysis | `implemented` | `trial_balance` | 3 | — | LG-04 |
| **M-05** | IQR robust outliers | `implemented` | `trial_balance` | 1 | — | TB-13, LG-04 |
| **M-06** | Horizontal / vertical / common-size analysis | `implemented` | `trial_balance` | 2 | — | FS-04, FS-05, FS-06, LG-06 |
| **M-07** | Ratio analysis vs peer benchmarks | `implemented` | `trial_balance, peer_ratios` | 1 | — | FS-02, FS-03 |
| **M-08** | Beneish M-Score | `implemented` | `trial_balance` | 2 | — | MS-01 |
| **M-09** | Altman Z-Score | `implemented` | `trial_balance` | 1 | — | MS-02 |
| **M-10** | Sloan accrual ratio | `implemented` | `trial_balance` | 1 | — | MS-03 |
| **M-11** | Piotroski F-Score | `implemented` | `trial_balance` | 2 | — | MS-04 |
| **M-12** | Isolation Forest | `implemented` | `trial_balance` | 1 | 100 | Unsupervised / Model |
| **M-13** | Local Outlier Factor | `implemented` | `trial_balance` | 1 | 100 | Unsupervised / Model |
| **M-14** | Fuzzy name matching | `implemented` | `trial_balance` | 1 | — | TB-06 |

---

## 6. ICAI Mapping

Every deterministic rule maps directly to ICAI Board of Studies curriculum references:

- **Module TB (Trial Balance Structure — 14 Rules)**:
  - `TB-01`: ICAI Ch. 6.1.1 — Trial balance arithmetic inaccuracy
  - `TB-02`: ICAI Ch. 6.1.1 — Abnormal debit or credit balances
  - `TB-03`: ICAI Ch. 6.1.1 — Unreconciled subsidiary and general ledger suspense accounts
  - `TB-04`: ICAI Ch. 6.1.1 — Round-tripping and estimated balances
  - `TB-05`: ICAI Ch. 6.1.1 — Sundry and miscellaneous accounts masking leakage
  - `TB-06`: ICAI Ch. 6.1.2 — Duplicate vendor or customer masters / shell companies
  - `TB-07`: ICAI Ch. 6.1.1 — Passthrough and round-tripping accounts
  - `TB-08`: ICAI Ch. 6.1.1 — Personal expenses or unverified individual contractors
  - `TB-09`: ICAI Ch. 6.1.1 — Misclassification of accounts
  - `TB-10`: ICAI Ch. 6.1.1 — Inflated cash in hand masking unrecorded drawings
  - `TB-11`: ICAI Ch. 4.2.2 / Ch. 6.1.1 — Related party asset diversion
  - `TB-12`: ICAI Ch. 6.2.1 — Benford's Law first-digit digital analysis
  - `TB-13`: ICAI Ch. 6.2.2 — Relative Size Factor outlier detection
  - `TB-14`: ICAI Ch. 6.1.1 — Matched circular turnover

- **Module LG (Ledger Trend Across Years — 10 Rules)**:
  - `LG-01`: ICAI Ch. 6.1.1 — Sudden appearance of material new balances
  - `LG-02`: ICAI Ch. 6.1.1 — Unexplained disappearance of major assets or balances
  - `LG-03`: ICAI Ch. 6.1.1 — Reversal of normal debit/credit posture
  - `LG-04`: ICAI Ch. 6.2.2 — Cohort Z-score growth anomaly
  - `LG-05`: ICAI Ch. 6.1.1 — Stagnant / non-moving overdue balances
  - `LG-06`: ICAI Ch. 6.1.1 — Disproportionate expenditure surge
  - `LG-07`: ICAI Ch. 6.1.1 — Multi-year circular trading pattern
  - `LG-08`: ICAI Ch. 6.1.1 — Temporary window dressing spike and reversal
  - `LG-09`: ICAI Ch. 6.1.1 — Progressive expansion of unclassified expenditure
  - `LG-10`: ICAI Ch. 6.1.1 — Customer concentration and credit risk accumulation

- **Module FS (Statement Level — 16 Rules)**:
  - `FS-01`: ICAI Ch. 4.2.2 Scheme 1 / Ch. 6.1.1 — Earnings quality disconnect
  - `FS-02`: ICAI Ch. 6.1.1 — Performance 'too good to be true'
  - `FS-03`: ICAI Ch. 6.1.1 — Financial ratio peer benchmark deviation
  - `FS-04`: ICAI Ch. 4.2.2 Scheme 1 / Ch. 6.1.1 — Fictitious revenues & channel stuffing
  - `FS-05`: ICAI Ch. 4.2.2 Scheme 4 — Overstatement of inventory
  - `FS-06`: ICAI Ch. 6.1.1 — Sudden margin volatility
  - `FS-07`: ICAI Ch. 6.1.1 — High earnings volatility
  - `FS-08`: ICAI Ch. 4.2.2 Scheme 3 — Improper capitalisation of operating expenses
  - `FS-09`: ICAI Ch. 4.2.2 Scheme 3 / Ch. 6.1.1 — Idle or fictitious capital expenditure
  - `FS-10`: ICAI Ch. 4.2.2 Scheme 3 — Revaluation reserve manipulation
  - `FS-11`: ICAI Ch. 4.2.2 Scheme 10 / Ch. 6.1.1 — Related party transactions
  - `FS-12`: ICAI Ch. 6.1.1 — Deteriorating working capital debt coverage
  - `FS-13`: ICAI Ch. 4.2.2 Scheme 1 — Premature revenue recognition
  - `FS-14`: ICAI Ch. 6.1.1 — Financial reporting period & ratio irregularities
  - `FS-15`: ICAI Ch. 6.1.1 — Chronic prior period error corrections
  - `FS-16`: ICAI Ch. 4.2.2 Scheme 6 — Cookie-jar provisioning & earnings smoothing

- **External Models (4 Published Academic Models)**:
  - `MS-01`: Beneish M-Score (1999) — 8-variable probabilistic earnings manipulation index
  - `MS-02`: Altman Z"-Score (1983/2000) — Private non-manufacturing distress model
  - `MS-03`: Sloan Accrual Ratio (1996) — Balance sheet accrual quality evaluation
  - `MS-04`: Piotroski F-Score (2000) — Fundamental financial health vs growth divergence

---

## 7. Methods Evaluated and Rejected

These 13 forensic methods were evaluated against trial-balance constraints and deliberately rejected. No stubs, dead code, or placeholder functions exist in the codebase:

| Method ID | Method Name | Why Blocked on Trial Balance | What Dataset Unlocks It |
|---|---|---|---|
| **M-15** | Benford 2nd-digit / first-two-digits | Requires ~1,000+ values; a typical SME trial balance has 300-800 | Day Book / Voucher Register |
| **M-16** | Last-two-digits test | Requires 1,000+ individual amounts | Day Book |
| **M-17** | Number duplication test | Each ledger carries exactly one balance | Day Book |
| **M-18** | Gap and sequence analysis | No sequential document numbers in a trial balance | Day Book with voucher / invoice / cheque numbers |
| **M-19** | Regression expectation modelling | Three annual observations cannot support a regression | Monthly trial balances (36 observations) |
| **M-20** | Correlation break analysis | Three points cannot establish a correlation | Monthly trial balances for 2+ years |
| **M-21** | Dechow F-Score | ~80% overlapping with Beneish M-Score; excluded as redundant | Nothing — a deliberate design choice |
| **M-22** | One-Class SVM | Adds nothing over Isolation Forest at this data volume | Nothing — a deliberate design choice |
| **M-23** | DBSCAN clustering | Clusters of ledger balances carry no audit meaning | Day Book + vendor master, to cluster counterparties by behaviour |
| **M-24** | Autoencoder reconstruction error | ~400 rows and ~6 features would memorise rather than learn | 10,000+ transaction rows with 20+ features |
| **M-25** | Supervised classification | No labelled fraud outcomes exist | Historical confirmed fraud cases, tagged |
| **M-26** | NLP on narrations | A trial balance has no narration field | Day Book |
| **M-27** | Network / graph analysis | No counterparty-to-counterparty links in a trial balance | Day Book with both sides of each entry |

---

## 8. Results on the Synthetic Dataset

Evaluated on `data/sample/sample_tb_FY22_FY24.xlsx` containing 10 planted manipulations:

| # | Planted Manipulation | Target Rule | Detection Status |
|---|---|---|---|
| 1 | Suspense A/c left with ₹18.4L closing balance in FY24 | `TB-03` | **FOUND [OK]** |
| 2 | Near-duplicate creditor ledgers: `Shreeji Enterprises` and `Shreeji Enterprise` | `TB-06` | **FOUND [OK]** |
| 3 | `Sundry Creditors — Ravi Trading Co` with ₹4.2Cr turnover both sides, nil closing | `TB-07`, `TB-14`, `LG-07` | **FOUND [OK]** |
| 4 | `Consultancy Charges` grows 180% FY22→FY24 while revenue grows 12% | `LG-06` | **FOUND [OK]** |
| 5 | New ledger `Bhavya Marketing Pvt Ltd` appears only in FY24 with ₹1.1Cr debit | `LG-01` | **FOUND [OK]** |
| 6 | Receivables inflated 45% in FY24 against 12% revenue growth | `FS-04`, `MS-01` | **FOUND [OK]** |
| 7 | ₹2.6Cr of expenses capitalised into CWIP with flat revenue | `FS-08` | **FOUND [OK]** |
| 8 | Fixed asset additions of ₹2.1Cr with no revenue increase from them | `FS-09` | **FOUND [OK]** |
| 9 | PAT positive all three years, operating cash flow negative in FY23 and FY24 | `FS-01`, `MS-03` | **FOUND [OK]** |
| 10 | `Sundry Debtors — Kirit & Sons` carries identical balance ₹31.5L across all 3 years | `LG-05` | **FOUND [OK]** |

### Detection and noise

| Measure | Value |
|---|---|
| Planted manipulations detected **on the presented lead sheet** | **10 / 10 (100%)** |
| Raw exception instances generated | 1,103 |
| After de-duplication on (rule × subject) | 424 |
| Audit leads presented, across 112 ledgers | **125** |
| Suppressed as systemic (exported, not hidden) | 299 |
| Entity risk score (governance not assessed) | **42.8 / 100 — RED** |

De-duplication and per-rule suppression cut what the auditor reads by **89%**
without losing a single planted manipulation: every one of the ten survives
onto the lead sheet, not merely into the raw exception set.

An analytical red-flag engine is deliberately high-recall — it casts a wide net
across ~437 accounts so that nothing material is missed. The lead sheet, the
per-rule cap and the ranking are what convert that recall into a day's work
rather than a week's.

---

## 9. Scope and Limitations

> This engine analyses balance-level data. It addresses **financial statement fraud** directly; it detects **corruption** only through its shadow in the accounts, and **asset misappropriation** largely not at all, since those are transaction-level events. Of the 22 financial statement fraud schemes in ICAI Chapter 4.2.2, 13 are directly detectable here, 6 leave a detectable shadow, and 3 are out of reach without transaction data.
>
> Every rule is a heuristic. On real data the false-positive rate is high, by design — in fraud risk assessment the cost of a missed indicator exceeds the cost of an unnecessary look. Thresholds should not be tuned until the output looks clean. A tool that flags nothing is not a good tool; it is a broken one.

---

## 10. Legal Framework

- **Companies Act, 2013**:
  - Section 447 (Punishment for Fraud)
  - Section 143(12) & Rule 13 (Statutory Auditor Duty to Report Fraud)
  - Section 36 (Inducement to Invest)
- **Standards on Auditing (SA)**: SA 240 (*The Auditor's Responsibilities Relating to Fraud in an Audit of Financial Statements*)
- **ICAI FAIS Standards**: FAIS 130 (*Predication*), FAIS 140 (*Professional Skepticism*), FAIS 210/220
- **Companies (Auditor's Report) Order, 2020 (CARO 2020)**
- **RBI Master Directions on Frauds** (DBS.CO.CFMC.BC.No.1/23.04.001/2016-17)
- **Insolvency and Bankruptcy Code, 2016 (IBC)**: Preferential, Undervalued, Fraudulent, and Extortionate (PUFE) transactions (ss. 43, 45, 49, 50, 66)
- **Bharatiya Sakshya Adhiniyam, 2023**: Electronic records admissibility (replaces the Indian Evidence Act, 1872 from 1 July 2024; the ICAI study material still cites the 1872 Act).

---

## 11. Disclaimer

This application is an academic capstone and decision-support tool. It is not a substitute for professional audit judgment, forensic inquiry, or legal determinations. Red flags and statistical exceptions generated by this engine do not constitute evidence that an offense has occurred.
