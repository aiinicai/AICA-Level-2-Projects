# Akshar: Bharat Stock Analyser (Claude Skill for Indian equity research)

## Purpose

A Claude Skill that produces a data-backed BUY, HOLD or SELL research note for any NSE or BSE
listed stock. The user names a company; the skill computes every figure in code, applies
published rating rules, has Claude add researched context, and delivers an HTML and PDF report
in the style of an Indian broker research note.

## Main features

- **Name to report in one request**: accepts company names, NSE symbols, Yahoo tickers and BSE codes.
- **Three-method target price**: relative P/E or P/B, FCF DCF or justified P/B for lenders, and
  street consensus, with outlier exclusion and weight renormalisation.
- **Six-pillar scorecard (24 metrics)**: quality, growth, valuation, technical trend, relative
  strength against the Nifty 50, and risk.
- **Transparent rating**: BUY 15%+ upside, HOLD -5% to 15%, SELL below -5%, plus quality and
  weak-stock gates. The rule chain is printed in every report.
- **Self-checking model (v1.1)**: a provisional gate blocks BUY when only one valuation method
  works, a download fails, or newer quarterly results exist (SEBI LODR deadline check plus a
  mandatory filing search). Quarters are matched by date, one-off gains are removed, the target
  multiple and the target itself are capped, and bear, base and bull scenarios are shown. These
  controls came from an independent review of an earlier Dixon Technologies report; the review
  findings and fixes are tabulated in the README.
- **Exchange filings layer (v1.2)**: the latest quarterly results are read from the company's
  own NSE XBRL filings (consolidated where filed), replacing Yahoo's figures for those quarters
  and listing any disagreement. Results board meeting dates confirm freshness automatically
  (rescheduled meetings are recognised), and the NSE shareholding pattern gives promoter, FII,
  DII and pledge data. The layer is optional and read-only; if NSE or BSE cannot be reached the
  report runs on Yahoo and says so.
- **Research note with 20+ exhibits**: key stock data, price performance against the Nifty and
  the sector index, quarterly snapshot (QoQ and YoY), P&L, balance sheet, cash flow, ratios,
  valuation football field, P/E history, cost of capital, scorecard, technical dashboard (RSI,
  MACD, support and resistance), peer table, news and sources, methodology, disclaimer.
- **Built for India**: Rs crore, Indian digit grouping, FY and quarter labels, NSE peer groups
  and sectoral indices, section 115BAA tax rate.
- **Guardrails against invented numbers**: Claude's commentary may cite only computed figures
  or dated sources, cannot change the rating, and is labelled "Analyst view". Source data
  inconsistencies are flagged in the report.
- **Audit trail**: every run writes a JSON file with all inputs and outputs.

## Setup and usage

```bash
cp -R bharat-stock-analyser ~/.claude/skills/
bash ~/.claude/skills/bharat-stock-analyser/scripts/setup_env.sh
```

Then ask Claude: "Analyse Tata Steel and give me a buy, hold or sell view."

Without Claude: `.venv/bin/python scripts/analyse.py "hdfc bank"`.

For claude.ai, upload `bharat-stock-analyser.zip` under Settings, Capabilities, Skills (code
execution needs internet access to Yahoo Finance and, for the exchange layer, the NSE and BSE
domains).

Tests: `python -m pytest -q` (84 offline tests).

Sample reports for Dixon Technologies, Tata Steel, HDFC Bank and Infosys are in `examples/`.

## Limitations

Annual statements, consensus and peer data come from Yahoo Finance, which is unofficial and
occasionally inconsistent; the tool flags the gaps it detects. The NSE and BSE endpoints are
website pages, not documented APIs, and can change or block automated access. Bank
asset-quality metrics and sum-of-the-parts valuation are not covered by the model. Output is educational and not investment advice; the
author is not a SEBI-registered Research Analyst or Investment Adviser.

## Originality

Original code. The architecture idea came from reviewing the MIT-licensed
`daily_stock_analysis` project; no code was copied.
