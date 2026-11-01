# Bharat Stock Analyser (Claude Skill)

A Claude Skill that turns an Indian stock name into a data-backed equity research note with a
**BUY, HOLD or SELL** rating, a 12-month target price and the evidence behind both.

Ask Claude "analyse Tata Steel" or "is HDFC Bank a buy?" and the skill:

1. Resolves the name to an NSE or BSE listing.
2. Downloads five years of prices, four to five years of financial statements, analyst
   consensus and peer data (Yahoo Finance), and the latest quarterly results, results board
   meeting dates and shareholding pattern from the company's NSE filings.
3. Computes 40+ ratios and indicators, a three-method target price and a six-pillar scorecard.
4. Applies published rating rules (BUY 15%+ upside, HOLD -5% to 15%, SELL below -5%, with
   quality gates).
5. Has Claude research the latest results and news, then adds that context as a clearly
   labelled "Analyst view".
6. Produces a broker-style HTML and PDF research note with 20+ exhibits and a chat summary.

The report format follows Indian broker research notes (the IDBI Capital Tata Steel Q2FY23
result review was the reference): rating box, target price, key stock data, price performance
against the index, shareholding, quarterly snapshot, financial summary, ratios, valuation,
rating key and disclaimer.

## Why this project

| Problem | What the skill does |
|---|---|
| Free stock tips in India rarely show their working | Every number is computed by code and traceable in a JSON audit file |
| LLM answers about stocks can invent figures | The engine computes all figures; Claude may only cite them or a dated source, and cannot change the rating |
| Global tools ignore Indian conventions | Rs crore and lakh, Indian digit grouping (2,41,636), FY and Q1FY27 labels, Nifty 50 and sectoral indices, NSE peer groups, section 115BAA tax rate in WACC |
| Ratings feel arbitrary | The rule chain is printed in every report ("Upside 26.2% gives BUY; score 44 is below 50, so HOLD") |

## Example output

Sample reports generated on 1 November 2026 (prices as of 30 October 2026) are in
[`examples/`](examples/):

| Stock | Rating | CMP | Target | Upside | Score | Notes |
|---|---|---|---|---|---|---|
| Dixon Technologies | BUY (Low conviction) | Rs 11,000 | Rs 17,376 | +58.0% | 65 | Q2FY27 (filed 30-Oct-2026) taken from the NSE filing; profit excluding one-offs fell 3.7% YoY; DCF conflict and a re-rating to 69.9x keep conviction Low |
| Tata Steel | BUY (Low conviction) | Rs 167.6 | Rs 217.1 | +29.5% | 50 | NSE confirms Q2FY27 is not yet published (meeting moved from 27-Oct to 7-Nov-2026); DCF conflict keeps conviction Low |
| HDFC Bank | BUY (Low conviction) | Rs 692.8 | Rs 832.9 | +20.2% | 55 | Yahoo stopped at Q1FY26; six quarters to Q2FY27 now come from NSE filings; justified P/B conflict keeps conviction Low |
| Infosys | HOLD | Rs 1,185 | Rs 1,334 | +12.6% | 70 | Quarterly figures from NSE filings in rupees (Yahoo reports in USD) |

Version 1.1 rated Dixon and HDFC Bank as provisional HOLD because their latest results were
missing from Yahoo. With the exchange layer (version 1.2) those quarters are in the model, so
the provisional gate no longer applies and the model's own BUY stands, with Low conviction.

Each example has `_report.html`, `_report.pdf`, `_analysis.json` and the Markdown digest
that Claude reads. Dixon and Tata Steel also have the commentary JSON and the digest after
re-rendering with it.

## Model review and version 1.1 changes

An independent review of an earlier Dixon Technologies report (BUY, target Rs 20,790, +89%)
found that the conclusion was not supported. Each finding was checked against the data and
the code. The confirmed causes and the fixes:

| Finding | Root cause | Fix in v1.1 | Severity |
|---|---|---|---|
| Target rested on one method; consensus "unavailable" | The run was on claude.ai, where the profile download failed; the model treated a failed download as "no analysts" | Retries; failed downloads recorded; provisional gate (no BUY) when the profile fails or only one method is usable | High |
| Q1FY27 "YoY" compared with Q4FY25 | The source skipped Q2FY26 and the code took "five rows back" | Quarters matched by date; missing quarters named | High |
| Trailing EPS included a skipped quarter and a one-off gain | Last four rows summed without checking dates | Four consecutive quarters required; one-offs removed | High |
| Q2FY27 results missed | No freshness control | SEBI LODR deadline check; mandatory filing search; `newer_results` makes the rating provisional | High |
| Historical P/E of 70.6x assumed | No limit on re-rating | Target multiple capped at 1.25x current; target capped at 1.15x the highest analyst target | High |
| Valuation score of 100 was circular | Upside to the model's own target was a scored metric | Removed; FCF yield added; PEG on forward growth | Medium |
| EBITDA included a Rs 528 crore other-income gain | Source EBITDA includes other income | EBITDA excludes other income and unusual items; reported and adjusted profit both shown | Medium |
| DCF dropped silently | Outlier exclusion had no diagnostic | Explanation printed; a conflicting excluded method sets conviction to Low | Medium |
| Wrong peers | Dixon was grouped with paints and durables | New Electronics Manufacturing Services peer group | Medium |
| Customer concentration, incentive receivables, shareholding pattern | Not in the data source | Required items in Claude's research checklist (SKILL.md Step 3) | Medium |

