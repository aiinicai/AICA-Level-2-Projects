# Financial Statement Flux Analyzer

**AICA Level 2 Capstone Project — Batch 89**
**Author:** CA Shrey Chopra — Director of Accounting

---

## ⚠️ Usage notice — read before anything else

> This tool was developed solely as a submission for the ICAI AICA (AI for
> Chartered Accountants) Level 2 capstone project. It is provided for
> **evaluation purposes only** and is **not licensed for commercial,
> production, or client-facing use**. No part of this application, its
> source code, or its output templates may be copied, redistributed, or
> reused without the **prior written permission of the project owner**.

This notice is reproduced in the web app's footer and on every exported
Excel, PDF, Word, and CSV file.

---

## 1. Purpose

Controllership teams close the books every period and must explain every
material movement in the financial statements before the numbers reach
the CFO and the auditors. This tool automates the mechanical parts of
that "flux review" — the variance math, the materiality screening, and a
senior-manager-grade first-pass explanation for every flagged line —
while keeping the **final judgement squarely with the controller**, never
with the rule engine or the optional AI step.

## 2. What changed from the v1 prototype

| | v1 (prototype) | v2 (this submission) |
|---|---|---|
| Interface | Streamlit widgets | A real web app — Flask backend + custom HTML/CSS/JS front end, built and styled like a product people would pay for |
| Input | One combined CSV with a `period` column | **Two separate files** — one per period — matching how a preparer actually pulls a trial balance |
| Scope | One generic flux table | **Income Statement and Balance Sheet handled as separate modes**, each with statement-appropriate commentary framing |
| Comparison | Two arbitrary periods | Four named comparison types: **Month-over-Month, vs. Prior Quarter-End, vs. Prior Year-End, Year-over-Year Same Period** |
| Commentary tone | Plain rule-based sentence | **Big 4 senior-manager register**: severity-tiered, category-aware professional-skepticism framing, explicit ask for preparer support |
| Governance | None — the table was the answer | **Controller sign-off workflow**: every material line is Pending until a named controller marks it Approved; exports are watermarked DRAFT until every material line is signed off |
| Export | Excel + PDF | **Excel, PDF, Word, and CSV** — all carrying the sign-off status and the usage notice |

### 2.1 Reviewer-feedback polish pass

An early reviewer of this submission asked for the table to be sortable
and filterable, for the AI's wording to be kept visibly separate from
what the controller actually decides, for the exports to read like an
actual Big 4 close-review deck rather than a plain table dump, for a
way to view amounts in $000s/$Mn, and for the sample data to show off
more of the engine. All of that shipped as a second pass:

| | Before | After |
|---|---|---|
| Commentary | One shared, editable field | **Two columns, end-to-end** (UI, every export): `AI-Generated Commentary` (system-drafted, read-only, reference only) and `Controller Final Commentary` (the one editable, authoritative field — this is what a FINAL export carries) |
| Review table | Fixed order, no filtering | **Click-to-sort** every column, **filter** by entity/category/severity/status, and a **live search box** on line item — all client-side, instant |
| Amount view | Always full dollars | **Actual / $000s / $Mn toggle** — rescales every amount on screen (table, chart, KPI tiles) instantly, no re-export needed |
| Excel | A styled table with conditional formatting | A genuine **Excel Table object** (native AutoFilter + sortable column headers, banded rows), a live **Display Units dropdown** whose formulas rescale the whole sheet, a cover/executive-summary sheet with KPI tiles and an embedded variance-bridge chart, and print-ready landscape layout |
| PDF | One continuous landscape table | A proper **report package**: cover page, contents, an executive summary page with KPI tiles and the same bridge + severity charts, an entity summary, then one **card per material line** (fact table + both commentary columns, clearly labelled) — portrait, page-numbered, footer on every page |
| Sample data | 3 entities × ~9 lines, single-period feel | 3 entities × **15 P&L / 14 balance-sheet lines**, with a deliberate mix of severities, a brand-new balance, a balance run to zero, and a **balance sheet that actually ties** (Assets = Liabilities + Equity, Retained Earnings rolls forward by net income) in both periods |

## 3. How it works

1. **Pick a statement** — Income Statement or Balance Sheet. Each has its
   own category vocabulary (Revenue/Cost of Sales/Opex/Other for P&L;
   Assets/Liabilities/Equity for balance sheet) and its own commentary
   framing.
2. **Pick a comparison type** — Month-over-Month, vs. Prior Quarter-End,
   vs. Prior Year-End, or Year-over-Year Same Period. This only changes
   the wording and report header; the underlying variance math is the
   same regardless of label, exactly as it would be on a real close
   calendar.
3. **Upload two files** — a prior-period trial balance and a
   current-period trial balance, each a simple `entity, category,
   line_item, amount` extract. No combined file, no period column to get
   wrong.
4. **Set one materiality %.** Lines under $1,000 are never flagged,
   whatever the percentage.
5. **(Optional) AI-enhanced commentary.** An LLM (OpenAI) can polish the
   rule-based draft into smoother prose — it is instructed to preserve
   every number and every ask, and never invents a root cause. It never
   decides materiality, and it never marks anything as resolved.
