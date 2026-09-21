# MF X-Ray V1 — User Guide

**MF X-Ray — AI-Powered Mutual Fund Portfolio Intelligence & Risk Analysis System**  
**ICAI AI Level 2 Capstone Project**  
**Version:** V1.0

---

## 1. Introduction

**MF X-Ray V1.0** is an offline, privacy-centric portfolio-intelligence tool designed for Chartered Accountants, financial analysts, and mutual fund investors. 

Instead of looking at mutual funds merely as individual "black boxes", MF X-Ray penetrates the fund wrapper to perform a **look-through portfolio x-ray**. It uncovers:
- Your **true effective exposure** to individual underlying stocks.
- **Hidden overlap** between seemingly different mutual fund schemes.
- **Sector concentration risks**.
- Transparent **Risk & Health analytics** (0–100 Health Score).
- Rule-based **AI Insights** and an interactive natural-language question interface (**Ask MF X-Ray**).

---

## 2. Launching the Modern Desktop Application (1-Click)

You do **not** need to run commands or interact with raw Python code. The tool includes dedicated 1-click Windows launchers:

1. **Option A (Recommended):** Double-click **`Launch_MF_XRay.bat`** in the project folder.
2. **Option B (Silent Mode):** Double-click **`Launch_MF_XRay.vbs`** to launch without opening a command prompt window.
3. The tool automatically opens in a **dedicated, frameless desktop application window** (Edge App Mode) featuring a modern dark-navy financial UI.

*(Note: If you ever prefer running the Python script directly, you can also run `python run_app.py` or `python MF_XRay_V1.py`.)*

---

## 3. Clean Slate: Entering Your Own Data

By default, the application starts with a **100% clean portfolio** (no demo data loaded). You can enter and manage all your own funds and investments:

### Method A: Direct Investment Entry
1. In the top navigation bar, click the green **"+ Add Investment"** button (or go to **"My Portfolio"**).
2. Select any fund from the dropdown.
3. Enter your **Investment Amount (₹)** (e.g. `200000`).
4. Select **Lump Sum** or **SIP**, and choose the **Investment Date**.
5. Click **"Save Investment"**.
6. The Dashboard, Look-Through X-Ray, Sector Allocation, and Health Score immediately calculate in real time.

### Method B: Adding Your Own Custom Schemes & Holdings
1. Click the blue **"+ Add Custom Fund"** button in the top navigation bar.
2. Enter the **Fund Name**, Category, NAV, AUM, Expense Ratio, and 1Y/3Y/5Y returns.
3. Add the underlying stocks with their respective weights and sectors.
4. Click **"Save Fund & Holdings"**. The fund is saved permanently to `user_funds.json`.

### Method C: Loading Demo Data (Optional)
If you ever want to preview all 14 analytics modules with pre-configured sample data, click the blue **"Load Demo Portfolio"** button in the top bar. You can clear it at any time by clicking **"Clear Entire Portfolio"**.

## 4. Step-by-Step Module Walkthrough

### Module 1: My Portfolio
1. Click **"My Portfolio"** on the left sidebar.
2. Under the **Add / Update Fund** form:
   - **Fund:** Select an available fund from the dropdown.
   - **Investment Amount (Rs.):** Enter your investment amount (e.g. `200000`).
   - **Method:** Choose `Lump Sum` or `SIP`.
   - **Investment Date:** Enter date in `DD-MM-YYYY` format (defaults to today).
   - Click **"Add / Update Fund"**.
3. If the fund already exists in your portfolio, entering a new amount updates it in place.
4. View the updated **Holdings Table** and the live **Allocation Donut Chart** side-by-side.
5. To remove an individual fund, select it from the "Remove fund" dropdown and click **"Remove"**.
6. To reset completely, click **"Clear Entire Portfolio"**.

---

### Step 3: Use Portfolio X-Ray (The Look-Through Core)
1. Click **"Portfolio X-Ray"** on the sidebar.
2. Review the **Worked Example**:
   > *If Fund A (₹5,00,000) holds Company X at 10% (₹50,000) and Fund B (₹5,00,000) holds Company X at 8% (₹40,000), your true effective exposure to Company X is ₹90,000 or 9.0% of your ₹10,00,000 portfolio.*
3. Inspect the **Effective Stock Exposure Table**:
   - **Company:** Underlying corporate entity.
   - **Effective Exposure %:** Weighted portfolio exposure percentage.
   - **Exposure Amount:** True rupee amount allocated to this company across all your funds.
   - **Number of Funds:** Number of your held schemes owning this stock.
   - **Funds Holding It:** Exact list of schemes containing this company.
4. Notice how stocks appearing in multiple schemes (e.g., *Northbridge Bank*, *Bluepeak Software*) rise to the top of your portfolio risk concentration.

---

### Step 4: Understand the Overlap Analyzer
1. Click **"Overlap Analyzer"** on the sidebar.
2. Inspect the **Fund Overlap Matrix (%)**:
   - Shows pairwise similarity between every pair of funds.
   - 100% on the diagonal represents self-similarity.
   - An overlap of 40%+ triggers the **"High Overlap"** analytical warning.
