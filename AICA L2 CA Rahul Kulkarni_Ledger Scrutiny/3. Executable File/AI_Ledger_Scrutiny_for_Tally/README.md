# AI Ledger Scrutiny Assistant for Tally
**Capstone Project – ICAI AI Level 2 (AICA)**
**Prepared by:** CA Rahul Kulkarni

---

## 1. Problem statement
In audit firms, article assistants and accounts staff post thousands of vouchers in Tally.
During statutory and tax audits, the auditor has to scrutinise every ledger by hand to find
cash payments above limits, missing TDS, duplicate bills, wrong classification, entries in
suspense, and so on. This takes a lot of time, depends on the person doing it, and items get
missed when volumes are high.

## 2. Solution
A Python web app (Streamlit) that:
1. **Connects directly to Tally** (TallyPrime / Tally.ERP 9) through Tally's built-in XML
   server on port 9000. It pulls groups, ledgers and every voucher for the audit period, so
   no manual export is needed. It can also read a Day Book XML file exported from Tally,
   or run on built-in demo data.
2. **Applies 16 audit and Income-tax rules** to every ledger line.
3. **Uses AI / analytics:** an Isolation Forest machine-learning model, Benford's Law and
   statistical outliers flag unusual entries that fixed rules cannot catch.
4. **Produces an audit working paper in Excel.** Exceptions are colour-coded by severity,
   and the paper has a summary, a sheet for each high-risk rule, Benford results and the AI
   anomalies, with space for preparer and reviewer sign-off.

## 3. Scrutiny rules implemented
| ID | Check | Reference | Severity |
|----|-------|-----------|----------|
| R01 | Cash payment > ₹10,000 to a person in a day (split payments are added together) | Sec 40A(3), Rule 6DD | High |
| R02 | Cash receipt ≥ ₹2,00,000 from a person in a day | Sec 269ST / 271DA | High |
| R03 | Loan or deposit accepted/repaid in cash ≥ ₹20,000; loans given in cash | Sec 269SS / 269T | High |
| R04 | Negative cash balance on any day | SA 500, CARO | High |
| R05 | Entries dated on Sundays or holidays | Unusual timing | Low |
| R06 | Round-sum amounts (estimates or provisions) | Audit judgement | Low |
| R07 | Possible duplicate entries; duplicate voucher numbers | Occurrence / internal control | Medium |
| R08 | Missing or weak narration | SA 230 documentation | Low |
| R09 | TDS not deducted: 194C, 194J, 194I, 194H (single and aggregate limits per payee) | Sec 40(a)(ia) | High |
| R10 | Possibly disallowable items (penalty, fine, donation, personal, interest on TDS/GST…) | Sec 37(1), 40(a)(ii), 43B | Medium |
| R11 | Cash or bank used in a Journal voucher | Internal control | Medium |
| R12 | Material entries (≥ materiality) for 100% vouching | SA 320 | Info |
| R13 | Entries outside the audit period, future-dated, or without a date | Cut-off | Medium/High |
| R14 | Entries in a Suspense account | Unexplained items | High |
| R15 | Debtors with credit balance / creditors with debit balance | Schedule III classification | Low |
| R16 | Amount far above that ledger's normal level (z-score) | SA 520 analytical review | Medium |
| R17 | **AI-detected anomaly (Isolation Forest)** | Machine learning | Medium |
| – | **Benford's Law first-digit test** (MAD with Nigrini thresholds) | Fraud analytics | Summary |

All limits are in `config.py` and can also be changed from the sidebar.

## 4. AI component (how the model works)
- **Model:** Isolation Forest (scikit-learn). This is unsupervised learning, so no labelled
  "fraud" data is needed.
- **Features for each entry:** log of amount, weekday, day of month, how rarely the ledger is
  used, z-score of the amount within its ledger, round-figure flag, narration length and
  voucher type.
- The model learns what is normal for this company and gives each entry an anomaly score.
  The top ~2% (adjustable) are flagged, each with a plain-English reason such as "amount
  much higher than usual for ledger; rarely used ledger; Sunday entry". This makes the
  result explainable to the auditor.
- **Benford's Law** tests whether the first digits of the amounts follow the natural pattern.
  A large deviation suggests manipulated or invented figures.
