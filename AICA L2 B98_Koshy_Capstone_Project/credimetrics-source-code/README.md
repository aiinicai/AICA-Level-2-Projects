# CrediMetrics - Financial Ratio Analysis & Credit Assessment Tool

> Enterprise-grade financial statement analysis, ratio computation engine, 100-point credit health scoring, red flag detection, and lender-ready Credit Appraisal Memorandum (CAM) generator.

Built with **React 19, TypeScript, Tailwind CSS, jsPDF, SheetJS (XLSX), and Lucide Icons**.

---

## 🌟 Key Features

1. **User Authentication & Role-Based Access Control (RBAC)**
   - 5 Persona Profiles: Chartered Accountant (CA), Bank Credit Officer, Loan Consultant, Risk Admin, and Independent Viewer.
   - Comprehensive audit logging tracking all statement imports, recalculations, and report downloads.

2. **Company Management**
   - Track Corporate Identification Number (CIN), Income Tax PAN, Industry sector, Registered Office Address, Year Established, and Annual Turnover (in INR Crores).
   - Pre-loaded with 4 multi-tier corporate profiles:
     - **Apex Precision Engineering Ltd.** (*Grade AAA — Health Score 91/100 — Approved*)
     - **Zenith Cloud Technologies Pvt. Ltd.** (*Grade AA — Health Score 78/100 — Conditional Approval*)
     - **Surya Infrastructure & Logistics Ltd.** (*Grade BB — Health Score 53/100 — Review Required*)
     - **Bharat Textile Mills Ltd.** (*Grade B — Health Score 34/100 — Rejected with High Risk Flags*)

3. **Financial Statement Upload & Entry**
   - **Excel (.xlsx, .xls) & CSV Parser**: Multi-year column extraction for Balance Sheet and P&L.
   - **Interactive Manual Entry**: Instant balance sheet equation validator (`Total Assets = Total Liabilities & Equity`) with automated reserve balancing.
   - **Downloadable Excel Template**: Ready-to-use sample workbook for immediate testing.

4. **Financial Ratio Computation Engine**
   - **Liquidity**: Current Ratio, Quick Ratio, Cash Ratio.
   - **Profitability**: Gross Margin, Net Profit Margin, EBITDA Margin, Return on Assets (ROA), Return on Equity (ROE).
   - **Solvency**: Debt-to-Equity Ratio, Interest Coverage Ratio (ICR), Debt-to-Total-Assets.
   - **Efficiency**: Inventory Turnover, Days Inventory Outstanding (DIO), Asset Turnover, Receivables Turnover, Days Sales Outstanding (DSO), Working Capital Turnover.
   - Multi-year comparative trends with prudential banking benchmark statuses (*Healthy*, *Moderate*, *Risk*).

5. **Financial Health Scoring Engine (Section 5 Standard)**
   - 100-point Health Scoring calibrated to Basel/RBI credit underwriting norms:
     - **Liquidity**: 25% weight
     - **Profitability**: 25% weight
     - **Solvency**: 25% weight
     - **Efficiency**: 25% weight
   - Rating Tiers: Excellent (90–100), Good (75–89), Average (60–74), Weak (40–59), High Risk (<40).

6. **Credit Underwriting & Decision Matrix (Section 6 Standard)**
   - Credit Grades: **AAA**, **AA**, **A**, **BBB**, **BB**, **B**.
   - Underwriting Decisions:
     - **Approve**: Score > 85, Debt/Equity < 1.5, Current Ratio > 1.5
     - **Conditional Approval**: Score 65–84
     - **Review Required**: Score 50–64
     - **Reject**: Score < 50
   - Automated computation of maximum recommended credit exposure, risk-adjusted interest spread, collateral margin, and sanction covenants.

7. **Red Flag Detection Engine (Section 8 Standard)**
   - Real-time detection of:
     - ⚠ Current Liabilities Exceed Current Assets (`Current Ratio < 1.0`)
     - ⚠ Severe Quick Liquidity Deficit (`Quick Ratio < 0.8`)
     - ⚠ Excessive Debt Burden (`Debt to Equity > 3.0`)
     - ⚠ High Loan Default Risk (`Interest Coverage < 1.5`)
     - ⚠ Negative Net Profit (Operational Loss)
     - ⚠ Continuous Profit Decline over multiple years
     - ⚠ 3-Year Topline Revenue Decline
     - ⚠ Prolonged Debtor Collection Period (`DSO > 120 days`)

