# Corporate Credit Appraisal Engine (₹10-50 Cr facilities)

Streamlit dashboard that ingests 3 years of audited financials plus existing-debt and proposed-facility details,
computes the ratio set, scores the borrower (Grade A-E), tests NBFC policy guardrails on a pro-forma basis and drafts
the appraisal memo with covenants, DSRA, drawing-power and monitoring triggers.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
Pick a sample applicant in the sidebar (Strong / Moderate / Stressed) - or upload your own workbook.
Use *Download Excel template* in the sidebar to get the exact input layout.

## Layout
| File | Role |
|---|---|
| `appraisal/config.py` | Policy limits, scorecard weights/bounds, grade bands, RAG thresholds, formatters |
| `appraisal/ingestion.py` | Excel / CSV loading, schema + balance-sheet validation -> `ApplicantData` |
| `appraisal/sample_data.py` | 3 mock applicants (balanced statements) and the Excel template writer |
| `appraisal/ratios.py` | Derived line items and all profitability / liquidity / gearing ratios |
| `appraisal/exposure.py` | Existing-exposure profile, pro-forma metrics, stress grid, repayment schedule |
| `appraisal/scoring.py` | Weighted scorecard, grade overrides, policy-compliance checks |
| `appraisal/memo.py` | Recommendation engine, covenants, monitoring triggers, Markdown memo |
| `appraisal/charts.py` | Plotly figures |
| `app.py` | Streamlit UI (summary card + 4 tabs) |

## Input format (Excel, or CSVs whose file names contain the keyword)
Sheets: `Applicant` (incl. optional *Credit Bureau Score (300-900)*), `Proposed` (Field | Value), `BalanceSheet`, `PnL`, `CashFlow` (Line Item | FY1 | FY2 | FY3),
`ExistingDebt` (Lender, Facility Type, Sanctioned Limit, Outstanding, Interest Rate (%), Annual Principal, Annual Interest).
Units: ₹ Crore. Capex and Debt Repaid are positive numbers. Long-term borrowings exclude current maturities.

## Key definitions and assumptions (edit in `config.py` / `exposure.py`)
* EBITDA excludes other income. ICR = EBIT / finance costs. TNW = net worth - intangibles.
* DSCR = (EBITDA - Capex - Tax) / (Principal + Interest). Historical DSCR deducts actual capex; **pro-forma DSCR deducts
  maintenance capex (= depreciation)** because growth capex is assumed to be funded by the proposed loan.
* Pro-forma: lender-wise outstanding + new facility; latest-year EBITDA and TNW held flat; first full repayment year
  debt service; optional refinance portion retires existing debt pro-rata.
* Credit bureau score: optional input; scored within Scale & Vintage (25% of that pillar, 550 -> 0 pts, 800 -> 100 pts), soft policy check at >= 700. If blank it is skipped and weights re-normalise.
* Scorecard: Profitability 30 / Leverage 30 (pro-forma) / Liquidity 20 / Scale & Vintage 20, linear 0-100 per metric,
  +/-3 trend adjustment, grade A >=80, B >=65, C >=50, D >=35, else E. DSCR < 1.0x caps at D; negative TNW -> E.
* Decision: Decline (grade E, critical breach, or grade D with 2+ hard breaches) / Approve with covenants (no hard
  breach and grade A-B) / otherwise Refer to Credit Committee.

All thresholds are illustrative defaults; calibrate them to your Board-approved credit policy before any real use.
The output is decision support, not a substitute for credit-officer judgement, KYC/CIBIL checks or legal due diligence.
