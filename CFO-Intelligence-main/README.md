# CFO Intelligence — Virtual CFO & FP&A Advisory Platform

An enterprise-grade, AI-powered Virtual CFO and Financial Planning & Analysis (FP&A) platform built with **React 19**, **TypeScript**, **Tailwind CSS**, and **Google Gemini AI (`@google/genai`)**. 

Designed for CPA firms, fractional CFO practices, and finance executives to ingest raw financial data, execute deterministic financial models, simulate multi-variable scenarios, connect to accounting portals via Model Context Protocol (MCP), and generate board-ready CFO advisory report packs.

---

## 🌟 Key Features

### 1. Multi-File Financial Ingestion & Cross-Statement Reconciliation
- **Simultaneous Multi-Upload**: Ingest **Profit & Loss**, **Balance Sheet**, and **Trial Balance** statements simultaneously in Excel (`.xlsx`, `.xls`), `.csv`, `.tsv`, or `.txt` format.
- **AI Classification & Normalization**: Automatically classifies statement types, extracts time series periods, and normalizes accounts.
- **Trial Balance Reconciliation**: Verifies that debits equal credits ($Debits = $Credits with zero variance detection) and reconciles P&L Net Income to Balance Sheet Equity roll-forwards.
- **Conversational Account Disambiguation**: Flags ambiguous line items (e.g., freight, contractor expenses, suspense accounts) and prompts targeted inquiries for instant resolution.

### 2. Live MCP Gateway (Model Context Protocol)
- **Accounting Connectors**: Connects to major accounting ecosystems:
  - **QuickBooks Online (QBO)**
  - **Tally Prime**
  - **Zoho Books**
  - **Oracle NetSuite**
  - **Xero**
- **JSON-RPC 2.0 Live Tools**:
  - `accounting_query_ledger`: Query general ledgers, sub-accounts, and transaction batches.
  - `accounting_get_trial_balance`: Fetch full debits/credits trial balance.
  - `accounting_get_ar_aging`: Pull categorized AR aging brackets (Current, 1-30, 31-60, 61-90, 90+ days).
  - `accounting_push_budget_metrics`: Push pro-forma forecast metrics back to cloud accounting ledgers.

### 3. Driver-Based Budgeting & 12-Month Pro-Forma Forecasting
- **Strategic Forecast Drivers**: Configure Revenue growth algorithms (YoY %, Volume × Price, Pipeline, MRR), Gross Margin hurdles, OPEX & Staffing rosters (headcount, salary load, hiring timeline), Working Capital cycles (DSO, DPO, DIO, CCC), and Seasonality profiles.
- **AI Driver Advisor**: One-click Gemini recommendations tuned to specific industry dynamics (SaaS, Healthcare, Manufacturing, E-commerce, Professional Services).
- **Dynamic 12-Month Trajectory**: Generates synchronized 3-Statement projections with runway, burn rate, and covenant tracking.

### 4. Interactive Financial Analysis & Scenario Modeling
- **3-Statement Engine**: Synchronized Income Statement, Balance Sheet, and Direct/Indirect Cash Flow Statements.
- **Executive KPI Dashboard**: QuickRatio, CurrentRatio, Gross/EBITDA margins, Return on Equity (ROE), Return on Assets (ROA), and Cash Conversion Cycle (CCC).
- **Scenario Simulator & Stress Testing**: Toggle Bull / Base / Bear cases, inflation shocks, supply chain disruptions, and pricing elasticity.
- **Breakeven & DCF Valuation**: Interactive sensitivity matrix calculating enterprise value, WACC, and margin-of-safety thresholds.

### 5. Board-Ready Report Packs & Export
- **Customizable Firm Branding**: Firm Header, CPA credentials, disclaimers, and client metadata.
- **Multi-Format Export**: One-click generation of print-ready **Executive PDF Report Packs** (via jsPDF & html2canvas) and structured **Excel Workbooks** (via SheetJS).

### 6. Zero-Leak Privacy Shield
- **Client Data Sanitization**: Built-in PII redaction layer masks sensitive company identifiers, bank account numbers, and individual tax IDs before sending prompts to external AI inference models.

---

## 🛠️ Technology Stack

