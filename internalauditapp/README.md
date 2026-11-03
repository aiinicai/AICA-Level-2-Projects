# AuditPro - Internal Audit Management System

A local, single-user internal audit documentation tool for single entities and multinational groups.
The frontend is JavaScript (no build step), the backend is Python (Flask) and the database is SQLite.

## Quick start

1. Install **Python 3.10 or later** from python.org and tick "Add python.exe to PATH".
2. Double-click **`run_app.bat`**. On first run it creates `.venv`, installs the dependencies listed in
   `requirements.txt` (Flask, python-docx, python-pptx, openpyxl), starts the server and opens
   http://127.0.0.1:5050 in your browser.
3. On the start screen, **create a new company** (single entity or multinational group with its legal
   entities) or **load the demo company** to explore.

Data is stored in `data\internal_audit.db`. Uploaded evidence goes to `data\uploads` and generated
reports to `data\exports`. To back up, copy the `data` folder.
Optional environment variables: `AUDIT_APP_PORT` (default 5050) and `AUDIT_APP_NO_BROWSER=1`.

## Features (modelled on TeamMate+, AuditBoard and HighBond)

| Area | What it does |
|---|---|
| Company & entities | Multi-company files, group structure (holding, subsidiaries, branches, JVs), country, currency, industry per entity |
| Audit universe & risk assessment | Auto-built from the library for each entity. Six weighted risk factors give an inherent score (0-100), a risk level, a suggested audit frequency and a 5x5 heat map |
| Risk-based audit plans | Annual plans with available vs budgeted hours. One click generates engagements from High/Medium-risk units, spread across quarters. Exports a Word plan document |
| Engagements | Objectives, scope, team, dates, budget, status workflow (Planned > Planning > Fieldwork > Reporting > Closed) |
| Work program (RACM) | Loaded from the library: risk, assertion, control, type, nature, frequency, key/fraud flags and test steps. Each row has a workpaper with population, sample size, design and operating-effectiveness results, testing notes, conclusion and WP reference |
| Sign-offs & review | Preparer and reviewer sign-off. The reviewer must be a different person, and open review notes block review sign-off |
| PBC lists | Document request list generated from the library, with status tracking |
| Findings | Condition, criteria, cause, effect, recommendation, rating, root cause, financial impact, management response, action owner, due and revised dates, repeat flag. A finding can be raised directly from a failed workpaper |
| Action tracking | Follow-up history, overdue detection, ageing, implementation rate |
| Sampling | Frequency-based guidance, attribute sampling, monetary unit sampling, and reproducible random selection with a seed |
| Data analytics (CAATs) | Upload CSV/Excel and run: duplicates, Benford's law, weekend/holiday postings, round amounts, outliers, sequence gaps, split transactions, just-below-threshold, SoD (creator = approver), period-end postings, stratification. Exceptions export to Excel |
| Evidence | File attachments per engagement and per workpaper |
| Reports | Word audit report, PowerPoint Board/Audit Committee presentation, Excel RACM + PBC, findings tracker, universe register |
| Audit trail | Log of every create, update, delete and sign-off |

## Procedure library (`backend/library`)

52 processes and 474 risk-control-procedure rows. Each process also has audit objectives, a PBC list,
analytics ideas and KPIs.

- **Common (14):** Governance & entity-level controls, Procure-to-Pay, Order-to-Cash, Inventory,
  Treasury, Payroll & HR, Fixed Assets, Financial Close, Tax (VAT/CT/TP/Customs), ITGC,
  Legal & Contracts, Intercompany & Related Parties, Budgeting & MIS, ERM & BCP.
- **Home Retail (9):** POS & cash, merchandising & pricing, shrinkage, returns, loyalty & gift cards,
  delivery & after-sales, DC/warehouse, supplier rebates & consignment, store expansion & leases.
- **E-commerce (9):** OMS & fulfilment, payment gateway/BNPL reconciliation, COD & 3PL, fraud,
  returns & refunds, marketplaces, digital marketing & promo codes, platform change management,
  data privacy & cyber.
- **Building Material Trading (9):** credit management, quotations & pricing, project sales & site
  delivery, imports/LC/customs, yard stock, fleet, supplier rebates, cut-to-size processing,
  collections & PDCs.
- **Real Estate Developer (11):** land & feasibility, approvals, tendering, project cost control &
  variations, off-plan sales & brokers, escrow & RERA, IFRS 15 revenue, handover & DLP,
  facility management & service charges, leasing, AML/KYC.

To extend the library, add a dict to the relevant module's `PROCESSES` list. The schema is described
at the top of each file. Restart the app afterwards. If a library file has a syntax error, the app
still starts and shows the error on the start screen.

## Project structure

```
run_app.bat            installer + launcher
requirements.txt
backend/app.py         Flask API + static file server
backend/db.py          SQLite schema and helpers
backend/services.py    risk scoring, sampling, ratings, library loading
backend/analytics.py   CAAT tests (pure Python)
backend/reports.py     Word / PowerPoint / Excel generation
backend/seed.py        demo company
backend/library/       audit procedure library
frontend/              index.html, css/, js/ (single-page app)
data/                  database, uploads, exports (created at first run)
```
