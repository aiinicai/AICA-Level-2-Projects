# User Guide

A step-by-step guide for using the Equity Research Framework without writing
any code. If you're setting this up for the first time, follow the
[Quickstart in the main README](../README.md#quickstart-windows-1011-64-bit-python-313)
first — this guide picks up once `pytest` shows tests passing and you're
ready to actually analyze a company.

---

## 1. Install the Application

Covered in the [main README's Quickstart](../README.md#quickstart-windows-1011-64-bit-python-313).
In short: install Python 3.13 (64-bit), create a virtual environment, run
`pip install -r requirements.txt`.

## 2. Configure It

Copy `.env.example` to `.env`. You do **not** need to fill in anything to
start — the deterministic pipeline (financials, cash flow, technical
analysis, valuation, rule-based risk) works with zero configuration.

Only fill in an API key if you want the AI-assisted features: extracting
qualitative commentary from an annual report PDF, extracting qualitative
risks, analyzing a pledge disclosure, and generating a written investment
thesis. Two providers are supported, and you can configure one or both:

- **`GOOGLE_API_KEY`** (recommended, especially for evaluation/testing) —
  Google Gemini. Get a free key, no credit card required, at
  [aistudio.google.com](https://aistudio.google.com): sign in, click
  "Get API Key," and paste it into `.env` next to `GOOGLE_API_KEY=`. The
  free tier covers Flash/Flash-Lite models with modest rate limits — fine
  for analyzing a public document like a company's published annual
  report. **Free-tier content is used by Google to improve their
  products**, so don't use the free tier for confidential/proprietary
  documents — use the paid tier (or OpenAI) for those instead.
- **`OPENAI_API_KEY`** — get a key at
  [platform.openai.com](https://platform.openai.com), paste it into
  `.env` next to `OPENAI_API_KEY=`.

**If you configure both**, Gemini is tried first for every AI-assisted
action, and OpenAI is used only as an automatic fallback if a live
Gemini call actually fails (e.g. the free tier's rate limit is hit) —
OpenAI is never invoked, and you're never billed for it, if Gemini
succeeds. This is useful if you want to run mostly on Gemini's free tier
but still have a paid backup for reliability, or if you're sharing this
project for evaluation and want the evaluator to be able to run
everything on the free tier without needing (or being billed against)
your own OpenAI key.

**Tracking spend without leaving the app:** the sidebar (visible on
every page) shows a running "Estimated Session Cost" total, broken down
by provider, updated after every AI-assisted call. This is a rough
estimate built from a periodically-verified pricing table, not a live
feed from either provider — if a call used a model not in that table
(e.g. a brand-new model released after the table was last updated),
it's excluded from the total and called out explicitly rather than
silently counted as free. For actual billing, use the links the sidebar
provides to each provider's own usage dashboard.

## 3. Launch the Dashboard

```powershell
.venv\Scripts\activate
streamlit run app/main.py
```

A browser tab opens automatically. If it doesn't, the terminal prints a URL
(usually `http://localhost:8501`) — open that manually.

**Saving and resuming your work:** the sidebar (visible on every page) has
a **Session** section. Once a company is loaded, click **Save Session** to
download a single JSON file containing everything computed so far —
financials, every metric, risks, AI interpretations, the thesis, your
Human Review decisions, price data, audit trail. To resume later (or on a
different machine), upload that file via **Load Session** and click
**Restore This Session** — you're back exactly where you left off, with no
need to re-upload the original Excel/PDF/CSV files or re-run any analysis
(including LLM calls, which cost time and money each time). If the app has
changed since you saved (a rare case), the load is best-effort: whatever
can be restored is restored, and you'll see a clear warning listing
anything that couldn't be — never a silent partial loss.

## 4. Load a Company

On the **Company Input** page (the default landing page):

1. Enter the **Company Name** and **Ticker** (e.g. `Sona BLW Precision
   Forgings Ltd` / `SONACOMS`).
2. Choose the **Exchange** (NSE or BSE) and optionally a **Sector**.
3. Upload the **Financials** file — this must be a Screener.in Excel export
   (the "Export to Excel" button on a company's Screener.in page). This is
   required.
4. Optionally upload a **Price History CSV** (an NSE historical-data export
   — download from NSE's website for your ticker) to unlock the Technical
   Dashboard.
5. Optionally upload any combination of documents to unlock AI-assisted
   business/management/risk extraction on later pages. Two groups:
   - **Documents**: Annual Report, Investor Presentation, Earnings Call
     Transcript, Corporate Announcement, Promoter Pledge Disclosure (all PDF)
   - **Quarterly Updates**: Latest Quarterly Results, Investor Presentation
     (Quarterly Meet), Transcript of Quarterly Investor Meet (all PDF) — kept
     as a genuinely distinct source category from the annual documents above,
     since a claim sourced from last quarter's investor meet carries
     different recency than one from the annual report, and the generated
     report/audit trail preserves that distinction rather than merging them
   
   You can upload one, several, or all eight — each is tagged with its exact
   type internally, so a claim the report shows can be traced back to
   precisely which document it came from.
6. Click **Run Analysis**.

## 4b. Promoter Holding / Pledge (Optional)

Screener.in's export doesn't include shareholding-pattern data. Two ways
to add it:

**Historical CSV (recommended, more precise):** upload an NSE
Shareholding Pattern CSV export for your symbol (available from NSE's
website) in the **Shareholding Pattern CSV** uploader on the main form.
Promoter holding is applied to any period whose fiscal year-end date
exactly matches a filing date in the file — periods without an exact
match stay honestly unavailable rather than approximated from a nearby
quarter. If the holding shows a sustained decline across periods, the
Risk Dashboard will automatically flag it as a governance risk (this is
a real signal worth understanding the cause of — lock-in expiry, planned
secondary sales, and dilution from fundraising are all legitimate
explanations, not automatically a red flag). **This file does not
contain pledge data** — pledge comes from a separate NSE filing.

**Manual single-period entry:** if you only have a current-period figure
(from any source), a **Promoter Holding / Pledge (Manual Entry)** section
appears below the main form once financials are loaded — enter both
percentages and click **Apply Promoter Data**. This only affects the
most recent period. Every metric or report line using either method is
always labeled as manually entered/derived from an uploaded filing, not
sourced from the primary Screener data.

**Pledge specifically — three ways to set it, each labeled distinctly:**
1. **Upload a pledge-disclosure PDF** (e.g. a SEBI Regulation 31 filing)
   using the **Promoter Pledge Disclosure PDF** uploader, then go to the
   **Risk Dashboard** and click **Analyze Pledge Disclosure**. This is
   AI-assisted (requires `OPENAI_API_KEY`) and specifically distinguishes
   a pledge on *this* company's own shares from a pledge on an upstream
   holding entity's shares — a real distinction that matters (a promoter's
   parent company pledging its own shares in a different transaction does
   NOT mean this company's shares are pledged).
2. **Type a percentage directly** in the manual-entry Promoter Pledge
   field.
3. **Check "I confirm there is no promoter pledge currently"** if you
   independently know there's no pledge, even without a document. This
   is recorded as a distinct **user assertion**, not confused with a
   document-derived finding — the system never assumes "no document
   uploaded" means "no pledge" on its own.

This runs the deterministic pipeline immediately — no AI calls happen at this
step, so it works even without an OpenAI API key. You'll see a success
message with the number of periods loaded, plus any data-validation warnings
(these are informational, not necessarily errors — e.g. a note about a
sudden share-count change around an IPO date is expected, not a bug).

## 5. Load Financial Data

This happens automatically as part of Step 4 above — there's no separate
step. The uploaded Excel is parsed into a canonical financial-statement
series, unit-converted, and validated in one action.

## 6. Upload Documents

Also part of Step 4 (the PDF uploader). If you skip it initially, you can't
currently re-upload without re-running the whole Company Input form again —
if you want document analysis, upload the PDF the first time.

## 7. Run Analysis

The deterministic analysis (fundamentals, cash flow, working capital,
technical indicators, valuation multiples, rule-based financial risks) all
runs automatically when you click **Run Analysis** on Company Input. Two
further analysis steps are separate, explicit actions (by design — nothing
AI-generated happens without you asking for it):

- **AI-IDS Score**: go to the **AI-IDS Score** page and click **Compute
  AI-IDS Score**. This combines everything computed so far into the overall
  0-100 score.
- **AI-assisted risk extraction**: on the **Risk Dashboard** page, if you
  uploaded a PDF, click **Extract Qualitative Risks from Document**. This
  makes LLM calls (requires `OPENAI_API_KEY`) and takes a few seconds per
  page analyzed.
- **Business & Management commentary extraction**: also on **Risk
  Dashboard** — click **Extract Business & Management Commentary**. This
  is the *only* way to populate the AI-IDS Score's Business/Management
  component; without running it, that component stays permanently
  "unavailable" no matter what else you do. Requires an uploaded document
  with content classified as Business or Management Discussion pages
  (most annual reports have both) and `OPENAI_API_KEY`.
- **Investment thesis**: on the **Final Thesis & Report** page, click
  **Generate Investment Thesis**. Also requires `OPENAI_API_KEY`.

**Before any of the three Risk Dashboard extraction actions actually
run**, you'll see a rough time estimate (e.g. "estimated 3.2-8.1
minutes") and need to click **Confirm and Run** — this exists because
processing a real, large document (dozens or even ~190+ relevant pages)
makes one API call per page, and on some OpenAI account tiers this can
trigger the account's rate limit, causing the OpenAI SDK's own automatic
retry logic to silently take several minutes with no visibility into
what's happening. Once confirmed, a real progress bar shows exactly
which page is being processed, and a small pause between calls (default
0.5s, adjustable via `LLM_REQUEST_DELAY_SECONDS` in `.env`) proactively
reduces how often the rate limit gets hit in the first place. If you're
on a lower-tier account and still see frequent retries in your terminal,
try increasing that setting.

A note on the AI-IDS Score's six components: **Business/Management**
needs the extraction above; **Valuation** needs peer data (see the Peer
Comparison section on Valuation Dashboard, covered under "Interpret the
Score" below) — both stay honestly "unavailable" until you take that
specific action, rather than silently scoring as zero.

## 7b. Financial Dashboard Layout

Metrics show as a **pivot table** — metric names as rows, years as
columns — so you can read a ratio's trend left-to-right across all
periods in one glance, rather than scrolling through a long list
interleaving different years. A **Key Financials** table (Sales/Revenue,
Net Profit, Total Assets) sits above Fundamentals, since these absolute
figures aren't themselves ratios and weren't otherwise included in the
Fundamentals table. The same tabular format is used in the generated
report's Historical Financial Analysis section, so what you see on this
page and what ends up in the downloaded report match exactly.

## 8. Review Evidence

Every AI-generated claim is labeled `[LEVEL 2 - AI Interpretation]` with a
confidence rating (high/medium/low) — visually distinct from
`[LEVEL 1 - Verified/Calculated]` data everywhere it appears, including in
the final report. Nothing AI-generated is ever presented as a verified fact.

Use the **Human Review** page to actually record your review of each AI
claim (and the generated thesis, if any): enter your name once at the top,
then Accept or Reject each item, with an optional note. Reviewing the same
item again updates your existing review rather than creating a duplicate.
The generated report's Human Validation Checklist reflects exactly what's
been reviewed here — anything you haven't gotten to shows as "not yet
reviewed," honestly, rather than being silently marked complete.

## 9. Generate the Report

On the **Final Thesis & Report** page, click **Generate Report**. A
**"Read Report Here"** section opens immediately, showing the full
report rendered right in the browser — no download needed to actually
read it, and this is usually the fastest way to review what was
generated.

Two download buttons are also available if you want a file:
- **Download Report (Word .docx)** — recommended if you want an actual
  file to open, print, or share. Opens directly and readably in
  Microsoft Word.
- **Download Report (Markdown)** — plain text with markdown syntax
  (`##`, `**`, etc.), useful for version control or further editing in a
  tool that understands markdown. **If you just double-click a `.md`
  file in Windows, it typically opens in Notepad showing the raw
  syntax, not a nicely formatted document** — that's expected for this
  file type, not a bug. Use the Word download or the in-app "Read
  Report Here" section instead if you just want to read it.

You can generate a report at any point, even before running every analysis
step — sections with no data yet will honestly say so (e.g. "*No investment
thesis has been generated for this run*") rather than being silently
omitted or showing a placeholder that looks like real content.

**Report History:** every time you click **Generate Report**, it's added
to a running history table below (newest expandable at the top), showing
the score, recommendation, and the change from the previous generation —
so you can see the thesis evolve as you refine assumptions, add documents,
or review AI claims, rather than only ever having the latest version. Each
historical entry stores its own complete report, downloadable independently
at any time. History resets when you load a new company on Company Input
(a fresh dataset shouldn't be mixed with a different company's history),
and is included when you Save Session, so it survives across sessions too.

A third download button, **Download Audit Trail (JSON)**, appears whenever
the current run has recorded audit entries — this happens automatically as
you use Company Input (every key metric, validation flag, and data source
gets logged with its calculation formula), giving you a machine-readable
record of exactly where every number in the report came from.

## 10. Interpret the Score

The AI-IDS (AI-Assisted Investment Decision Score) is a 0-100 score built
from 6 weighted components:

| Component | Default Weight | What it measures |
|---|---|---|
| Fundamentals | 30% | Revenue growth, margins, ROE/ROCE, leverage |
| Cash Flow Quality | 15% | How well reported profit converts to real cash |
| Business/Management | 15% | Confidence-weighted average of AI-extracted commentary |
| Valuation | 20% | How the stock's multiples compare to peers |
| Technical | 10% | RSI + price vs. 200-day moving average |
| Risk/Governance | 10% | Penalty-based score from identified risks |

To populate the **Valuation** component with real peer data (rather than
leaving it unavailable), go to the **Valuation Dashboard** page and use the
**Peer Comparison** section: upload one or more peer companies' Screener.in
Excel exports (name the files after the company, e.g. `Uno Minda.xlsx` —
the filename becomes the peer's display name) and click **Compute Peer
Comparison**. Each peer's multiples are computed with the exact same
pipeline used for the subject company, then compared via median and
premium/discount.

The same page also offers **Bear/Base/Bull DCF scenarios** and a **WACC x
Terminal Growth sensitivity grid**, both built on top of the single-point
DCF you run first — adjust the Bear/Bull haircut/uplift magnitudes and the
sensitivity step sizes as you like; nothing is auto-derived without your
input.

**Adjusting the weights interactively:** the AI-IDS page has a slider for
each of the 6 components, defaulting to the `.env`-configured split
(30/15/15/20/10/10%). Move them to explore "what if I cared more about
Valuation and less about Technical" — you don't need the sliders to sum to
exactly 100%; they're automatically renormalized, and both the raw values
you set and the resulting effective weights are shown so nothing changes
invisibly. **Slider adjustments are session-only** — they never modify
your `.env` file — so click **Reset to Configured Defaults** at any time
to return to your actual configured weights, or just reload the page.

**Important nuance**: if a component has no usable data (e.g. no price
history was uploaded, so Technical is unavailable), it is **excluded
entirely** from the score rather than counted as zero — the remaining
components' weights are proportionally rescaled ("renormalized") so they
still sum to 100%. The report and dashboard both show which components (if
any) were excluded this way, so a high score built from only 3 of 6
components is visibly different from one built from all 6.

The score is a transparent, documented scoring *convention* — not an
objective truth. See each component's rubric in
`app/scoring/investment_score.py`'s docstrings if you want the exact
thresholds used.

**The final recommendation (BUY/HOLD/AVOID)** always requires human review —
the dashboard and every generated report say so explicitly, and this is not
boilerplate: the underlying thesis object is structurally incapable of
claiming a human already validated it unless you've actually done so.
