# Equity Research Framework

An AI-Enabled Equity Research & Investment Decision Framework for Indian listed
companies — built through 8 milestones plus a set of targeted hardening passes,
end to end, with every quantitative claim traceable to a real calculation and
every AI-generated claim explicitly labeled as such.

**This is a decision-support tool.** It does not predict stock prices and does
not guarantee investment outcomes. Every report it produces ends with that
disclaimer, and every AI-generated interpretation is marked Level 2 (AI
Interpretation) as distinct from Level 1 (Verified/Calculated) data — see
[Core Design Principles](#core-design-principles) below.

The sample data bundled in `data/sample/` is for **Sona BLW Precision
Forgings Ltd** (NSE: SONACOMS), a real Indian auto-ancillary company, used
throughout development and testing — every number quoted in this README that
references Sona BLW is a real figure the pipeline actually computed, not an
illustration.

---

## Quickstart (Windows 10/11, 64-bit, Python 3.13)

```powershell
# 1. Confirm Python 3.13 64-bit
python --version
python -c "import platform; print(platform.architecture())"

# 2. Create and activate a virtual environment
py -3.13 -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Run the test suite (should show "727 passed" or higher)
pytest

# 5. Copy the environment template and fill in what you need (see Configuration below)
copy .env.example .env

# 6. Launch the dashboard
streamlit run app/main.py
```

If any step fails, see [Troubleshooting](#troubleshooting) below before
assuming something is broken — most first-run issues are environment setup,
not application bugs.

---

## What This Project Does

Takes a company from raw data through to a decision-support investment
report, in nine stages:

```
RAW DATA (Excel/CSV/PDF)
  -> DATA VALIDATION
  -> FUNDAMENTAL / CASH FLOW / WORKING CAPITAL ANALYSIS  (deterministic)
  -> TECHNICAL ANALYSIS  (deterministic, requires price history)
  -> CHANGE-DETECTION / TRENDS  (deterministic)
  -> DOCUMENT INTELLIGENCE  (PDF extraction + quarantine)
  -> AI INTERPRETATION  (LLM-backed, document commentary + risk extraction)
  -> VALUATION  (multiples + DCF, always with bear/base/bull scenarios)
  -> RISK REGISTER  (rule-based + AI-assisted, never fabricated)
  -> INVESTMENT SCORE  (AI-IDS, configurable weights, never zero-fills missing data)
  -> INVESTMENT THESIS  (BUY/HOLD/AVOID, with mandatory invalidation triggers)
  -> REPORT  (19-section Markdown + Word .docx)
```

Every stage after "RAW DATA" is independently testable and has its own test
suite under `tests/unit/` — see [Testing](#testing) below.

---

## Core Design Principles

These aren't just described in the code comments — they're enforced
structurally, and the test suite specifically checks for violations:

- **No fabricated data.** A metric that can't be honestly computed returns
  `status=MISSING_INPUT` / `NOT_APPLICABLE` / `UNAVAILABLE` with `value=None`
  — never a guessed or zero-filled number. Example: Payable Days and Cash
  Conversion Cycle are permanently `NOT_APPLICABLE` in this project because
  the source data has no Trade Payables line — computing CCC without its
  payables leg would be a *different, misleading* metric, not "CCC minus a
  piece."
- **Deterministic and AI-generated content are structurally separated.**
  `app/analysis/`, `app/valuation/`, `app/scoring/` never import from
  `app/ai/` for their core calculations. Only `app/ai/` calls an LLM.
- **Missing data is never zero-filled.** The Investment Score (Module 9)
  renormalizes weights over whatever components have usable data rather than
  scoring an unavailable component as 0 — tested explicitly in
  `tests/unit/test_investment_score.py`.
- **Document content is data, never instructions.** Every LLM prompt that
  includes text extracted from an uploaded PDF wraps it in explicit
  `<document_excerpt>` delimiters with a preamble stating it is inert data —
  see `app/ai/prompts.py` and the quarantine layer in `app/documents/quarantine.py`.
- **No overconfident language.** Phrases like "guaranteed return" or
  "risk-free" are structurally impossible in a generated thesis —
  `app/ai/thesis_generator.py`'s lint neutralizes them even if the LLM
  produces them, and a report-level regression test scans the *entire*
  generated report independently.
- **Never claim human validation that didn't happen.** A `HumanReview`
  object is only ever created by an explicit UI action; the report's Human
  Validation Checklist renders every item as unreviewed by default.

---

## Architecture

```
app/
|-- main.py               Streamlit entrypoint (streamlit run app/main.py)
|-- config.py              Centralized settings (.env-driven)
|
|-- core/                  Shared models, enums, exceptions, audit trail, logging
|                          (imported by every other layer; no LLM/network code here)
|
|-- data/                  Module 1 -- Ingestion
|   |-- loaders.py            Screener.in Excel parser + NSE Shareholding
|   |                          Pattern CSV parser (promoter holding history)
|   |-- financial_data.py     Raw -> canonical FinancialStatement, unit conversion
|   |-- validators.py         8 data-quality rules
|   `-- market_data.py        CSV (primary) / yfinance / Rediff price providers
|
|-- documents/             Module 4 + 12 -- Document Intelligence & Quarantine
|   |-- pdf_parser.py          Page-level PDF text extraction (PyMuPDF)
|   |-- quarantine.py          Instruction-pattern detection/neutralization
|   |-- source_tracker.py      Wraps pages into quarantined DocumentEvidence
|   `-- extractor.py           Keyword-based section classification
|
|-- analysis/              Module 2/3/8 -- Deterministic Analysis (no LLM calls)
|   |-- fundamentals.py        Growth, profitability, balance-sheet ratios
|   |-- cashflow.py            CFO, FCF, FCF conversion, capex estimation
|   |-- working_capital.py     Receivable/inventory days, CCC
|   |-- shareholder.py         EPS, dividend payout
|   |-- technical.py           SMA/RSI/MACD/Bollinger/beta (hand-rolled)
|   |-- trends.py              Module 3 change-detection engine
|   |-- peers.py                Peer relative-valuation comparison
|   `-- risk.py                 Rule-based + AI-assisted risk register
|
|-- valuation/              Module 7 -- Valuation (no LLM calls)
|   |-- multiples.py            P/E, EV/EBITDA, P/B, EV/Sales
|   |-- dcf.py                  Full DCF with sensitivity analysis
|   `-- scenarios.py            Bear/Base/Bull scenario runner
|
|-- scoring/                 Module 9 -- Investment Score
|   `-- investment_score.py     AI-IDS: 6 weighted components, renormalization
|
|-- ai/                      Module 5/6 -- AI Interpretation Layer
|   |-- llm_client.py            OpenAI + Gemini clients, FallbackLLMClient,
|   |                              UsageTrackingLLMClient, FakeLLMClient
|   |-- pricing.py                Per-token pricing table for cost estimation
|   |-- rate_limiting.py         Batch-call pacing + duration estimates
|   |-- prompts.py                Data/instruction-boundary-enforcing prompts
|   |-- json_utils.py             Strict-JSON response parsing
|   |-- document_analysis.py      Management/business commentary extraction
|   `-- thesis_generator.py       Investment thesis + banned-phrase lint
|
|-- reports/                 Module 14 -- Report Generation
|   |-- generator.py              19-section Markdown report assembler
|   |-- templates.py              Markdown formatting helpers (Level 1/2/3 labels)
|   |-- metric_tables.py          Shared pivot/table logic (Financial Dashboard
|   |                              UI + report generator render identically)
|   |-- docx_export.py            Markdown -> Word .docx converter (landscape
|   |                              orientation + smaller font for wide tables)
|   `-- history.py                Report History tracking across generations
|
| `-- ui/                       Dashboard
    |-- dashboard.py               Navigation shell, session state,
    |                              Save/Load Session sidebar controls
    |-- session_io.py              Session save/reload serialization
    `-- pages/                     8 pages (Company Input, Financial
                                    [pivot table: metrics x years],
                                    Technical [Plotly candlestick + RSI
                                    subplot + volume], Valuation [+ peer
                                    upload, DCF scenarios/sensitivity],
                                    Risk [+ business/management commentary
                                    extraction, pledge analysis], AI-IDS
                                    Score, Human Review, Final Thesis)
```

---

## Configuration

Copy `.env.example` to `.env` and fill in what you need. Nothing in `.env`
is required to run the deterministic pipeline (data ingestion, fundamentals,
cash flow, technical analysis, valuation multiples, DCF, rule-based risk
detection) — only the AI-assisted features (document commentary extraction,
AI risk extraction, thesis generation) need `OPENAI_API_KEY`.

| Variable | Required for | Default |
|---|---|---|
| `OPENAI_API_KEY` | AI interpretation, thesis generation | none — these features raise a clear error if unset |
| `OPENAI_MODEL` | (same) | `gpt-4o` |
| `MARKET_DATA_PROVIDER` | Technical analysis | `csv` (uses the bundled sample price history) |
| `CSV_PRICE_HISTORY_PATH` | (same) | `./data/sample/SONACOMS_NSE_price_history.csv` |
| `WEIGHT_*` (6 variables) | Investment Score weighting | Sum to 1.0; spec defaults (30/15/15/20/10/10%) |
| `LLM_REQUEST_DELAY_SECONDS` | Pacing between batch LLM calls | `0.5` — reduces rate-limit retries on large documents; see below |

The app validates `WEIGHT_*` sums to 1.0 at startup and fails fast with a
clear error if misconfigured, rather than silently producing a distorted score.

### AI provider: Gemini (free tier) + OpenAI (paid backup)

Two interchangeable LLM providers are supported for the AI-assisted
features (risk extraction, business/management commentary, pledge
disclosure analysis, thesis generation). Configure either or both in
`.env`:

- **`GOOGLE_API_KEY`** — Google Gemini, via the current GA `google-genai`
  SDK. Get a free key (no credit card required) at
  [aistudio.google.com](https://aistudio.google.com). Free tier is
  limited to Flash/Flash-Lite models, and free-tier content is used by
  Google to improve their products — fine for public documents (e.g. a
  company's published annual report), **not** recommended for
  confidential/proprietary documents.
- **`OPENAI_API_KEY`** — unchanged from before.

**If both are configured, Gemini is tried first and OpenAI is used only
as an automatic fallback** if a live Gemini call actually fails (e.g.
the free tier's rate limit is exceeded) — see `FallbackLLMClient` in
`app/ai/llm_client.py`. OpenAI is never invoked, and never billed, if
Gemini succeeds. This exists specifically so this project can be
evaluated (e.g. for a capstone submission) entirely on Gemini's free
tier without requiring or billing anyone else's OpenAI key. If only one
key is configured, that provider is used alone.

`scripts/verify_gemini_live.py` mirrors `verify_openai_live.py` for
live verification against the real Gemini API.

### Rough cost estimate (sidebar)

The sidebar shows a running "Estimated Session Cost" total, broken down
by provider, for every AI-assisted call made since the app started —
no need to leave the dashboard to get a rough sense of spend. Built on
`app/ai/pricing.py`'s per-token pricing table (verified against both
providers' pricing pages as of the date shown in the sidebar — AI
provider pricing changes fast, so treat this as a rough estimate, not a
bill) and a `UsageTrackingLLMClient` wrapper that records real token
counts from each provider's own API response. A call whose model isn't
in the pricing table (e.g. one released after the table was last
updated) is excluded from the total and called out explicitly — **never
silently counted as $0**. Always confirm actual spend against your
provider's own dashboard (linked directly in the sidebar).

### Rate limiting / batch LLM call pacing

Every AI-assisted extraction (risk, business/management commentary,
pledge disclosure) makes one API call per document page. On a real
large document this can trigger the OpenAI account's rate limit,
causing the SDK's own automatic retries to silently take several
minutes with no visibility. Three mitigations, all in
`app/ai/rate_limiting.py` and wired into every batch extraction call:

1. **Upfront estimate + confirmation** — before a batch runs, the UI
   shows a rough time estimate and requires an explicit confirmation
   click, so you know what you're starting before you start it.
2. **Real progress bar** — "page N of M" during processing, not a
   generic spinner.
3. **Proactive pacing** — a small delay (`LLM_REQUEST_DELAY_SECONDS` in
   `.env`, default 0.5s) between calls, reducing how often the rate
   limit gets hit in the first place rather than reactively retrying
   after the fact.

### Visual theme

`.streamlit/config.toml` sets a deliberate "Midnight + Electric Teal"
palette instead of Streamlit's generic default red: Midnight primary
(`#172A46`), a light background (`#F6F8FA`), Slate Card secondary
surfaces (`#E5EAF0`), and dark text (`#18212B`). Streamlit's native
theming has exactly one interactive-color slot and no separate "accent"
slot, so Electric Teal (`#00A6A6`) is applied via a small, deliberately
minimal CSS injection (`app/ui/styling.py`) targeting only `st.metric()`
values through the `stMetricValue` data-testid — confirmed to actually
exist in the pinned Streamlit version's frontend bundle before use,
rather than a broad override across many sub-elements that could break
silently across versions. Edit `.streamlit/config.toml` and
`app/ui/styling.py` directly to adjust.

---

## Testing

```powershell
pytest                    # full suite
pytest tests/unit          # unit tests only
pytest tests/edge_cases     # data-quality edge cases only
pytest -v                    # verbose, see every test name
pytest --cov=app --cov-report=html   # coverage report (requires pytest-cov)
```

The suite is built specifically to catch real regressions, not just confirm
code runs:
- **Real data throughout.** Most test files use the actual bundled Sona BLW
  financials/price history/annual-report PDF, not synthetic fixtures — e.g.
  a test asserts FY2026 EPS equals exactly Rs 10.40, cross-checked against the
  company's real reported figure.
- **Independent reference calculations.** RSI, DCF, and other numeric
  functions are checked against hand-worked or independently-coded reference
  values, not just internal self-consistency.
- **No live LLM calls anywhere.** Every AI-layer test uses `FakeLLMClient`
  (`app/ai/llm_client.py`), a deterministic test double — this keeps the
  suite fast, free, and reproducible.
- **Real Streamlit smoke tests.** `tests/unit/test_dashboard.py` uses
  Streamlit's own `AppTest` framework to actually launch the app and
  navigate every page, not just import-check the files.

See [`docs/TESTING_NOTES.md`](docs/TESTING_NOTES.md) for what's been verified
against live external services and what hasn't (see also
[Known Limitations](#known-limitations) below).

### Live service verification scripts

`pytest` never makes a live network/API call — every test uses a fake or
bundled-file data source, on purpose. Two standalone scripts exist
specifically to verify the real external integrations, and are NOT part
of the automated suite:

```powershell
python scripts\verify_yfinance_live.py   # no API key needed
python scripts\verify_openai_live.py     # requires OPENAI_API_KEY in .env
python scripts\verify_gemini_live.py     # requires GOOGLE_API_KEY in .env (free tier)
```

Run these once after setup (or after upgrading either dependency) to
confirm the live integrations actually work on your machine — see
`docs/TESTING_NOTES.md` for what these have already confirmed.

---

## Known Limitations

Documented here rather than glossed over — consistent with this project's
own "no fabricated data" principle applied to its own documentation:

- **`YFinanceProvider` — confirmed working via a real live test** (2026-08-12,
  on the project owner's machine). One real issue surfaced and was fixed in
  the process: the originally-pinned `yfinance==0.2.51` failed against
  Yahoo's current backend (an empty-response error caused by a crumb/cookie
  anti-bot requirement older versions can't satisfy) — upgrading to
  `yfinance==1.5.2` (now the pinned version) resolved it cleanly. The live
  result cross-validated exactly against the bundled CSV data (both sources
  agree on SONACOMS' 2026-08-10 close price to the rupee). Re-run
  `scripts/verify_yfinance_live.py` any time to re-confirm.
  `CSVPriceProvider` remains the primary, default price data source
  (bundled sample covers 2021–2026 daily data for SONACOMS) — yfinance is
  the live-refresh fallback.
- **`RediffMoneyProvider`** only supports same-day current-price lookup via
  the BSE Gainers/Losers snapshot (ported from a real, confirmed VBA macro's
  markup) — it does not support historical price history; use `CSVPriceProvider`
  or `YFinanceProvider` for that. Unlike the other two providers above,
  this one has **not** been live-tested (no pressing need arose once
  `CSVPriceProvider` and `YFinanceProvider` were both confirmed working) —
  it remains the one honest gap in this project's external-service
  verification, documented rather than glossed over.
- **`OpenAIClient` — confirmed working via a real live test** (2026-08-12,
  on the project owner's machine, model resolved to `gpt-4o-2024-08-06`).
  Three real code paths tested successfully: basic completion, document
  analysis (correctly extracted a real, page-sourced governance claim
  from the bundled annual report), and pledge disclosure extraction — the
  most demanding real check, since the actual filing discloses a pledge
  on an *upstream* holding entity's shares rather than Sona BLW's own
  shares. The live model correctly made that distinction on every
  relevant page, matching what had only been verified against
  `FakeLLMClient` before. Re-run `scripts/verify_openai_live.py` any time
  to re-confirm.
- **`GeminiClient` — confirmed working via a real live test** (2026-08-13,
  on the project owner's machine, model `gemini-3.5-flash-lite`). All
  three real code paths succeeded, including the same demanding pledge
  disclosure test — Gemini additionally handled a nuance neither prior
  run explicitly exercised (correctly classifying a cover-letter page
  with no specific percentages as `not_applicable` rather than guessing).
  Re-run `scripts/verify_gemini_live.py` any time to re-confirm.
- **The PDF section classifier is keyword-frequency based**, not a true
  layout/TOC-aware chapter parser. It's a good triage signal (verified
  against the real bundled annual report) but not chapter-perfect — Indian
  annual reports commonly interleave statutory sections.
- **Module 8's risk framework is a hybrid**, not a comprehensive standalone
  system: deterministic rules cover Financial risk only (4 threshold-based
  checks); qualitative risk categories (Business, Governance, Regulatory,
  Market, Management Execution) depend entirely on what the AI extraction
  finds in whatever document pages are supplied — there's no exhaustive
  category coverage guarantee.
- **Promoter Holding/Pledge** are not present in the Screener.in "Data
  Sheet" export this project's loader consumes, so they're `UNAVAILABLE`
  by default — but can be manually entered for the latest period on the
  Company Input page (see the "Promoter Holding / Pledge (Manual Entry)"
  section). Manually-entered values are always flagged as such in every
  downstream metric/report, never conflated with primary-source data.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `py -3.13` not recognized | Only a different Python version is installed, or the Python Launcher isn't on PATH. Try `python -m venv .venv` instead, or run `py -0` to list installed versions. |
| `.venv\Scripts\activate` fails with a script-execution-policy error (PowerShell) | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that PowerShell window first, then retry. |
| `pip install -r requirements.txt` fails on one package | Note the exact error and package name — version pins may need a small bump if a package was yanked from PyPI since this was written. |
| Pasting multi-line code into the `python` interactive prompt scrambles indentation | Windows terminal paste issue, not a code bug — save as a `.py` file and run `python file.py` instead, or use a single-line `python -c "...; ...; ..."` command with semicolons. |
| `streamlit run app/main.py` opens but a page shows an error | Check the terminal output, not just the browser — Streamlit prints the full Python traceback there. |

---

## Further Documentation

- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) — step-by-step guide for a
  non-developer: install, configure, load a company, run analysis, review
  evidence, generate a report, interpret the score.
- [`docs/TESTING_NOTES.md`](docs/TESTING_NOTES.md) — what has and hasn't
  been verified against live external services, and the self-review
  checklist walkthrough.