- **Frontend**: React 19, TypeScript, Tailwind CSS v4, Motion (Framer Motion), Recharts, Lucide React
- **Backend / API**: Node.js, Express, tsx, esbuild
- **AI / LLM Integration**: Google Gen AI SDK (`@google/genai`) powered by `gemini-2.5-flash` / `gemini-3.7-flash`
- **Document Processing**: SheetJS (`xlsx`), jsPDF, html2canvas

---

## 🚀 Getting Started

### Prerequisites
- **Node.js** (v20.x or higher recommended)
- **npm** or **bun** / **yarn** / **pnpm**
- **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))

---

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cfo-intelligence.git
   cd cfo-intelligence
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in the project root based on `.env.example`:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and configure your API keys:
   ```env
   GEMINI_API_KEY="your_actual_gemini_api_key_here"
   APP_URL="http://localhost:3000"
   ```

---

### Development Mode

Start the integrated Express + Vite development server:
```bash
npm run dev
```

The application will be accessible at:
```
http://localhost:3000
```

---

### Production Build & Deployment

1. **Build the client and bundle the server**:
   ```bash
   npm run build
   ```
   This compiles the React SPA to `dist/` and creates a self-contained CommonJS backend in `dist/server.cjs` with `esbuild`.

2. **Start the production server**:
   ```bash
   npm start
   ```

---

## 📁 Project Structure

```
├── .env.example              # Environment variables template
├── metadata.json             # Applet capabilities and metadata
├── package.json              # NPM dependencies and scripts
├── server.ts                 # Express API server + Gemini AI endpoints + Vite middleware
├── tsconfig.json             # TypeScript configuration
├── vite.config.ts            # Vite configuration
├── src/
│   ├── App.tsx               # Main application layout, state, and tab routing
│   ├── main.tsx              # React entry point
│   ├── index.css             # Tailwind CSS imports
│   ├── types.ts              # TypeScript interfaces, types, and enums
│   ├── components/
│   │   ├── advisory/         # AI CFO Executive Summary & Chat
│   │   ├── common/           # Firm Header/Footer, Navigation, Modals
│   │   ├── dashboard/        # Executive KPIs, Charts, Trend Analyzers
│   │   ├── data-import/      # Multi-File Ingestion, Statement Mapping, Disambiguation
│   │   ├── financials/       # 3-Statement Models (P&L, Balance Sheet, Cash Flow)
│   │   ├── forecasting/      # Driver Basis Configuration & 12-Month Pro-Forma
│   │   ├── integrations/     # MCP Connectors (QBO, Tally, Zoho, NetSuite, Xero)
│   │   ├── reports/          # Report Pack Customizer, Print & PDF Generator
│   │   └── scenarios/        # Scenario Matrix, Stress Testing, Sensitivity
│   └── services/
│       ├── aiAdvisorService.ts   # Client-side AI advisory bridge
│       ├── connectorService.ts   # MCP Accounting connector client
│       ├── dataQualityEngine.ts  # Sanity checks and audit formulas
│       ├── demoData.ts           # Pre-configured multi-industry financial models
│       ├── exportService.ts      # PDF & Excel workbook exporter
│       ├── fileParser.ts         # Multi-statement parser, categorizer & reconciler
│       ├── financialEngine.ts    # Deterministic 3-statement calculations & KPIs
│       ├── forecastingEngine.ts  # Driver-based forecasting & pro-forma generator
│       ├── industryRules.ts      # Industry-specific benchmark logic
│       └── privacyShield.ts      # PII redaction and payload sanitization
```

---

## 📤 Pushing to GitHub

To publish this project to your GitHub account:

1. **Initialize Git (if not already initialized)**:
   ```bash
   git init
   ```

2. **Add and commit all files**:
   ```bash
   git add .
   git commit -m "Initial commit: CFO Intelligence Platform with AI Advisory & Multi-Statement Ingestion"
   ```

3. **Link to your GitHub repository and push**:
   ```bash
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
   git push -u origin main
   ```

---

## 🔒 Security & Privacy

- **Server-Side API Key Protection**: The `GEMINI_API_KEY` is exclusively accessed in server-side routes (`server.ts`) and is never exposed to the client browser.
- **Client PII Sanitization**: Prior to AI processing, customer records and accounting identifiers pass through the client-side `PrivacyShield` engine to redact sensitive credentials and financial identifiers.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