One review point was not adopted: explicit FY27 to FY29 earnings forecasts. The model uses
consensus forward EPS where available, and building a forecast model was out of scope.

## Version 1.2: exchange filings layer

Yahoo Finance missed or lagged quarters in the v1.1 examples (Dixon skipped Q2FY26 and did not
yet carry Q2FY27; HDFC Bank stopped at Q1FY26). Version 1.2 reads the company's own filings
from NSE:

| What | NSE source | Effect |
|---|---|---|
| Quarterly results | SEBI integrated filing XBRL (consolidated where filed), latest 6 quarters | Replace Yahoo's figures for the same quarters; Yahoo is compared with the filing and differences above 2% (revenue) or 5% (profit) are listed |
| Results board meetings | Board meeting list | Results filed or a results meeting held for a quarter not in the data make the rating provisional; otherwise freshness is confirmed without a web search. Rescheduled meetings are recognised |
| Shareholding pattern | Shareholding pattern XBRL | Promoter, FII, DII, mutual funds, public, promoter pledge and the promoter trend, in the report and the narrative |

BSE is used for the BSE code and as a fallback for the latest results date. The layer is
optional and read-only: these are the exchanges' website endpoints, not documented APIs, so a
blocked or changed endpoint becomes a data note and the report runs on Yahoo alone. On claude.ai
the domains `www.nseindia.com`, `nsearchives.nseindia.com`, `www.bseindia.com` and
`api.bseindia.com` must be allowed for code execution. `--no-exchange` switches the layer off.

Analyst consensus, annual statements, five-year prices and peer multiples still come from
Yahoo, because the exchanges do not publish them in a usable form.

These are outputs of an automated model for demonstration. They are not recommendations.

## Install

### Claude Code (desktop app or terminal), recommended

```bash
cp -R bharat-stock-analyser ~/.claude/skills/
bash ~/.claude/skills/bharat-stock-analyser/scripts/setup_env.sh
```

Restart Claude Code, then ask: `Analyse Tata Steel and give me a buy, hold or sell view.`

### Claude.ai (web or desktop chat)

1. Zip the `bharat-stock-analyser` folder (the zip must contain the folder, with `SKILL.md`
   inside it), or use the prepared `bharat-stock-analyser.zip`.
2. In Claude, open Settings, then Capabilities, and upload the zip under Skills.
3. Code execution must be allowed to reach Yahoo Finance and, for the exchange layer,
   `www.nseindia.com`, `nsearchives.nseindia.com`, `www.bseindia.com` and `api.bseindia.com`.
   If your plan or organisation blocks network access from code execution, use Claude Code
   instead.

### Run without Claude

```bash
cd bharat-stock-analyser
bash scripts/setup_env.sh
.venv/bin/python scripts/analyse.py "tata steel" --outdir ./reports
```

Requirements: Python 3.10 or later, internet access, and optionally Google Chrome, Microsoft
Edge or Chromium for PDF output.

## How it works

```
User: "Analyse Tata Steel"
        |
        v
SKILL.md  ->  Claude runs scripts/analyse.py "tata steel"
                 |
                 |  data.py         resolve name -> TATASTEEL.NS; fetch prices, statements, consensus, peers
                 |  exchange.py     NSE filings: quarterly results XBRL, results meetings, shareholding pattern
                 |  fundamentals.py annual and quarterly tables, ROE, ROCE, cash conversion, FY-end P/E bands
                 |  indicators.py   SMA, RSI, MACD, Bollinger, ATR, beta, drawdown, support and resistance
                 |  valuation.py    relative P/E or P/B + DCF or justified P/B + consensus -> blended target
                 |  scoring.py      six-pillar scorecard -> rating rules -> BUY / HOLD / SELL + conviction
                 |  narrative.py    rule-based positives and concerns, each citing a number
                 |  charts.py       9 exhibits (matplotlib)
                 |  report.py       HTML research note -> PDF via headless Chrome
                 v
        Markdown digest printed for Claude
                 |
Claude researches latest results and news (web search), writes commentary JSON
                 |
        analyse.py --render ... --commentary ...   (no new download; numbers unchanged)
                 |
                 v
Chat summary + HTML + PDF + JSON audit file
```

### Target price

| Method | Weight | Non-financial companies | Banks and NBFCs |
|---|---|---|---|
| Relative multiple | 40% | Forward EPS x median of own FY-end P/E and peer P/E, capped at 1.25x current P/E | Forward book value x median of own and peer P/B, same cap |
| Intrinsic | 30% | 10-year two-stage FCF DCF at WACC | Justified P/B = (ROE - g) / (CoE - g) |
| Street consensus | 30% | Mean analyst target (3+ analysts) | Same |