6. **Review as controller.** Every material line starts "Pending," with
   the AI-Generated Commentary shown alongside an editable Controller
   Final Commentary box (pre-filled with the same draft, but tracked as
   a completely separate field). Edit the controller's text, set a
   status (Explained / Approved / Rejected), and record a reviewer. Sort
   any column, filter by entity/category/severity/status, or search a
   line item to work through a long list efficiently. Only **Approved**
   lines count toward sign-off.
7. **Sign off and export.** Enter the controller's name and title. Once
   every material line is Approved and sign-off is recorded, exports
   switch from **DRAFT** to **FINAL — CONTROLLER-APPROVED** — in Excel,
   PDF, Word, or CSV, each carrying both commentary columns clearly
   labelled so a reviewer can always see what the AI said versus what
   the controller decided.

## 4. Project structure

```
AICA-L2-Batch-89-Shrey-Chopra/
├── README.md
├── requirements.txt
├── run.py                       # Entry point: python run.py
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── flux_engine.py           # Variance/materiality logic — statement- and comparison-aware, no UI code
│   ├── ai_commentary.py         # Big-4-tone rule engine + optional LLM polish layer
│   ├── review_store.py          # Controller sign-off workflow state
│   ├── legal.py                 # Single source of truth for the usage notice
│   ├── routes.py                # Flask API + page routes
│   ├── exports/
│   │   ├── charts.py            # Shared matplotlib bridge/severity charts (Excel + PDF)
│   │   ├── excel_export.py
│   │   ├── pdf_export.py
│   │   ├── word_export.py
│   │   └── csv_export.py
│   ├── templates/index.html
│   └── static/
│       ├── css/app.css
│       └── js/app.js
├── sample_data/
│   ├── income_statement_prior.csv / _current.csv
│   └── balance_sheet_prior.csv / _current.csv
└── screenshots/
```

`flux_engine.py`, `ai_commentary.py`, and `review_store.py` have no Flask
dependency — they can be unit tested or reused independently of the web
layer.

## 5. Setup & usage

### Prerequisites
- Python 3.9+

### Install & run
```bash
cd AICA-L2-Batch-89-Shrey-Chopra
pip install -r requirements.txt
python run.py
```
Open **http://localhost:5000** in your browser.

`openai` in `requirements.txt` is only needed if you try the optional
AI-polish toggle — the app works fully without it.

### Try it
Click **"Use bundled sample data instead"** to run the tool immediately
against fictional data for both statements. To use your own data, upload
two files — one per period — with columns:

| Column | Description |
|---|---|
| `entity` | Legal entity / cost center |
| `category` | Revenue / Cost of Sales / Operating Expenses / Other Income-Expense (Income Statement) or Assets / Liabilities / Equity (Balance Sheet) — optional; uncategorized lines get neutral framing |
| `line_item` | The specific line |
| `amount` | Balance for that line in that period (expenses/contra-accounts negative) |

## 6. Technology used

| Layer | Tool | Role |
|---|---|---|
| Backend | Flask (Python) | API + page serving |
| Frontend | Vanilla HTML / CSS / JS | Full control over look and interaction — no framework build step |
| Data processing | pandas | Merge periods, compute variance, materiality logic |
| Excel export | openpyxl | Native Excel Table (AutoFilter), heatmap, live unit-scale formulas, embedded charts, sign-off sheet |
| PDF export | ReportLab | Cover page, executive summary, per-line commentary cards, page numbers |
| Word export | python-docx | Editable report for a broader close memo |
| Charts | matplotlib | Variance-bridge (waterfall) and severity-distribution charts, shared by the Excel and PDF exports |
| Generative AI (optional) | OpenAI API (`gpt-4o-mini`) | Commentary wording polish only |

## 7. Design decisions worth explaining to an examiner

- **Two files, not one.** A preparer pulls a trial balance one period at
  a time from the ERP; forcing them to hand-merge two periods into one
  CSV with a period column first is an artificial step. The app does
  that merge internally (`flux_engine.compute_flux`, an outer join on
  entity/category/line_item).
- **Statement-aware commentary.** A receivables increase and a revenue
  increase call for different professional-skepticism framing — the
  first asks about existence/recoverability, the second about cut-off
  and corroboration. `ai_commentary.py` encodes this as `IS_FRAMING` /
  `BS_FRAMING` dictionaries, keyed by category and direction of
  movement, so the wording is never generic.
- **Severity tiers, not a flat flag.** A line breaching the threshold by
  a hair and a line breaching it by 3x are not the same problem — the
  engine tags each as `standard`, `elevated`, or `high` and the opening
  sentence reflects that urgency.
- **AI never gets the final word.** `enhance_commentary()` only rewrites
  prose; `review_store.py` is a completely separate mechanism that
  tracks a human controller's decision per line, and exports are
  watermarked DRAFT until a **named** controller has approved every
  material line. This was a specific, explicit design requirement for
  this submission and is enforced in the backend (`is_ready_for_final_export`),
  not just the UI — an export route cannot be tricked into returning
  FINAL by editing the page.
