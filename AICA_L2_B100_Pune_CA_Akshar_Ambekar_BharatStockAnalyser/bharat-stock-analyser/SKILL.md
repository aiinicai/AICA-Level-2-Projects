---
name: bharat-stock-analyser
description: Data-backed equity research for Indian listed stocks (NSE and BSE). Use this skill whenever the user names an Indian company, NSE symbol or BSE code and asks for a stock analysis, research report, target price, valuation, or whether to buy, hold or sell it (for example "analyse Tata Steel", "is HDFC Bank a buy?", "research report on INFY", "should I hold Reliance?"). Produces a BUY / HOLD / SELL rating with a 12-month target price, a six-pillar scorecard, financial summary, valuation build-up, technical view and peer comparison, delivered as an HTML and PDF research note plus a chat summary.
---

# Bharat Stock Analyser

Turns a stock name into a broker-style research note for the Indian market. A Python engine
fetches the data and computes every number; Claude adds researched context and writes the
narrative. The rating comes from published rules, not from opinion.

## What the user gets

1. A chat summary: rating, target price, upside, the reasons, the risks, key levels.
2. `<SYMBOL>_<YYYYMMDD>_report.html`: a self-contained research note with 20+ exhibits.
3. `<SYMBOL>_<YYYYMMDD>_report.pdf`: the same note as an A4 PDF (when Chrome, Edge or Chromium is installed).
4. `<SYMBOL>_<YYYYMMDD>_analysis.json`: every computed figure, for audit.

Default output folder: `~/Documents/Bharat-Stock-Reports` (override with `--outdir`).

## Workflow (follow these steps in order)

### Step 0. Set up paths and the Python environment

`SKILL_DIR` is the base directory of this skill (shown when the skill loads; it is the folder
that contains this SKILL.md). Use the environment's Python if it exists, otherwise create it once:

```bash
SKILL_DIR="<base directory of this skill>"
if [ -x "$SKILL_DIR/.venv/bin/python" ]; then PY="$SKILL_DIR/.venv/bin/python"; else bash "$SKILL_DIR/scripts/setup_env.sh" && PY="$SKILL_DIR/.venv/bin/python"; fi
```

Setup needs internet access and takes one to two minutes the first time. If creating the
environment fails, try `python3 -m pip install -r "$SKILL_DIR/scripts/requirements.txt"` and
use `PY=python3`.

### Step 1. Run the analysis

```bash
"$PY" "$SKILL_DIR/scripts/analyse.py" "<stock name, NSE symbol or BSE code>"
```

- Accepts names ("tata steel", "zomato", "l&t"), NSE symbols (TATASTEEL), Yahoo tickers
  (TATASTEEL.NS) and 6-digit BSE codes (500470).
- Takes 30 to 60 seconds. Run it in the foreground and wait.
- Exit code 2 means the stock was not found: show the error and ask the user for the exact
  NSE symbol. If the name is ambiguous (for example "Tata" or "Adani"), ask which company
  before running.
- Optional flags: `--outdir DIR`, `--no-pdf`, `--rf 6.4` (risk-free %), `--erp 7` (equity risk
  premium %), `--tg 5` (terminal growth %), `--no-exchange` (skip NSE and BSE filings).

Data sources: Yahoo Finance for prices, annual statements, consensus and peers; NSE filings
for quarterly results (XBRL), results board meeting dates and the shareholding pattern
(promoter, FII, DII, pledge). A quarter filed with NSE replaces Yahoo's figure for that
quarter. If NSE cannot be reached, the report runs on Yahoo alone and the digest says so.

The script prints a Markdown digest: rating and how it was reached, results freshness,
exchange filings, valuation methods, scorecard, annual financials, quarterly change (with the
source of each quarter), technicals, data-backed positives and concerns, peers, feed
headlines, data warnings and output file paths. Read all of it.

### Step 2. Check the data before writing anything

- If the rating line says **PROVISIONAL**, lead the chat reply with that and the reasons. A
  provisional rating is never BUY. Do not present it as a recommendation.
- If the digest has a `Results freshness: CHECK REQUIRED` section, the exchange check did not
  run or failed, and Step 3 item 1 is mandatory. `Results freshness: confirmed with NSE` means
  the filings were checked: the data includes the latest filed quarter, and any later quarter
  is not yet published (the next results board meeting date is shown when known).
