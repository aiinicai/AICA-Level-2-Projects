# AI-Powered CFO Dashboard

## AICA Level 2 Capstone Project

An AI-powered financial decision-support dashboard designed to help
CFOs and business leaders convert structured financial data into
meaningful management insights, financial diagnostics and
action-oriented CFO perspectives.

---

## 1. Problem Statement

Financial information is often available across multiple financial
statements and datasets. Reviewing this information manually can make
it difficult for management to obtain a consolidated view of
profitability, growth, leverage, working capital, valuation and
financial risks.

The objective of this project is to create a single CFO-oriented
dashboard that converts structured financial data into a consolidated
financial review and supports faster, more structured decision-making.

---

## 2. Project Objective

The AI CFO Dashboard provides a centralized environment where users
can select a company and reporting period and analyse its financial
performance through multiple CFO-oriented perspectives.

The application combines:

- Deterministic financial calculations
- Financial diagnostics
- Comparative analysis
- AI-assisted CFO analysis
- Exportable management reports

---

## 3. Key Features

### Executive Dashboard

Provides a consolidated management view of important financial
performance indicators.

### Profitability Analysis

Analyses revenue, EBITDA, operating margins, PAT and related
profitability indicators.

### Solvency Dashboard

Evaluates leverage, debt-to-equity, interest coverage and other
financial-strength indicators.

### Growth & Momentum

Provides a view of growth trends and operating momentum.

### Working Capital Analysis

Provides analysis of working-capital efficiency and related
financial indicators.

### Valuation Multiples

Provides valuation-oriented analysis using relevant financial
multiples.

### Peer Benchmarking

Allows financial performance to be viewed against comparable
companies.

### Red Flags

Highlights potentially important financial and operating warning
signals requiring management attention.

### Data Quality

Provides diagnostics relating to the quality and completeness of
the financial information used by the dashboard.

### Company Explorer

Allows users to explore companies available within the application
dataset.

### AI CFO Advisor

Provides AI-assisted CFO-level analysis based on the selected
company, financial metrics and reporting period.

The AI CFO Advisor supports:

- Executive Board Memo generation
- Margin Driver analysis
- Capital Allocation analysis
- DuPont analysis
- Interactive CFO questions

The application also includes entity-context controls designed to
reduce the risk of attributing the financial metrics of one company
to another company.

---

## 4. AI Architecture

The application follows a two-layer analytical approach:

1. Deterministic financial analysis
2. AI-assisted CFO analysis

The frontend does not directly store the Gemini API credential.

When a user requests AI CFO analysis, the frontend sends the request
to the backend endpoint:

    /api/cfo-memo

The backend retrieves the Gemini API key from the server environment
and uses it to communicate with the Gemini model.

The generated response is then returned to the dashboard.

### High-Level Flow

    User
      |
      v
    CFO Dashboard
      |
      v
    /api/cfo-memo
      |
      v
    Server-side middleware
      |
      v
    GEMINI_API_KEY
      |
      v
    Gemini
      |
      v
    AI CFO Analysis
      |
      v
    Dashboard

---

## 5. Deterministic Fallback

The application includes a deterministic offline CFO engine.

If the backend Gemini service is unavailable, the application can
fall back to rule-based financial analysis using the available
financial metrics.

This provides resilience and allows the application to continue
providing core CFO-oriented analysis when live AI inference is
unavailable.

---

## 6. Financial Analysis

The dashboard works with financial indicators including:

- Revenue
- Operating EBITDA
- Operating Profit Margin
- Profit After Tax
- Debt
- Net Worth
- Debt-to-Equity
- Interest Coverage Ratio
- ROCE
- Economic Spread
- Operating Scissors
- Working Capital indicators
- Valuation multiples
- Peer benchmarking indicators

---

## 7. Reports and Exports

The application provides export functionality for management use,
including:

- Board Memo PDF
- Company financial summary in Excel format

---

## 8. Technology Stack

- React 19
- TypeScript 6
- Vite 8
- Tailwind CSS 3
- Google Gemini
- Supabase
- Recharts
- XLSX
- jsPDF
- jsPDF AutoTable
- Lucide React
- Motion
- Oxlint

---

## 9. Project Structure

    src/
    ├── assets/
    ├── components/
    ├── context/
    ├── data/
    ├── lib/
    ├── services/
    ├── types/
    ├── utils/
    ├── views/
    ├── App.tsx
    ├── main.tsx
    ├── App.css
    └── index.css

### Major folders

- `components` – reusable user-interface components
- `context` – application and authentication state
- `data` – company and financial datasets
- `lib` – external service clients
- `services` – AI and service integrations
- `types` – TypeScript data definitions
- `utils` – financial calculations, formatting and export utilities
- `views` – dashboard screens and analytical modules
- `assets` – application visual assets

---

## 10. Security and Environment Variables

Sensitive credentials should not be committed to the repository.

The Gemini API key is accessed through the server environment:

    GEMINI_API_KEY

Environment files containing actual credentials must not be uploaded
to GitHub.

For local development, environment variables should be configured
locally.

A `.env.example` file can be used to document the required
environment-variable names without exposing actual credentials.

The Supabase client uses the application's publishable configuration
for client-side connectivity. Supabase service-role or other
privileged credentials must never be exposed in client-side code.

---

## 11. Running the Project

### Prerequisites

- Node.js
- npm

### Install Dependencies

    npm install

### Configure Environment Variables

Create a local environment configuration containing the required
values for the application.

Do not commit actual credentials to GitHub.

### Start Development Server

    npm run dev

Vite will display the local development URL in the terminal.

### Build the Project

    npm run build

### Preview the Production Build

    npm run preview

---

## 12. Capstone Project

### Course

AICA Level 2 Certification Course

### Project

AI-Powered CFO Dashboard

### Batch

AICA-L2-Batch-080

### Candidate

Nimisha Shah

---

## 13. Disclaimer

This application is an educational Capstone project developed for
financial analysis and decision-support demonstration.

The outputs are intended for analytical and demonstration purposes
and should not be treated as investment, accounting, tax or other
professional advice without appropriate professional review.