- **Human in the loop:** the app only flags entries. The auditor reviews them and makes the
  final judgement, as SA 200 requires professional judgement.

## 5. Architecture
```
Tally (port 9000) ──XML/HTTP──► tally_connector.py ──► DataFrames (groups, ledgers, entries)
                                                             │
                     config.py (limits) ──► scrutiny_engine.py (16 rules + Benford + AI)
                                                             │
                                  app.py (Streamlit dashboard) ──► report.py (Excel working paper)
```
| File | Purpose |
|------|---------|
| `app.py` | Web dashboard: data source, period, thresholds, tabs, downloads |
| `tally_connector.py` | Sends XML requests to Tally and parses vouchers, ledgers and groups; also reads XML files |
| `scrutiny_engine.py` | All audit rules, Benford test, Isolation Forest model |
| `config.py` | Thresholds, TDS limits, keywords |
| `report.py` | Builds the formatted Excel working paper |
| `demo_data.py` | Sample company with deliberate errors, for demonstration and the viva |
| `requirements.txt` | Python libraries |
| `Start_Ledger_Scrutiny.bat` | One-click launcher for Windows (installs libraries, starts the app) |

## 6. How to run
**Quick start (evaluators):** install Python 3.10+ (tick "Add Python to PATH"), then
double-click **`Start_Ledger_Scrutiny.bat`**. It installs the libraries on first run and
opens the app in the browser. Choose **Demo data** → **Run Ledger Scrutiny** to see the
full output without Tally.

**Manual steps:**

**Step 1. Install Python 3.10 or later** from python.org (tick "Add Python to PATH").

**Step 2. Install the libraries.** Open Command Prompt in this folder and run:
```
pip install streamlit pandas numpy requests openpyxl scikit-learn
```

**Step 3. Turn on Tally's XML server.**
- *TallyPrime:* F1 (Help) → Settings → Connectivity → Client/Server configuration →
  set *TallyPrime is acting as* = **Both**, *Port* = **9000**. Restart Tally.
- *Tally.ERP 9:* Gateway → F12 Configure → Advanced Configuration → Client/Server =
  **Both**, Port = **9000**.
- Open the company you want to audit.
- Check it works: open `http://localhost:9000` in a browser. It should show
  *"TallyPrime Server is Running"*.

**Step 4. Start the app:**
```
streamlit run app.py
```
The app opens in the browser. Choose **Tally (live)** → *Test connection* → pick the company
→ set the period → **Run Ledger Scrutiny**. To try the app first without Tally, choose
**Demo data**.

**If live connection is not possible:** in Tally go to Day Book → set the period to the full
year → Alt+E Export → Format = XML. Then upload that file under **Upload Tally XML**.

## 7. Output
- Dashboard: counts of vouchers and exceptions (High/Medium), and a Dr = Cr check.
- Tabs: Summary, Exceptions (filter and search), AI anomalies, Benford chart, Cash book
  chart, Ledger viewer with running balance.
- Downloads: **Excel audit working paper** and an exceptions CSV.

## 8. Benefits
- A full-year ledger scrutiny takes minutes instead of days, and every entry is checked
  (100% coverage instead of sampling).
- The same checks run the same way for every client and every staff member.
- The Excel output is a ready audit trail and documentation (SA 230).
- Findings feed directly into Form 3CD clauses: 21(a) disallowances, 21(b) 40A(3),
  31 (269SS/269T/269ST) and 34 TDS.

## 9. Limitations and future scope
- The rules flag *possible* issues. Exemptions (Rule 6DD, lower-deduction certificates,
  PAN and threshold status of the payee) must be checked by the auditor.
- Payee-wise TDS aggregation depends on the party ledger being selected in the voucher.
- Possible additions: GSTR-2B reconciliation, 43B(h) MSME payment-delay check,
  alteration/audit-trail log analysis (Rule 3(1) of the Companies (Accounts) Rules),
  LLM-generated draft audit queries, and a multi-company batch run.

## 10. Data security
All processing runs **locally** on the auditor's computer. Tally data is not uploaded
anywhere.

*Thresholds reflect the Income-tax Act, 1961 as amended for FY 2025-26. Verify them against
the current law before use.*
