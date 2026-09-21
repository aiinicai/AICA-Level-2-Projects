# MF X-Ray V1 — Testing Summary

**Project:** MF X-Ray — AI-Powered Mutual Fund Portfolio Intelligence & Risk Analysis System  
**Capstone:** ICAI AI Level 2 Capstone Project  
**Version:** V1.0  
**Testing Date:** 2026-09-16  
**Status:** ALL TESTS PASSED (14 Automated Unit & Integration Tests, 14 Screen GUI Verification)

---

## 1. Executive Summary

This testing summary validates the end-to-end functionality, mathematical integrity, risk models, AI explainability layer, report generation, and GUI stability of **MF X-Ray V1.0**.

All core calculations were verified against strict hand-calculated benchmarks (including the Section 35 reference test), and every graphical module was verified under both headless and interactive environments.

---

## 2. Test Execution Results

| # | Test Performed | Objective | Result | Notes / Validation Metrics |
|---|----------------|-----------|--------|----------------------------|
| 1 | **Application Startup & Metadata** | Verify version branding (`V1.0`), window title, subtitle, and disclaimer constants. | **PASS** | Title, headers, footers, and about sections correctly state V1.0 and disclaimer. |
| 2 | **Demo Portfolio Loading** | Validate default demo dataset (4 funds, ₹9,00,000 total investment). | **PASS** | Successfully parsed: Bluechip Equity (₹3.0L), Flexi Cap (₹2.5L), Growth Equity (₹2.0L), Mid Cap (₹1.5L). Allocations sum to 100.0%. |
| 3 | **Section 35 Worked Example Math** | Verify mathematical accuracy of look-through effective exposure formula. | **PASS** | Fund A (₹5L @ 10%) + Fund B (₹5L @ 8%) = ₹90,000 on ₹10L corpus $\rightarrow$ **9.0% effective exposure** confirmed. |
| 4 | **Effective Exposure Look-Through (Portfolio X-Ray)** | Verify underlying exposure aggregation and descending sorting across all companies. | **PASS** | Correctly aggregated overlapping stocks (e.g. Northbridge Bank: 6.70%, ₹60,300 across 3 funds; Bluepeak Software: 6.64%, ₹59,800). |
| 5 | **Fund Overlap Matrix & Pairs** | Check pairwise overlap calculation $\sum \min(w_{1,i}, w_{2,i})$, matrix symmetry, and 100% diagonal. | **PASS** | Symmetrical matrix validated; diagonals are 100.0%; sorted pairs identify high overlap pairs (e.g. Bluechip & Growth Equity). |
| 6 | **Sector Analysis** | Validate sector-wise exposure aggregation, descending ranking, and chart rendering. | **PASS** | Aggregates all underlying companies by sector. Donut chart and horizontal bar chart with concentration threshold line rendered. |
| 7 | **Risk Analysis & Sharpe Ratio** | Verify annualised volatility ($\sigma \times \sqrt{12}$), Sharpe ratio with configurable $R_f$, and max drawdown. | **PASS** | Volatility: 21.21%, Sharpe Ratio: 0.20 (at $R_f=6.0\%$), Max Drawdown: -27.10%. Dynamically recalculates when user edits $R_f$. |
| 8 | **Portfolio Health Score Breakdown** | Verify 0–100 score computation across 6 transparent components. | **PASS** | 6 components (Diversification: 14.7/20, Overlap: 16.3/20, Stock Concentration: 12.2/20, Sector Concentration: 11.1/15, Volatility: 5.9/15, Drawdown: 4.6/10) sum exactly to **65 / 100** (Moderate Risk). |
| 9 | **Rule-Based Alert Engine** | Test threshold-driven alerting for high overlap, stock concentration, sector concentration, and fund concentration. | **PASS** | Correctly triggers High and Medium severity alerts based only on calculated metrics; no false positive alerts. |
| 10 | **AI Explainability & Narrative** | Check synthesis of natural-language portfolio narrative. | **PASS** | Generates clear, plain-English summary. Verified absence of any unsolicited buy/sell/hold advice. |
| 11 | **Ask MF X-Ray NL Q&A Engine** | Test natural language questions: company lookups, concentration drivers, CA summary, overlap, sector, and invalid queries. | **PASS** | Correctly answers company holdings (e.g. "Which funds contain Northbridge Bank?"), explains concentration reasons, provides CA review, and states "Insufficient data" on non-portfolio queries without hallucinating. |
| 12 | **What-If Simulator** | Test hypothetical removal of a mutual fund and before/after comparison. | **PASS** | Accurately computes differential overlap, investment change, concentration shift, and updated Health Score. |
| 13 | **SIP Analysis & XIRR** | Verify monthly instalment cash flows, unit accumulation, current valuation, and numerical XIRR convergence. | **PASS** | 24-month SIP of ₹10,000 (₹2,40,000 invested) accurately solved using Newton-Raphson with bisection fallback. |
| 14 | **Excel Export (.xlsx)** | Verify generation of multi-tab formatted Excel workbook. | **PASS** | Generates all 11 formatted worksheets: Portfolio Summary, Fund Allocation, Fund Analysis, Underlying Holdings, Stock Exposure, Overlap Analysis, Sector Analysis, Risk Analysis, Alerts, AI Insights, Methodology. |
| 15 | **Word Report Export (.docx)** | Verify generation of formal Capstone-ready Word report. | **PASS** | Generates complete report with cover page, executive summary, overview tables, fund fact sheets, X-Ray tables, overlap matrix, risk section, health score, alerts, methodology, and statutory disclaimers. |
| 16 | **CSV Template Generation & Data Import** | Validate creation of import templates and CSV/Excel parsing. | **PASS** | Creates `template_fund_master.csv`, `template_holdings.csv`, `template_historical_nav.csv`. Imports and updates `COMPANY_SECTOR_MAP` and holdings. |
| 17 | **GUI Navigation & Layout Stability** | Test screen transitions across all 14 sidebar modules. | **PASS** | All 14 modules (Dashboard, My Portfolio, Fund Analysis, Portfolio X-Ray, Overlap Analyzer, Sector Analysis, Risk Analysis, Portfolio Changes, What-If Simulator, SIP Analysis, AI Insights, Reports, Data Management, About) render smoothly without Tkinter exceptions. |

---

## 3. Known Limitations & Architecture Notes for V2.0

1. **Synthetic Sample NAV History**:
   - *Limitation in V1:* As specified in the design guidelines, V1 operates offline with a synthetic 60-month monthly NAV history.
   - *Roadmap for V2:* An AMFI/NSE/BSE API connector or automated NAV downloader will be plugged into the data layer to replace synthetic prices with live daily NAVs.
2. **Simplified Portfolio Volatility**:
   - *Limitation in V1:* Portfolio-level volatility is computed as the investment-weighted average of individual fund volatilities (explicitly disclosed in the Methodology box).
   - *Roadmap for V2:* Full variance-covariance matrix taking cross-fund correlations into account.
3. **Factsheet Document Parsing**:
   - *Limitation in V1:* Factsheets are imported via structured CSV or Excel templates.
   - *Roadmap for V2:* Automated PDF factsheet extraction using computer vision / OCR and LLM RAG pipelines.