Methods outside 0.4x to 2.5x of the current price are excluded and shown as excluded. The
blended target is capped at 1.15x the highest analyst target. Earnings exclude estimated
one-offs, and bear, base and bull scenarios are shown.

### Scorecard

Quality 25%, Growth 20%, Valuation 20%, Technical trend 15%, Relative strength vs Nifty 50
10%, Risk 10%. Each of 24 metrics is scored 0 to 100 against published thresholds. Upside to
the model's own target is not scored.

### Rating

| Rule | Condition |
|---|---|
| BUY | Upside of 15% or more, composite score of 50 or more, and not provisional |
| HOLD | Upside from -5% to below 15%, or a BUY cut by the quality gate or the provisional gate |
| SELL | Upside below -5%, or score below 35 with upside below 5% |
| Provisional | Only one valuation method, a failed critical download, overdue quarterly results, or newer results or a data conflict found in research. Never BUY; conviction Low |

Full formulas: [`bharat-stock-analyser/references/methodology.md`](bharat-stock-analyser/references/methodology.md).

## Verification

```bash
.venv/bin/python -m pytest -q
```

84 offline tests cover Indian number formatting, fiscal labels, every indicator (including
hand-checked RSI extremes, drawdown and beta), ratio formulas against a synthetic company with
hand-calculated values, the DCF against the Gordon growth closed form, outlier exclusion,
weight renormalisation, every branch of the rating rules, commentary validation and a full
offline pipeline run that renders HTML. `tests/test_model_controls.py` adds 23 tests for the
v1.1 controls, using the actual Dixon quarterly figures: date-matched YoY, the trailing EPS
rule, one-off removal, SEBI deadlines (including the 60-day March quarter), the provisional
gate, both caps, scenarios, the non-circular scorecard and commentary-driven provisional
ratings. `tests/test_exchange.py` adds 16 tests for the exchange layer, with synthetic XBRL in
the SEBI layout carrying Dixon's Q2FY27 figures: quarter versus half-year and segment contexts,
exceptional items, bank mapping, shareholding and pledge, rescheduled meetings, consolidated
and revised filing selection, the merge with Yahoo, every freshness outcome, the fail-safe when
the exchanges block requests, and a full pipeline run.

Live runs were checked on Dixon Technologies, Tata Steel, HDFC Bank and Infosys. Filing figures
were compared with Yahoo: Dixon and Tata Steel matched (revenue within 0.6%, profit to owners
exact). The Dixon report was inspected visually.

## Limitations (stated openly)

| Limitation | Severity |
|---|---|
| Annual statements, consensus and peer data still come from Yahoo Finance, an unofficial source that can lag or disagree internally (the tool flags gaps it can detect) | High |
| The NSE and BSE endpoints are website pages, not documented APIs; they can change or block automated access, and their terms of use restrict it. The layer is optional and falls back to Yahoo | High |
| Filed quarters and Yahoo's annual figures can classify one-offs differently (Dixon FY26 is an example) | Medium |
| One-off removal is an estimate from line items and can differ from the company's adjusted figures | Medium |
| On claude.ai, restricted network access can make downloads fail (the rating is then provisional) and the exchange domains must be allowed. Claude Code is more reliable | Medium |
| Bank metrics such as NIM, GNPA, CASA and capital adequacy are not used by the model; Claude adds them from results releases | Medium |
| No sum-of-the-parts valuation for conglomerates and holding companies | Medium |
| Peer groups are curated for 137 large NSE stocks in 21 groups; others fall back to the Yahoo industry or have no peers | Low |
| End-of-day data; not for intraday trading | Low |

## Disclaimer

Educational capstone project. The author is not registered with SEBI as a Research Analyst or
Investment Adviser. Output is not investment advice, not a research report under the SEBI
(Research Analysts) Regulations, 2014, and not an offer or solicitation. Equity investing
involves risk, including loss of capital.

## Acknowledgements

The architecture idea (data, analysis, report) came from reviewing the MIT-licensed
`daily_stock_analysis` project by ZhuLinsen. No code was copied: that project targets Chinese,
Hong Kong and US markets and has no India support. Market data: Yahoo Finance via the
open-source `yfinance` library; company filings: National Stock Exchange of India and BSE
public filing pages, read-only. Report structure reference: IDBI Capital retail research note
on Tata Steel (Q2FY23), used for layout conventions only.

## Project layout

```
Akshar-Bharat-Stock-Analyser-Skill/
  README.md                       this file
  LICENSE                         MIT
  PR_DESCRIPTION.md               pull request text for submission
  bharat-stock-analyser/          THE SKILL (copy this folder to install)
    SKILL.md                      instructions Claude follows
    references/methodology.md     formulas, thresholds, limitations
    references/commentary-guide.md  analyst commentary schema and rules
    scripts/analyse.py            command-line entry point
    scripts/bsa/                  engine (12 modules)
    scripts/requirements.txt
    scripts/setup_env.sh
  bharat-stock-analyser.zip       upload-ready package for claude.ai
  examples/                       sample reports, digests and commentary
  docs/                           project presentation (PowerPoint, with speaker notes)
  tests/                          84 offline tests
```
