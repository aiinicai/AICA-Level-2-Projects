# Portfolio Analyzer & Executive Research Report Generator
**AICA Level 2 Capstone Project Documentation**

---

## 1. Executive Summary & Core Idea
The **Portfolio Analyzer & Executive Research Report Generator** was conceived to bridge a critical gap in financial portfolio reporting: automating the transformation of raw, unformatted broker statements (CSVs, Excel files, or text exports) into publication-ready, institutional-grade PDF valuation reports.

### The Problem
Financial advisors, equity research analysts, and portfolio managers often waste hours manually taking data from broker exports, searching for historical prices, formatting table layouts, writing qualitative stock updates, and calculating risk/allocation metrics.

### The Solution / Core Idea
This utility automates the end-to-end workflow:
1. **Universal File Ingestion:** Accepts messy input data with varied column headers.
2. **Automated Ticker & ISIN Resolution:** Normalizes non-standard Indian equity symbols (including SME, T2T, and segmented stocks) and links them to Yahoo Finance market tickers.
3. **Historical Valuation Engine:** Back-calculates asset prices and 12-week price trends as of any requested valuation date.
4. **AI-Driven Qualitative Insights:** Uses AI LLMs (Gemini / OpenAI) or intelligent rule-based fallbacks to generate stock research summaries (Promoter governance, Industry outlook, Financials, and Market sentiment).
5. **Typeset PDF Generation:** Builds an A4-formatted PDF report featuring executive dashboard cards, dynamic headers/footers (`Page X of Y`), and structured tables.

---

## 2. Technical Stack & Key Tools Used

| Category | Tool / Library | Purpose in Project |
| :--- | :--- | :--- |
| **GUI Framework** | `Tkinter` / `ttk` | Provides a cross-platform desktop user interface with form inputs, file browsers, and real-time execution logging. |
| **Market Data Engine** | `yfinance` | Fetches historical price movements, daily close prices, and 12-week weekly trend data dynamically from Yahoo Finance APIs. |
| **Symbol Resolution** | `requests` & `urllib` | Queries online financial search APIs to automatically map stock names and ISINs to ticker symbols (`.NS` / `.BO`). |
| **Data Processing** | `pandas` & `numpy` | Cleans raw spreadsheet inputs, handles missing data, normalizes column labels, and performs mathematical portfolio calculations. |
| **AI Integration** | `google-generativeai` & `openai` | Optional LLM integration that generates qualitative stock summaries using Gemini or GPT models. |
| **PDF Generation** | `ReportLab` | Constructs PDF documents using custom flowables, dynamic canvas footers, and styled tables. |

---

## 3. Key Features & Utility Advantages (Pros)

### 1. Robust Symbol Resolution for SME & Indian Equities
* **Challenge:** SME stocks (e.g., `-SM`, `-ST` suffixes) and non-standard symbols often fail standard API queries, leading to missing price data.
* **Advantage:** Built-in pattern cleaners and explicit override mappings ensure that small-cap, SME, and restricted stocks are correctly mapped to their primary exchange symbols without returning false "Not Listed" errors.

### 2. Time-Travel Valuation Engine
* **Advantage:** Unlike simple real-time trackers, this tool allows users to specify **any historical valuation date** (e.g., `"31 March 2026"`). The system calculates portfolio value, individual closing prices, and 12-week historical trends relative to that specific target date.

### 3. Dual-Layer AI & Rule-Based Research
* **Advantage:** If an API key for Gemini or OpenAI is provided, the tool fetches AI-generated qualitative highlights. If no API key is provided or network limits are hit, it falls back to a built-in research template, ensuring zero runtime crashes.

### 4. Flexible Input Handling
* **Advantage:** Features an auto-mapping engine that recognizes variants like `Scrip Name`, `Stock Name`, `Particulars`, `Qty`, `Shares`, `Buy Price`, `Cost`, and `CMP`. Users do not need to reformat their source spreadsheets prior to upload.

### 5. Automated Professional Branding
* **Advantage:** Auto-generates structured PDF files named according to client entity and valuation date (`Portfolio_<EntityName>_<Date>.pdf`), complete with corporate branding, custom color palettes, and pagination (`Page X of Y`).

---

## 4. Summary of Development Iterations & Prompts

The project evolved across several development stages based on real-world edge cases:

```
[Phase 1: Architecture] ──► [Phase 2: PDF Engine] ──► [Phase 3: SME Fixes] ──► [Phase 4: UI Refinement]
```

### Development Progression:
1. **Phase 1 — Core Ingestion & Historical Engine:**
   * Developed flexible file parser capable of reading `.csv`, `.xlsx`, and `.xls` formats.
   * Built historical price fetcher using `yfinance` with standard date slicing.

2. **Phase 2 — ReportLab Typesetting & PDF Generation:**
   * Implemented custom `NumberedCanvas` class to calculate total page count dynamically for footer pagination.
   * Created styled data tables for 12-week closing trends and portfolio allocation metrics.

3. **Phase 3 — Handling Edge Cases (SME Tickers & Date Parsing):**
   * Integrated `parse_flexible_date()` to handle multiple date formats (`31 March 2026`, `2026-03-31`, `31/03/2026`).
   * Built a symbol normalizer to resolve false unlisted stock tags for SME tickers (e.g., `MSTCLTD`, `IEML-ST`, `REMUS-SM`).

4. **Phase 4 — UI Customization & Final Polishing:**
   * Added dynamic **Client/Entity Name** fields.
   * Fixed contrast issues in PDF headers by styling table headers with explicit bold white text over dark navy backgrounds (`#0F172A`).
   * Addressed multi-threading to keep the Tkinter UI responsive during network operations.

---

## 5. Workflow Architecture

```
                 ┌────────────────────────┐
                 │  Raw CSV / Excel File  │
                 └───────────┬────────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │  Universal Column Parser  │
               └───────────┬───────────────┘
                             │
                             ▼
         ┌───────────────────────────────────────┐
         │ Ticker Resolver & Normalization Engine│
         └───────────┬───────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌───────────────┐        ┌──────────────────┐
│ yfinance API  │        │  AI Research /   │
│ (Historical)  │        │ Dynamic Fallback │
└───────┬───────┘        └────────┬─────────┘
        │                         │
        └────────────┬────────────┘
                     │
                     ▼
       ┌───────────────────────────┐
       │ ReportLab PDF Generator   │
       └─────────────┬─────────────┘
                     │
                     ▼
       ┌───────────────────────────┐
       │ Final PDF Analysis Report │
       └───────────────────────────┘
```

---

## 6. Conclusion
This Capstone project demonstrates a complete end-to-end Python pipeline combining data wrangling (`pandas`), web scraping and financial APIs (`yfinance`, `requests`), artificial intelligence (`Gemini`/`OpenAI`), graphical user interfaces (`Tkinter`), and automated document layout (`ReportLab`). The resulting tool saves significant manual effort while maintaining high analytical rigor and visual appeal.