- Exchange data notes (for example "Q1FY27 revenue: Yahoo Rs X cr, NSE filing Rs Y cr") show
  where Yahoo disagreed with the filing; the filing figure is used. Mention material ones.
- Read the `Data warnings` section. If it reports a failed download, a source inconsistency,
  a missing quarter, a one-off item or a currency conversion, say so in the chat summary and in
  the commentary risks.
- If a download failed (for example "Company profile: not available"), first re-run Step 1
  once. If it still fails, say that the report is incomplete. On claude.ai this usually means
  network access for code execution is restricted; Claude Code on the desktop is more reliable.
- Note the price date. Prices are end-of-day from Yahoo Finance and can be one day old.
- Feed headlines are unfiltered and can include unrelated companies. Use only the ones that
  are clearly about this company.

### Step 3. Research the context (when web search is available)

Work through this checklist. Record what you found, or "not found", for each item:

1. **Latest results (mandatory).** When freshness is confirmed with NSE, read the results
   release and investor presentation for the latest quarter in the digest (management
   commentary, segment figures, guidance). Otherwise search the NSE or BSE filing and the
   company's results release for any quarter newer than the latest one in the digest. If one
   is published, set `newer_results` in the commentary (quarter, date, source) and summarise its
   key figures in `highlights` with the source. The rating then becomes provisional on
   re-render.
2. **One-off items.** Check the results release for exceptional items, fair-value gains, large
   other income, incentive income and tax write-backs. Compare the company's own adjusted
   profit with the digest's "PAT excl. one-offs" estimate and state any gap.
3. **Notes to the results.** Look for auditor qualifications, emphasis of matter, contingent
   liabilities and material receivables (for example PLI incentives awaiting approval).
4. **Business concentration.** Segment mix, the largest customers or products and their share,
   and joint ventures or acquisitions in progress.
5. **Shareholding.** The digest's `Exchange filings` section has the latest NSE shareholding
   pattern (promoter, FII, DII, mutual funds, pledge) and the promoter trend. Explain any large
   change. If that section is missing, look up the pattern on nseindia.com; the fallback
   holdings field is Yahoo's insider and institution split, not the exchange pattern.
6. **Price move.** If the stock fell or rose more than 15% in three months, find the reason.
7. **Material events in the last 90 days:** orders, capacity, regulatory action, rating
   changes, M&A, block deals, litigation. Also note the sector drivers.
8. **Broker views.** Recent broker ratings and targets with dates, to compare with the model.

If anything you find contradicts a digest figure (for example a reported growth rate or profit
that differs materially), add it to `data_conflicts`. That also makes the rating provisional.

Keep each source's title, URL and date. Prefer exchange filings (nseindia.com, bseindia.com),
company investor pages and established financial media. Skip this step only if no search tool
is available, and say so in the summary; then the freshness check stays unresolved and must be
stated in the reply.

### Step 4. Write the analyst commentary file

Write a JSON file next to the analysis (for example `<SYMBOL>_commentary.json`). Read
`references/commentary-guide.md` for the schema, rules and a worked example. The short rules:

- Every number in the commentary must appear in the digest or in a cited source.
- Do not change the target price or any computed number. You cannot raise the rating. The only
  way research affects the rating is through `newer_results` and `data_conflicts`, which make it
  provisional (never BUY). If you disagree with the model in any other way, say why in `risks`
  or `summary` and label it as the analyst view.
- Plain, precise English. No hype words. Indian units (Rs, crore, lakh) and fiscal years
  (FY26, Q1FY27).

### Step 5. Re-render the report with the commentary

```bash
"$PY" "$SKILL_DIR/scripts/analyse.py" --render "<path>/<SYMBOL>_<YYYYMMDD>_analysis.json" --commentary "<path>/<SYMBOL>_commentary.json"
```

This does not download data again and does not change any number. It rewrites the HTML and
PDF with the commentary sections labelled "Analyst view", and re-applies the rating gates (the
printed digest shows the final rating; use that one in the reply).

### Step 6. Reply in chat

Use this structure (tables, not long paragraphs):

1. **Rating line**: `RATING | Target Rs X | CMP Rs Y | Upside Z% | Conviction | Score N/100`.
   Add `PROVISIONAL` and the reasons on the next line when the rating is provisional.