- **A real web app over Streamlit.** Streamlit is fast to prototype in
  but its component styling is constrained. A Flask backend with a hand-
  built frontend gives full control over layout, interaction, and visual
  polish — closer to something a controller would actually want to use
  daily — while keeping the core logic (`flux_engine.py`,
  `ai_commentary.py`) completely UI-agnostic and reusable.
- **AI-Generated vs. Controller Final are two separate fields, not one
  that gets overwritten.** Overwriting the AI's draft the moment a
  controller edits it would destroy the audit trail of what the model
  actually said. `review_store.py` keeps `ai_commentary` immutable once
  set and `controller_commentary` as the one editable field — every
  screen and every export shows both, side by side, clearly labelled.
- **A live unit-scale toggle in Excel, not three separate exports.**
  Rather than generating an "Actual," a "$000s," and a "$Mn" workbook,
  the Flux Detail sheet stores raw amounts in hidden helper columns and
  drives the visible Prior/Current/Variance columns off a formula
  keyed to a "Display Units" dropdown (`=RawValue/ScaleFactor`). Pick a
  unit in Excel and the whole sheet — and the entity chart figures on
  screen — rescale instantly, with no re-export.
- **Charts are generated once, shared by Excel and PDF.**
  `exports/charts.py` has no Flask/openpyxl/ReportLab dependency of its
  own — it takes plain row dicts and returns PNG bytes — so the variance
  bridge and severity charts are pixel-identical in both formats and can
  be unit tested independently of either export.

## 8. Where this could go next — toward a real-life product

These weren't built for this submission (scope), but are the natural next
steps if this were taken from capstone to production:

- **ERP/GL connectors** (Tally, SAP, Oracle, NetSuite, D365) so trial
  balances load directly instead of via CSV/XLSX upload.
- **Persistent audit trail** — a real database (not the in-memory
  `review_store`) recording every status change, every commentary edit,
  and every sign-off, with who/when, queryable across close cycles.
- **Role-based access** — Preparer, Reviewer, Controller as distinct
  logins, so "final judgement rests with the controller" is enforced by
  authentication, not just a name typed into a text box.
- **Multi-period trend view** — a rolling 5–8 period sparkline per line
  item, not just a two-period comparison, to catch a slow drift that no
  single-period threshold would flag.
- **Budget/forecast tie-out** — flux against budget or latest forecast,
  not only against the prior period, which is often the more decision-
  relevant comparison for management reporting.
- **Anomaly detection beyond a flat threshold** — Benford's Law screening
  or z-score outlier detection across GL accounts, to catch unusual
  patterns a simple % threshold would miss.
- **Evidence attachments** — let the preparer attach the supporting
  document (invoice, contract, board minute) directly to a flagged line,
  so the "obtain and document explanation" ask has somewhere to land.
- **Consolidation roll-up** — group-level flux across entities with
  intercompany eliminations, not just entity-by-entity review.
- **Configurable, scaled materiality** — thresholds that scale by entity
  size or account type rather than one flat % for every entity.
- **Notification digest** — a daily/close-week email or Slack summary of
  newly flagged high-severity items, so reviewers aren't polling the
  tool.
- **API/embeddability** — expose the flux engine as an API so it can sit
  inside an existing close-management platform rather than as a
  standalone tool.
- **Multi-user, real-time review** — several preparers and one controller
  working the same run concurrently (websocket-pushed row updates,
  row-level locking so two people don't overwrite the same commentary),
  instead of one browser tab owning the run.
- **Drill-down from the export back to the app** — a QR code or link on
  each PDF/Excel line that reopens that exact run and row in the web
  app, so a reviewer with a printed binder can jump straight to editing.
- **Saved materiality/entity templates per client or business unit** —
  today's threshold and category vocabulary are set fresh each run;
  a real deployment would let a controller save "how we review Entity X"
  once and reuse it every cycle.
- **Report themes / white-labelling** — swap the navy-and-gold palette
  and logo per client or business unit without touching code, for a firm
  running this across multiple engagements.
- **Prior-period commentary recall** — surface last cycle's controller
  note for the same line item next to this cycle's, so a recurring
  variance (e.g. seasonal FX swing) doesn't get re-investigated from
  scratch every close.

## 9. Limitations of this submission

- In-memory review state (`review_store.py`) — restarting the app clears
  all runs; there is no persistent database.
- No authentication — the "controller" is whoever types a name into the
  sign-off field. Fine for a demo/capstone; not fine for production.
- AI step polishes wording only; it does not and should not decide
  materiality or invent a root cause.
- Comparison types are labels chosen by the user, not derived from
  actual calendar dates in the data — the tool doesn't yet know what a
  "quarter" or "year" means for the uploaded periods.

## 10. Security note

No credentials, API keys, or confidential client data are included in
this repository. An OpenAI API key, if used, is entered at runtime in
the browser only — it is never written to disk, logged, or committed.
The bundled sample datasets are entirely fictional.
