# Bullion Ledger (PWA)

A responsive, offline-first Progressive Web App (PWA) built for Indian investors tracking physical gold and silver purchases in forms: **Vedhani**, **Coin**, and **Bar**.

Built with **React 19**, **TypeScript**, **Tailwind CSS**, and **Vite**, with complete local persistence via **IndexedDB** and an interactive SVG growth chart.

---

## 🏛️ Core Features

1. **Dashboard & Dynamic Valuation**
   - Single unified **"Valuation as of" date selector ($D$)**, defaulting to `30-Oct-2026` or current business date in `Asia/Kolkata`.
   - **5 Primary KPI Cards**:
     - **Invested Amount**: Total acquisition cost including actual invoice GST (taxes) and making/delivery charges.
     - **Reference Metal Value**: Current worth evaluated at 100% of the benchmark rate for the holding's fineness.
     - **Estimated Resale Value**: Realistic liquidity proceeds after applying the customizable resale markdown (default 3.0%).
     - **Unrealized Gain / Loss**: Displayed in Indian Rupees (`₹`) and percentage (`%`), with clear labels and accessible contrast.
     - **Portfolio XIRR**: Annualized internal rate of return calculated by combining all irregular purchase cash flows with the terminal liquidation value.
   - **Metal Breakdowns**: Dedicated cards for Physical Gold and Physical Silver showing total grams held, cost, resale proceeds, and asset-specific XIRR.
   - **Interactive SVG Chart**: Cumulative cost vs. estimated resale value with linear/logarithmic toggles, range filters (`1M`, `6M`, `1Y`, `3Y`, `5Y`, `ALL`), crosshair tooltips, and exchange transition marker (`NSE` $\to$ `IBJA` on `16-Jun-2026`).

2. **Purchases Ledger & Invoices**
   - Record purchases with required fields: Holding ID, Purchase Date, Jeweller/Seller, Invoice # (preserving leading zeros, e.g., `004921`), Metal (`GOLD` / `SILVER`), Form (`VEDHANI` / `COIN` / `BAR`), Purity/Fineness (`999`, `995`, `916`, etc.), Weight in grams, Rate in ₹/gram, and Rupee Taxes Paid (GST/TCS).
   - **Duplicate Detection**: Multi-field check across `(date, seller, invoice, metal, form, weight)` warns against accidental double-entry while preserving support for multi-item invoices.
   - **Bulk Import**: Drag-and-drop import from **Excel (.xlsx)** or **CSV** with live validation preview.
   - **Excel Template**: Single-click "Download XLSX Purchase Template" formatted with validation rules.
   - **Export**: Export all active purchases to Excel `.xlsx`.
   - **Soft Delete & Trash Bin**: Safe deletion with instant restoration or permanent purge.
   - **Undo Import**: One-click rollback for the last imported batch.

3. **Holding Details & Calculation Audits**
   - Individual holding cards and responsive table showing ID, invoice, seller, form, grams, invested cost, benchmark rate, resale value, holding days, and lot-level XIRR.
   - **Expandable Mathematical Breakdown**: Step-by-step arithmetic audit showing:
     $$\text{Adjusted Rate} = \text{Benchmark Rate} \times \frac{\text{Item Fineness}}{\text{Benchmark Fineness}}$$
     $$\text{Estimated Resale Value} = (\text{Grams} \times \text{Adjusted Rate}) \times (1 - \text{Markdown})$$
     $$\text{Single Lot XIRR} = \left(\frac{\text{Estimated Resale Value}}{\text{Invested Cost}}\right)^{\frac{365}{\text{Holding Days}}} - 1$$

4. **Historical Price Dataset (5,666 Records)**
   - Pre-bundled real historical dataset: **01-Jan-2019 through 30-Oct-2026** (1,889 Gold 995, 1,889 Gold 999, 1,888 Silver 999).
   - Provenance tracking: **NSE Spot** rates through `15-Jun-2026`; **IBJA Closing** rates from `16-Jun-2026`.
   - **Gap Detection**: Identifies documented non-publication gap for Silver on `03-Aug-2020` and carries forward `31-Jul-2020` rate with transparent flag.
   - **Audited Manual Corrections**: Change historical rates with mandatory audit reasons, logged to an auditable corrections ledger.
   - **Supplemental CSV Import**: Append future or corrected market observations.
   - **Live API Status**: Honest "Live updates not configured" state with replaceable `IRateProvider` architecture.

5. **Settings, Assumptions & Full Backup**
   - Separately configurable resale markdown percentages for Gold (default 3.0%) and Silver (default 3.0%).
   - Full offline JSON backup download and restore.
   - Opt-in sample demo portfolio loader and clear all data triggers.
   - Technical roadmap detailing migration to private cloud sync (Supabase/PostgreSQL, E2E encryption, daily cron).

6. **System Diagnostics & Verification Suite**
   - In-app 10-point test runner and headless test runner (`pnpm test`) validating mathematical parity, edge cases, Excel matching, and idempotency.

---

## 🚀 Getting Started

### Prerequisites
Node.js (v18+) and pnpm or npm.

### Quick Start
```bash
# Navigate to project
cd /Users/sahamay/.gemini/antigravity/scratch/bullion-ledger

# Run development server
pnpm dev

# Run automated 10-point technical verification suite
pnpm test

# Build production bundle
pnpm build
```

---

## 📊 Verification Test Results

All 10 acceptance checks pass automatically:
- ✅ **Check 1: CSV Import Idempotency**: Re-parsing identical CSV rows generates stable, identical record IDs without duplicates.
- ✅ **Check 2: Normalized Count & Coverage**: Exactly 5,666 observations (1,889 Gold 995, 1,889 Gold 999, 1,888 Silver 999).
- ✅ **Check 3: Benchmark Rates on 30-Oct-2026**: Gold 999 = ₹14,005.40/g; Silver 999 = ₹181.344/g.
- ✅ **Check 4: 10g Gold 999 Reference Value & 3% Resale**: Reference = ₹1,40,054.00; Resale = ₹1,35,852.38.
- ✅ **Check 5: Future Purchase Exclusion**: Purchases dated after valuation date $D$ are strictly omitted from portfolio totals.
- ✅ **Check 6: Silver Gap on 2020-08-03**: Detects missing Silver quote on 03-Aug-2020 and carries forward 31-Jul-2020 rate (₹63.871/g) with flag.
- ✅ **Check 7: 365-Day Exact 10.00% XIRR**: Outlay ₹1,00,000 $\to$ ₹1,10,000 in 365 days produces exact $10.0000\%$ p.a.
- ✅ **Check 8: Multi-Purchase XIRR Parity**: Irregular multi-lot cash flows match Excel's Newton-Raphson output.
- ✅ **Check 9: Same-Day Zero Days Guard**: Returns `null / N/A` for zero holding days, guarding against division-by-zero.
- ✅ **Check 10: Full Backup & Restore Integrity**: Roundtrip serialization and deserialization across all stores verified.