2. **Why** (3 to 5 bullets): the strongest data-backed reasons, each with its number.
3. **Risks** (3 to 5 bullets): from the concerns, the data warnings and your research.
4. **Valuation table**: method, value, weight, any cap applied, and the bear, base and bull
   scenario values. Compare the target with the consensus range.
5. **Key levels**: support, resistance, 52-week range.
6. **What would change the view**: two or three measurable triggers (for example "a quarter
   with EBITDA margin below 12%" or "price closing below the Rs 160 support").
7. **Files**: links to the HTML, PDF and JSON.
8. **Disclaimer** (one line): educational output, not investment advice, the author is not a
   SEBI-registered Research Analyst or Investment Adviser.

## How the rating works (so you can explain it)

| Step | Rule |
|---|---|
| Earnings basis | EBITDA excludes other income. Profit and EPS exclude estimated one-offs (unusual items and other-income spikes). Quarters are compared by date; trailing EPS needs four consecutive quarters, else the latest full year. |
| Target price | Blend of relative multiple (40%), DCF or justified P/B (30%) and street consensus (30%). Methods outside 0.4x to 2.5x of CMP are excluded; weights renormalise. The target multiple is capped at 1.25x the current multiple, and the target at 1.15x the highest analyst target. |
| Base rating | BUY if upside is 15% or more; HOLD from -5% to below 15%; SELL below -5%. |
| Quality gate | BUY with composite score below 50 becomes HOLD. |
| Weak-stock gate | HOLD with score below 35 and upside below 5% becomes SELL. |
| Provisional gate | Only one valuation method, a failed critical download, overdue results, results filed with the exchange (or considered at a results board meeting) but not in the data, or newer results or a data conflict found in research: the rating is provisional, cannot be BUY and has Low conviction. |
| Conviction | High, Medium or Low from the score and the spread between valuation methods; Low when an excluded method points the other way. |

The six scorecard pillars are Quality 25%, Growth 20%, Valuation 20%, Technical trend 15%,
Relative strength vs Nifty 50 10% and Risk 10%. The Valuation pillar does not score upside to
the model's own target. Full formulas and thresholds: `references/methodology.md`.

## Guardrails

- This is educational analysis. Always include the disclaimer. Never describe it as
  personalised advice or tell the user how much to invest.
- Never place, modify or suggest placing orders, even if a broker connector (for example Kite)
  is available in the session.
- Do not invent numbers. If a figure is missing in the digest, write "not available".
- If the user asks about a non-Indian stock, say that this skill covers NSE and BSE only.
- Mutual funds, ETFs, indices and unlisted companies are out of scope.

## Troubleshooting

| Symptom | Action |
|---|---|
| `ModuleNotFoundError` | Run `bash "$SKILL_DIR/scripts/setup_env.sh"`. |
| Network or DNS errors | The environment cannot reach Yahoo Finance. Tell the user. On claude.ai, network access for code execution may need to be enabled in settings; Claude Code on the desktop works out of the box. Do not produce a report from memory. |
| "Exchange data: ... not available (HTTP 403)" | NSE or BSE blocked the request. The report is complete on Yahoo data; freshness then relies on Step 3 item 1. On claude.ai, nseindia.com, nsearchives.nseindia.com, bseindia.com and api.bseindia.com must be allowed for code execution. |
| `PDF not produced` warning | No Chrome, Edge or Chromium found. The HTML report is complete; the user can print it to PDF. |
| A method shows "Excluded as an outlier" | Expected for some stocks (for example DCF for capex-heavy companies). Explain it in the reply, including any conflict note. |
| "Company profile: not available" or "Peer data download failed" | Re-run once. If it persists, the rating is provisional or the peer cross-check is missing; say so. |
| Peer table missing | The stock is not in a curated peer group; the relative multiple then uses only its own history. |

## Files in this skill

| Path | Purpose |
|---|---|
| `scripts/analyse.py` | Command-line entry point |
| `scripts/bsa/` | Engine: data, exchange, indicators, fundamentals, valuation, scoring, narrative, charts, report |
| `scripts/requirements.txt`, `scripts/setup_env.sh` | Dependencies and one-time setup |
| `references/methodology.md` | Formulas, thresholds, assumptions and known limitations |
| `references/commentary-guide.md` | Commentary JSON schema, writing rules and an example |
