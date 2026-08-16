# CMA Pro Builder

AI for Chartered Accountants (AICA) Level 2 capstone project.

**Participant:** Kuber Ranjan Purkar  
**ICAI Membership No.:** 187707  
**Batch:** AICA Level 2, Batch 74, Nashik  
**Batch completed:** 6 August 2026

CMA Pro Builder is an educational Credit Monitoring Arrangement and financial
covenant analysis application. It supports illustrative financial projections,
term-loan schedules, WDV depreciation, drawing power, ratio workings, reports,
and Excel export.

## Start here

For the simplest evaluation instructions, read [START_HERE.md](START_HERE.md).

On Windows, an evaluator who has Node.js installed can double-click
`START_DEMO.bat`. The script installs the declared packages when required,
starts the development server, and opens the application in the default browser.

## Manual source-code start

Requirements: Node.js 20 or later and an internet connection for the first
dependency installation.

```bash
npm ci
npm run dev
```

Then open <http://localhost:41731>.

No Gemini API key or other API credential is required for the demonstrated
financial calculations.

## Useful commands

```bash
npm run dev              # Frontend evaluation mode at http://localhost:41731
npm run lint             # TypeScript type check
npm run build            # Production frontend build in dist/
npm run server           # Optional SQLite/LAN mode at http://localhost:8080
npm run build:singlefile # Single-file frontend build
```

The Windows executable was submitted separately through the ICAI submission
form because the compiled binary is not required for source-code review.

## Main source structure

- `src/engine/cmaEngine.ts` - CMA calculations, projections, ratios and workings.
- `src/pages/Home.tsx` - application shell and workspace navigation.
- `src/components/` - configuration, actuals, simulator, reports and ratios.
- `src/lib/excelExport.ts` - Excel workbook generation.
- `server/` - optional Express and SQLite local-server mode.
- `test/` - calculation and export verification scripts.
- `dist/` - prebuilt frontend output for reference.

## Evaluation and privacy notes

- The repository contains source code and fictitious demonstration data.
- The evaluation build bypasses commercial licensing for capstone review.
- No private signing key, password, API key or client-identifying financial data
  is included.
- The application is an educational prototype. It is not an audit opinion,
  certificate, bank sanction recommendation or substitute for verification of
  source records and bank-specific norms.

## Illustrative ratio benchmarks

- Current Ratio: at least 1.23
- DSCR: at least 1.75
- Debt/Equity: not more than 3.00
- TOL/TNW: not more than 4.50
- Interest Coverage: at least 2.60

Actual definitions and acceptable levels differ by bank, borrower, facility and
sanction terms.

The optional server mode requires the native `better-sqlite3` package. Install
optional dependencies with `npm install --include=optional` only when that mode
is required. It is not needed for the browser-based capstone demonstration.