8. **Institutional Export & Download Center**
   - **PDF Credit Appraisal Memorandum (CAM)**: Official multi-page loan memo formatted with borrower details, executive recommendation badge, 4-pillar scores, full ratio matrix, red flags, SWOT analysis, and 3-tier sign-off blocks (*Prepared by, Risk Reviewed by, Sanctioning Authority*).
   - **Excel Financial Model (`.xlsx`)**: 4-worksheet workbook with Credit Appraisal Summary, Multi-Year Financial Statements, Ratio Calculations, and Red Flag Matrix.
   - **Blank Import Template (`.xlsx`)**: Pre-formatted Excel sheet for immediate data population.
   - **JSON Assessment Data (`.json`)**: Raw diagnostic payload.

---

## 🚀 Running Locally

### Prerequisites
- **Node.js**: v18.0.0 or higher (Node 20+ recommended)
- **npm**: v9.0.0 or higher (or pnpm / yarn)

### 1. Clone or Extract the Archive
If you downloaded the `.zip` file:
```bash
unzip credimetrics-source-code.zip -d credimetrics
cd credimetrics
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Start Development Server
```bash
npm run dev
```

The app will start at `http://localhost:3000` (or `http://localhost:5173`). Open this URL in your web browser.

### 4. Build for Production
To create an optimized production build:
```bash
npm run build
```
The output will be placed in the `dist/` directory.

To preview the production build locally:
```bash
npm run preview
```

---

## 📁 Project Structure

```
├── public/                 # Static assets and templates
├── src/
│   ├── components/         # Modular UI components
│   │   ├── AiInsightsCard.tsx         # Automated credit narrative engine
│   │   ├── AuditLogsModal.tsx         # System audit trail viewer
│   │   ├── CompanyModal.tsx           # Borrower registration modal
│   │   ├── CreditDecisionBanner.tsx   # Decision matrix & sanction terms
│   │   ├── HealthScoreCard.tsx        # 4-pillar 100-pt scoring card
│   │   ├── Navbar.tsx                 # Header with persona & company switcher
│   │   ├── RatioTable.tsx             # Multi-year ratio computation grid
│   │   ├── RedFlagsAlert.tsx          # Real-time risk indicator alerts
│   │   ├── ReportDownloadModal.tsx    # PDF, Excel, and JSON download center
│   │   ├── TrendAnalysisView.tsx      # Multi-year charts & CAGR analytics
│   │   └── UploadModal.tsx            # Excel/CSV parser & manual balance form
│   ├── data/
│   │   └── seedData.ts                # Pre-seeded companies, statements & users
│   ├── types/
│   │   └── financial.ts               # Complete TypeScript domain models
│   ├── utils/
│   │   ├── excelParser.ts             # Excel (.xlsx) & CSV file parser
│   │   ├── healthScoreEngine.ts       # 25% weighted scoring & decision matrix
│   │   ├── ratioEngine.ts             # Financial ratio computation & benchmarks
│   │   ├── redFlagEngine.ts           # Red flag rules detection engine
│   │   ├── reportGenerator.ts         # PDF, Excel, and JSON file generation
│   │   └── zipExporter.ts             # Source code archive exporter
│   ├── App.tsx                        # Master application layout & state
│   ├── index.css                      # Global Tailwind CSS styling
│   └── main.tsx                       # React DOM entry point
├── index.html                         # HTML entry with metadata
├── package.json                       # Dependencies & build scripts
├── tsconfig.json                      # TypeScript compiler options
└── vite.config.ts                     # Vite bundler configuration
```

---

## 💼 Pre-Seeded Demonstration Scenarios

You can switch between these companies in the top navbar:

| Company Name | Industry | Health Score | Credit Grade | Underwriting Decision |
|---|---|---|---|---|
| **Apex Precision Engineering Ltd.** | Auto Components | 91 / 100 | **AAA** | **APPROVE** (Prime Borrower) |
| **Zenith Cloud Technologies Pvt. Ltd.** | Enterprise SaaS | 78 / 100 | **AA** | **CONDITIONAL APPROVAL** (Working Capital Monitoring) |
| **Surya Infrastructure & Logistics Ltd.** | EPC Construction | 53 / 100 | **BB** | **REVIEW REQUIRED** (High Leverage D/E 2.6x) |
| **Bharat Textile Mills Ltd.** | Textiles | 34 / 100 | **B** | **REJECT** (Operational Losses, Severe Red Flags) |

---

## 📄 License
Apache-2.0