3. Review the **Overlap Heatmap**:
   - Darker orange/red squares highlight schemes holding substantial identical stocks.
4. Check **Companies Held by Multiple Funds**:
   - Displays all overlapping stocks with total money invested across schemes.
5. **Overlap Methodology**:
   $$\text{Overlap}(A, B) = \sum_{i \in \text{common}} \min(w_{A,i}, w_{B,i})$$
   *Calculates the shared common portfolio percentage between two schemes.*

---

### Step 5: Explore Sector Analysis
1. Click **"Sector Analysis"** on the sidebar.
2. View your true effective sector exposure:
   - **Donut Chart:** Shows relative sectoral weights.
   - **Bar Chart:** Ranks sectors from highest to lowest with a reference threshold dotted line at 30%.
   - Sectors exceeding 30% are flagged as high concentration.

---

### Step 6: Risk Analysis & Portfolio Health Score
1. Click **"Risk Analysis"**:
   - **Risk-Free Rate:** Defaults to 6.0% p.a. Enter your preferred rate and click **"Recalculate"** to update the Sharpe Ratio.
   - **Volatility (Annualised):** Standard deviation of monthly returns $\times \sqrt{12}$.
   - **Sharpe Ratio:** Risk-adjusted excess return $\frac{\text{CAGR} - R_f}{\sigma}$.
   - **Maximum Drawdown:** Historical peak-to-trough decline.
2. Check the **Portfolio Health Score** (on Dashboard & About):
   - Transparent 0–100 score built from 6 independent components:
     - Diversification (20 pts)
     - Overlap (20 pts)
     - Stock Concentration (20 pts)
     - Sector Concentration (15 pts)
     - Volatility (15 pts)
     - Maximum Drawdown (10 pts)

---

### Step 7: Portfolio Changes & Snapshots
1. Go to **"Portfolio Changes"**.
2. Enter a snapshot label (e.g. `Portfolio Q1`) and click **"Save Current Portfolio as Snapshot"**.
3. Modify your portfolio (e.g., add or remove a fund).
4. Save a second snapshot (e.g. `Portfolio Q2`).
5. Select **Previous** and **Current** snapshots and click **"Compare"**.
6. Review stock-level changes with status badges:
   - `New Holding`, `Removed Holding`, `Increased`, `Reduced`, `No Material Change`.
   - Percentage point (+/- pp) difference for each stock and sector.

---

### Step 8: Use the What-If Simulator
1. Click **"What-If Simulator"** on the sidebar.
2. Select any fund from your current portfolio from the dropdown.
3. Click **"Run What-If Simulation"**.
4. Instantly view the **Before vs. After** comparison table:
   - Change in Total Investment
   - Shift in Average Pairwise Overlap %
   - Shift in Top 5 Concentration %
   - Impact on Largest Sector %
   - Impact on overall Portfolio Health Score
5. Inspect the **Underlying Exposure Changes** table showing which stocks decrease or drop out.

---

### Step 9: Use "Ask MF X-Ray" (AI Insights)
1. Click **"AI Insights"** on the sidebar.
2. Read the auto-generated **Portfolio Narrative** explaining concentration and overlap in plain English.
3. In the **Ask MF X-Ray** box, type any natural language question, or click the **Quick Questions** buttons:
   - *"Which companies have the highest exposure?"*
   - *"Which funds overlap the most?"*
   - *"Which sector has the highest exposure?"*
   - *"Which funds contain Northbridge Bank?"*
   - *"Why is my portfolio concentrated?"*
   - *"Explain my portfolio like a CA."*
4. Click **"Ask MF X-Ray"** to receive an immediate, deterministic, mathematically grounded answer.

---

### Step 10: Run SIP Analysis
1. Click **"SIP Analysis"** on the sidebar.
2. Select a scheme, monthly SIP amount (e.g., ₹10,000), start date, and instalment count (e.g., 24).
3. Click **"Calculate"**.
4. View accumulated units, total capital invested, current market valuation, absolute return %, and exact **Annualised Return (XIRR)** calculated via the Newton-Raphson method.

---

### Step 11: Export Professional Reports
1. Click **"Reports"** on the sidebar.
2. **Excel Export (.xlsx):**
   - Click **"Generate Excel Report (.xlsx)"**.
   - Generates a styled 11-sheet workbook containing Portfolio Summary, Allocation, Fund Analysis, Underlying Holdings, Stock Exposure, Overlap Matrix, Sector Analysis, Risk Metrics, Alerts, AI Narrative, and Methodology.
3. **Word Report (.docx):**
   - Click **"Generate Word Report (.docx)"**.
   - Generates an executive Capstone document complete with cover page, executive summary, tables, bulleted alerts, methodology, and statutory disclaimers.

---

### Step 12: Data Management & CSV Templates
1. Click **"Data Management"** on the sidebar.
2. Click **"Generate CSV Templates"**:
   - Instantly generates `template_fund_master.csv`, `template_holdings.csv`, and `template_historical_nav.csv` in your folder.
3. **Import Fund Data:** Import new funds from CSV or Excel.
4. **Import Holdings:** Import underlying stocks and sector mappings from CSV or Excel.
5. **Export Dataset:** Save the complete active fund universe to Excel.
