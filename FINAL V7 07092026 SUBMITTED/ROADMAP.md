# FAMILY INVESTMENT MATRIX — DEVELOPMENT ROADMAP

## Project evolution

### Initial Core Version

Objective: create a single local family portfolio tracker.

Implemented:

- Streamlit user interface;
- SQLite local database;
- authentication;
- family members;
- brokers/platforms;
- transaction ledger;
- portfolio holdings;
- Excel/PDF-assisted input;
- charts;
- news;
- manual portfolio tracking.

---

## Startup Rectification

Problems observed:

- app launched with ordinary `python file.py`;
- Streamlit runtime warnings;
- first-run onboarding prompt;
- database locking risk.

Improvements:

- automatic dependency check;
- direct Python → Streamlit relaunch;
- Streamlit first-run preparation;
- SQLite timeout;
- WAL mode;
- foreign-key enforcement.

---

## V2 — Session State Stability

Problem:

`StreamlitValueAssignmentNotAllowedError`

Cause:

A Streamlit widget/form key conflicted with a session-state variable.

Fix:

- separated widget/form key naming from session-state naming;
- changed forced-password-state logic;
- scanned the source for similar literal-key collisions.

---

## V3 — Plotly Chart Stability

Problem:

Plotly wide-form chart error caused by mixed data types.

Fix:

- explicit numeric conversion;
- long-form chart dataframe;
- safer invested-vs-current chart generation.

Result:

More reliable Dashboard, Member View and analytical charts.

---

## V4 — User Interface + Manual Entry + Price Improvements

Implemented:

- professional light/high-contrast UI;
- explicit Plotly styling;
- automatic `Quantity × Price` transaction value;
- improved input resetting;
- strengthened current-price fallback;
- improved symbol cleaning.

Result:

Better readability and fewer manual arithmetic errors.

---

## V5 — Identifier Normalisation

Problem:

Pandas merge error:

```text
ValueError: merge on float64 and str columns for key 'identifier'
```

Cause:

Excel could convert numeric mutual-fund scheme codes to floats while SQLite stored identifiers as text.

Fix:

- canonical identifier cleaner;
- normalize before grouping;
- normalize before price-cache merge;
- numeric AMFI example `125497.0 → 125497`;
- symbols standardized to uppercase.

---

## V6 — Official Market-Data Architecture

Implemented:

- Zerodha Kite Connect LTP path;
- Upstox LTP path;
- Yahoo/yfinance fallback retained;
- mutual-fund NAV path;
- manual current-price override;
- session/environment-variable credential handling;
- connection diagnostics.

Design principle:

Prefer documented broker/provider APIs over scraping exchange web pages.

---

## V7 — FAMILY INVESTMENT MATRIX

V7 is the current project submission version.

Major additions:

### HDFC Securities

- HDFC market-price integration path;
- provider-specific instrument/token support;
- connection/testing route.

### ICICI Direct Breeze

- Breeze market-price integration path;
- provider-specific symbol/code support;
- session-based credential support.

### Instrument Master

Central provider mapping for:

- portfolio symbol;
- exchange;
- instrument name;
- ISIN;
- provider tokens/keys;
- HDFC mapping;
- ICICI Breeze mapping;
- Upstox key;
- Yahoo symbol.

### Preferred Provider

Settings now stores a preferred price provider.

The provider engine can prioritize:

1. HDFC
2. ICICI
3. Zerodha
4. Upstox
5. Yahoo

or start with a user-selected provider and then use fallback paths.

---

# Recommended V8 — Reliability & Reporting

Priority: high, cost: low.

Add:

- automatic dated database backups;
- Backup/Restore screen;
- stale-price indicator;
- price source and quote timestamp columns;
- full connection health panel;
- provider success/failure counters;
- export family/member reports to Excel/PDF;
- one-click transaction export.

---

# Recommended V9 — Performance Analytics

Add:

- XIRR;
- CAGR;
- absolute return;
- realised vs unrealised gain dashboard;
- dividend-inclusive total return;
- security/member/broker performance ranking;
- benchmark comparison.

---

# Recommended V10 — Indian Tax & Corporate Actions

Add:

- FIFO lot engine for tax reporting;
- short-term/long-term classification;
- Indian equity/MF capital-gain working;
- dividend/interest schedules;
- corporate-action master;
- bonus/split/rights/merger adjustment engine;
- tax-year export.

Tax outputs should be reconciled with broker statements and current law before filing.

---

# Recommended V11 — Broker Import Automation

Build deterministic statement adapters for:

- HDFC Securities;
- ICICI Direct;
- Zerodha;
- Upstox;
- SBI Securities;
- CAMS;
- KFintech;
- CAS statement formats.

Prefer deterministic CSV/XLSX imports before expensive OCR/AI extraction.

---

# Recommended V12 — Family Wealth Matrix

Extend beyond shares/mutual funds:

- fixed deposits;
- recurring deposits;
- PPF;
- EPF;
- NPS;
- bonds;
- sovereign gold bonds;
- insurance value/reference;
- property summary;
- bank deposits;
- loans/liabilities;
- family net-worth dashboard.

---

# Recommended V13 — Goals & Risk

Add:

- education goal;
- retirement goal;
- emergency reserve;
- target asset allocation;
- deviation/rebalancing alerts;
- sector concentration;
- single-stock concentration;
- family-member exposure;
- broker concentration;
- maturity calendar.

---

# Recommended V14 — Security & Multi-User

Add:

- read-only member role;
- editor role;
- administrator role;
- activity/audit log;
- encrypted secret storage;
- encrypted backup;
- optional two-factor authentication;
- idle logout;
- account lockout rules.

---

# Recommended V15 — LAN / Private Cloud

For broader family access:

- trusted LAN deployment;
- Docker packaging;
- reverse proxy;
- HTTPS;
- role-based authentication;
- optional encrypted cloud backup.

Do not expose the current development Streamlit server directly to the public internet without deployment hardening.

---

# Long-term optional integrations

- Google Drive/OneDrive encrypted backup;
- email/WhatsApp alert service;
- scheduled price refresh;
- corporate-action feeds;
- approved broker holdings APIs;
- depository/CAS imports;
- mobile/PWA interface;
- AI research assistant grounded in retrieved evidence;
- watchlists and research notes.

---

# Development priority philosophy

Before adding expensive APIs or AI features:

1. protect the database;
2. guarantee transaction correctness;
3. guarantee identifier correctness;
4. show quote freshness/source;
5. build reliable reports;
6. add analytics;
7. add tax/corporate actions;
8. automate broker imports;
9. only then expand cloud/AI/mobile features.

This keeps Family Investment Matrix affordable, auditable and maintainable.
