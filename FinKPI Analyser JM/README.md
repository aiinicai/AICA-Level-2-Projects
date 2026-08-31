# 📊 FinKPI Analyzer — Enterprise Financial & KPI Analytics Platform

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)
![React](https://img.shields.io/badge/Frontend-React%20%2B%20TailwindCSS-indigo)
![License](https://img.shields.io/badge/License-MIT-orange)

An end-to-end financial analytics solution designed to process multi-period Trial Balance data, calculate 40+ Financial KPIs across Profitability, Liquidity, Solvency, Efficiency, and Valuation, render interactive executive dashboards, and export colorful Excel and PDF audit reports.

---

## 🚀 Quick Start Guide (Windows)

### Option 1: One-Click Launch (Recommended)
Simply double-click the **`run.bat`** file in the project folder.  
It will automatically:
1. Install/verify Python dependencies (`requirements.txt`)
2. Validate and seed the 10-period Trial Balance dataset
3. Open the web dashboard in your default browser at **`http://localhost:8000`**

### Option 2: Command Line Execution
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed SQLite database from Trial Balance Excel
python seed_data.py

# 3. Launch application server
python run.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your web browser.

---

## 🎯 Key Application Features & Dashboard Tabs

The application features 5 ordered workspace tabs:

1. 📊 **KPI Analytics Dashboard**
   - Executive Summary Header & Key Metric Highlights.
   - Interactive multi-period selection filters (`Q1 FY2023` to `Q4 FY2024` + `Annual FY2023` & `Annual FY2024`).
   - Revenue & Profitability Growth Dynamics Chart.
   - Profitability Margins Trajectory Chart.
   - Liquidity & Solvency Ratios Chart.
   - **Operating Cost Breakdown Comparative Matrix**: Dual dropdown selectors (`P1` vs `P2`) with side-by-side % of revenue cost bars and exact cost-shift percentage point calculations.

2. ⚡ **KPI Engine Dashboard**
   - Categorized metric cards across Profitability, Liquidity, Solvency, Efficiency, and Valuation.
   - Metric values displayed with directional trend indicators (`▲ +Value`, `▼ -Value`, `▬ 0`).
   - Dedicated **Benchmark Target Box** (`🎯 Benchmark: 35 %` | `✓ ABOVE TARGET`).
   - **EPS & BVPS Calculation**: Shares outstanding calculated using **Rs. 10 per share** issue price from Paid-in Share Capital.

3. 🧾 **Financial Statements**
   - Multi-period side-by-side comparative financial matrices.
   - Complete Income Statement: Gross Revenue, Sales Returns, Net Revenue, COGS, Gross Profit, OpEx, EBITDA, EBIT, **Profit Before Tax (PBT)**, Tax, and **Profit After Tax (PAT / Net Income)**.
   - Complete Balance Sheet: Current Assets, Non-Current Assets, Current Liabilities, Non-Current Liabilities, Shareholders' Equity.

4. 📥 **Export Reports**
   - **Colorful Excel Workbook (`.xlsx`)**: Multi-tab workbook (`KPI Scorecard`, `Income Statement`, `Balance Sheet`) formatted with deep navy headers, currency styling (`₹#,##0.00`), and color-coded RAG badges.
   - **Executive PDF Report (`.pdf`)**: Font-safe vector PDF with executive metric highlight callout cards, styled table headers, alternating row fills, and font-safe `INR` currency formatting.

5. 📤 **Trial Balance Upload**
   - Upload new Excel or CSV Trial Balance files (`.xlsx`, `.csv`).
   - Automated double-entry balance validation engine.

---

## 🎨 RAG Status & Benchmark Color Rules

| Status | Badge / Border Theme | Meaning & Evaluation Criteria |
| :--- | :--- | :--- |
| **`GREEN`** | **Solid Emerald** (`#15803D`) | Benchmark target is met **AND** performance change is positive/improving (`▲ +Value`). |
| **`AMBER`** | **Solid Dark Amber** (`#B45309`) | Benchmark target is met **BUT** performance change is negative/declining (`▼ -Value`). |
| **`RED`** | **Solid Crimson** (`#B91C1C`) | Benchmark target is **NOT MET** (`⚠️ BELOW TARGET`). |

---

## 🧮 Accounting & Calculation Principles

- **P&L Flow Items (Revenue & Expenses)**:
  $$\text{Annual FY} = \text{Q1} + \text{Q2} + \text{Q3} + \text{Q4}$$
- **Balance Sheet Stock Items**:
  $$\text{Annual FY} = \text{Q4 Closing Balance}$$
- **Double-Entry Trial Balance Balancing**:
  All period net earnings are dynamically balanced into **Retained Earnings & Reserves (`Account 3020`)**, guaranteeing `Total Debits == Total Credits` with **₹0.00 variance** across all 10 periods.
- **Shares Outstanding**:
  $$\text{Shares Outstanding} = \frac{\text{Paid-in Share Capital (Account 3010)}}{\text{Issue Price (Rs. 10.00)}}$$

---

## 🧪 Automated Verification Suite

To run the automated API test suite covering all 13 core endpoints:
```bash
python test_api.py
```

Expected output:
```
==================================================
ALL API ENDPOINT TESTS PASSED SUCCESSFULLY! (13/13)
==================================================
```

---

## 📁 Repository Structure

```
FinKPI Analyser JM/
├── backend/                  # FastAPI Application Core
│   ├── app/
│   │   ├── api/             # API Endpoints & Routes
│   │   ├── config.py        # Benchmarks & Mapping Config
│   │   ├── database.py      # SQLite Database Session
│   │   ├── exporter.py      # Excel & PDF Export Engine
│   │   ├── financial_engine.py # Financial Statement Aggregator
│   │   ├── kpi_engine.py    # 40+ KPI Calculation Engine
│   │   └── models.py        # SQLAlchemy Data Models
├── frontend/
│   └── index.html           # React + TailwindCSS Single-Page App
├── TrialBalance_COMP001_FY2023_FY2024.xlsx # 10-Period Sample Dataset
├── generate_sample_tb.py    # Trial Balance Dataset Generator
├── seed_data.py             # Database Seeding Script
├── run.py                   # FastAPI Application Server Entrypoint
├── run.bat                  # One-Click Windows Batch Script
├── test_api.py              # Automated API Test Suite
└── requirements.txt         # Python Dependencies
```

---

## 📄 License
This project is licensed under the MIT License.
