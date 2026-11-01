# Methodology

All figures are computed by `scripts/bsa/`. This file documents every formula, threshold and
assumption so that a reviewer can reproduce any number in a report.

## 1. Data

| Item | Source | Notes |
|---|---|---|
| Daily prices (5 years) | Yahoo Finance via `yfinance` | Close is split and bonus adjusted; Adj Close is also dividend adjusted |
| Annual statements | Yahoo Finance | Usually consolidated. Up to 5 fiscal years |
| Quarterly results | NSE results filings (XBRL), Yahoo Finance for older quarters | Consolidated where the company files it. The latest 6 filed quarters replace Yahoo's figures for the same quarters; the latest 5 quarters are used |
| Results board meetings | NSE board meeting list; BSE results announcements as fallback | Last held and next scheduled results meeting |
| Shareholding pattern | NSE shareholding pattern (XBRL) | Promoter, FII, DII, mutual funds, public; promoter pledge as a share of promoter holding; promoter trend over 5 quarters. Yahoo's insider and institution split is the fallback |
| Consensus targets, analyst count | Yahoo Finance | |
| Benchmark | Nifty 50 (`^NSEI`); Sensex level shown for reference | |
| Sector index | Mapped from the curated peer group, for example Nifty Metal (`^CNXMETAL`) | |
| Peers | Curated NSE groups in `bsa/peers.py`, fallback by Yahoo industry | Peers with no data are dropped |

Statements reported in a foreign currency (for example USD for some dual-listed IT companies)
are converted to INR at the latest exchange rate. Ratios are unaffected; rupee CAGRs then
reflect growth in the reporting currency. The report states when this happens.

### Exchange filings (v1.2)

The exchange layer (`bsa/exchange.py`) reads public NSE pages that the NSE website itself
uses: the board meeting list, the SEBI integrated filing list (financial results from the
December 2024 quarter onwards, with an XBRL file per filing) and the shareholding pattern list.
These are website endpoints, not documented APIs, so they need a browser-like session
(`curl_cffi`) and can change or be blocked. Every call is retried once and wrapped; a failure
becomes a data note and the report continues on Yahoo data. BSE is used only to find the BSE
code and, if NSE gives nothing, the date of the latest results announcement. Set
`BSA_NO_EXCHANGE=1` or pass `--no-exchange` to switch the layer off.

| Filing field (XBRL element) | Model field |
|---|---|
| RevenueFromOperations (banks: Income, total income) | Revenue |
| InterestEarned less InterestExpended (banks) | Net interest income |
| OtherIncome (not for banks, where fee income is core) | Other income |
| ProfitBeforeTax less ProfitBeforeExceptionalItemsAndTax (or ExceptionalItems) | Unusual items |
| ProfitBeforeTax + FinanceCosts + Depreciation | Source EBITDA (then less other income and unusual items) |
| ProfitOrLossAttributableToOwnersOfParent | Net profit to owners |
| ProfitLossForPeriod | Net profit including minority interest |

The quarter is the context of about three months (80 to 100 days) that ends on the reporting
period end date and carries no dimension, so half-year, segment and balance-sheet values are
never mixed in. Where Yahoo also has the quarter, the two are compared: a revenue difference
above 2% or a profit difference above 5% (and at least Rs 1 crore) is written to the data
notes. The comparison is skipped when Yahoo reports in another currency, because converting at
today's rate creates differences that are only exchange rate moves.

### Per-share figures

EPS, DPS and book value per share are computed as the statement figure divided by the
**current** share count. Yahoo price history is adjusted for splits and bonus issues, so this
keeps historical P/E and P/B comparable. Shares issued for cash in past years introduce a small
error, which is accepted.

### Consistency checks

The pipeline compares (a) statement-derived book value per share with the source's reported
book value and (b) calculated ROE with the source's trailing ROE. Gaps above 15 percent and 3
percentage points respectively are written to the report's data notes.

### Download failures

The company profile and the four statements are retried up to three times (waits of 2 and 4
seconds). A download that still fails is recorded as failed, not as "no data". A failed
company profile or income statement makes the rating provisional (section 6), because the
consensus, market data and earnings would otherwise be silently missing. Peer downloads that
fail are reported in the data notes.

### Earnings basis and one-off items

| Item | Definition |
|---|---|
| EBITDA | Operating EBITDA: the source's EBITDA (which equals PBT + interest + depreciation, and so includes other income) less other income and unusual items |
| Net profit | Profit attributable to owners, after minority interest. Profit including minority interest is shown separately |
| One-off items (pre-tax) | The source's unusual items, plus any spike in other income: other income above 3x the median of the other periods in the same table, where the excess over that median is at least 10% of PBT. If both are flagged in one period, the larger is used, to avoid counting one item twice |
| Profit excluding one-offs | Net profit less one-off items x (1 - effective tax rate of the period, bounded to 0% and 35%) |

Profit and EPS excluding one-offs are used for FY-end P/E history, EPS and PAT CAGRs, the
quarterly PAT growth score and trailing EPS. This is an estimate: company-defined adjusted
figures can differ, and Claude is instructed to compare them.

### Quarterly comparisons and trailing EPS

- QoQ and YoY comparisons match quarters by period end date (within 20 days), not by position.
  When the source skips a quarter, the comparison shows "not available" and the report names
  the missing quarter.
- Trailing EPS = profit excluding one-offs over four consecutive quarters (each gap 80 to 100
  days) / current shares. Without four consecutive quarters, the latest full fiscal year's EPS
  excluding one-offs is used, and the basis is printed.

### Results freshness

The latest period covered is the later of the last quarter and the last fiscal year end. Every
quarter that ended after it and before the report date is listed with its SEBI LODR deadline
(Regulation 33: 45 days after quarter end; 60 days for the March quarter). A quarter past its
deadline makes the rating provisional.

When the exchange layer answered:

- Results filed with NSE for a quarter later than the data, or a results board meeting already
  held for such a quarter with no filing yet, make the rating provisional.
- A results meeting is matched to the latest quarter end before the meeting date. A meeting
  followed by a later scheduled meeting for the same quarter is treated as rescheduled (for
  example Tata Steel, 27 October 2026 moved to 7 November 2026).
- Otherwise a quarter within its deadline is confirmed as not yet published, the digest shows
  "Results freshness: confirmed with NSE" with the next meeting date, and no web search is
  needed for freshness.

When the exchange layer did not answer, a quarter within its deadline triggers a mandatory
search of the exchange filings in Claude's research step; if the results are published, the
commentary records them in `newer_results` and the rating becomes provisional.

### Ownership points in the narrative

From the exchange shareholding pattern: promoter holding of 50% or more is a positive and below
15% a concern (not for lenders); a change of 2 percentage points or more over the five
reported quarters is a positive (buying) or a concern (selling); any promoter pledge of 1% or
more of the promoter holding is a concern; FII plus DII holding of 40% or more is a positive.
Ownership does not enter the scorecard.

## 2. Financial ratios

| Ratio | Formula |
|---|---|
| ROE | Net profit / average shareholders' equity (current and previous year) |
| ROCE | EBIT / (total assets - current liabilities) |
| ROA | Net profit / average total assets |
| Net debt to equity | (total debt - cash and equivalents) / equity |
| Interest cover | EBIT / interest expense |
| Cash conversion | Cash flow from operations / net profit (3-year average in the scorecard) |
| Free cash flow | Operating cash flow - capital expenditure (source FCF where available) |
| Working capital days | Inventory and payables on cost of revenue, receivables on revenue, times 365 |
| FY-end P/E, P/B | Close on the fiscal year-end date / EPS excluding one-offs or book value per share of that year |
| CAGR | (last / first) ^ (1 / years) - 1, up to 3 years; not computed if either end is not positive |

Lenders (sector "Financial Services", or no EBITDA line with a net interest income line) use a
separate ratio set: ROE, ROA, net margin, leverage, P/B.

## 3. Technical indicators

| Indicator | Definition |
|---|---|
| SMA 20, 50, 200 | Simple moving averages of close |
| RSI (14) | Wilder smoothing (alpha = 1/14) of gains and losses |
| MACD | EMA 12 - EMA 26; signal = EMA 9 of MACD; histogram = MACD - signal |
| Bollinger bands | SMA 20 plus and minus 2 population standard deviations |
| ATR (14) | Wilder smoothing of true range |
| Volatility | Standard deviation of daily returns over 252 sessions x sqrt(252) |
| Maximum drawdown | Largest fall from a running peak over 252 sessions |
| Beta | Covariance of daily returns with the Nifty 50 / variance of Nifty 50 returns, 252 sessions |
| Support and resistance | Swing lows and highs (lowest or highest bar within 5 sessions each side) over 180 sessions; levels within 1.5 percent are merged; nearest two each side |
| Golden or death cross | 50-day average crossing the 200-day average in the last 60 sessions |

## 4. Valuation

### Cost of capital

| Assumption | Default | Override |
|---|---|---|
| Risk-free rate (India 10-year G-Sec, approximate) | 6.5% | `--rf` |
| Equity risk premium (India) | 7.0% | `--erp` |
| Beta | Blume adjusted: 0.67 x raw 1-year beta + 0.33, bounded to 0.7 and 1.5 | |
| Pre-tax cost of debt | 9.0% | |
| Tax rate | 25.17% (section 115BAA rate including surcharge and cess) | |
| WACC | Market-value weights of equity and total debt, floor 10% | |
| Terminal growth | 5.0% | `--tg` |

Cost of equity = risk-free rate + beta x equity risk premium.

### Method A: relative multiple (weight 40%)

Non-financial companies:

- Trailing EPS: excluding one-offs, as defined in section 1. The source's own trailing EPS is
  used only when neither four consecutive quarters nor a full year is available.
- Forward EPS: consensus forward EPS if it is between 0.5x and 1.4x trailing EPS. If consensus
  expects more than 1.4x, forward EPS is capped at 1.4x trailing, because applying a historical
  P/E to recovery earnings double counts the recovery. Without consensus, trailing EPS grows at
  the 3-year EPS CAGR bounded to -10% and +20%.
- Target P/E: median of (own FY-end P/E median, peer median P/E), bounded to 5x and 80x. P/E
  values above 150x are ignored as not meaningful. The target P/E is then capped at 1.25x the
  current P/E: the model does not assume a re-rating of more than 25% within 12 months.
- Value = forward EPS x target P/E.

Lenders: forward book value per share = book value x (1 + ROE x (1 - payout)); target P/B =
median of (own FY-end P/B median, peer median P/B), bounded to 0.5x and 15x, with the same
1.25x cap on the current P/B.

Scenarios (shown, not blended):

| Case | Forward EPS (lenders: forward book value) | Multiple |
|---|---|---|
| Bear | Base less 15% | 0.8x the lower of current and target multiple |
| Base | As used in method A | Target multiple |
| Bull | Base plus 10% | 1.15x the target multiple |

### Method B: intrinsic value (weight 30%)

Non-financial: two-stage free cash flow DCF.

- Base FCF = average FCF of the last three years. Not computed if this is not positive.
- Growth: revenue CAGR bounded to 3% and 15% for years 1 to 5, fading linearly to terminal
  growth by year 10.
- Terminal value = FCF year 10 x (1 + g) / (WACC - g).
- Equity value = enterprise value - net debt. Fair value per share = equity value / shares.
- 12-month value = fair value x (1 + cost of equity - dividend yield).

Lenders: justified P/B = (ROE - g) / (cost of equity - g), with ROE the 3-year average and
g = ROE x (1 - payout) bounded to 0% and the lower of 10% and (cost of equity - 1%).
Value = justified P/B x forward book value per share.

### Method C: street consensus (weight 30%)

Mean analyst target price, used only when at least three analysts cover the stock.

### Blend

A method whose value is below 0.4x or above 2.5x the current price is excluded as an outlier
and shown as excluded. Weights of the remaining methods are rescaled to 100%.
Dispersion = (highest - lowest included value) / blended target.

When the DCF is excluded and free cash flow was below 0.5x of net profit over the base years,
the report explains that historical cash flow understates value during growth capex, and that
the gap is still a warning. An excluded method that lies on the other side of the current
price from the target (below 0.8x CMP for a target above CMP, or above 1.2x CMP for a target
below CMP) is listed as a conflict and sets conviction to Low.

Consensus cap: when at least three analysts cover the stock, the blended target is capped at
1.15x the highest analyst target. The uncapped value is shown.

## 5. Scorecard

Each metric is scored on a straight line between a weak value (score 0) and a strong value
(score 100), clipped at both ends. A pillar is the average of its available metrics. The
composite is the weighted average of available pillars, with weights rescaled if a pillar has
no data.

| Pillar (weight) | Metric | Score 0 at | Score 100 at |
|---|---|---|---|
| Quality (25%) | ROE (non-financial) | 5% | 22% |
| | ROCE | 6% | 25% |
| | Net debt to equity | 1.5x | 0x |
| | Interest cover | 1.5x | 10x |
| | CFO to PAT, 3-year average | 0.5x | 1.1x |
| | ROE (lenders) | 8% | 18% |
| | ROA (lenders) | 0.5% | 2.0% |
| | Book value CAGR (lenders) | 5% | 18% |
| Growth (20%) | Revenue CAGR | 0% | 15% |
| | EPS CAGR excluding one-offs | -5% | 20% |
| | Latest quarter revenue YoY (date-matched) | -5% | 20% |
| | Latest quarter PAT YoY excluding one-offs (date-matched) | -10% | 25% |
| Valuation (20%) | P/E (lenders P/B) vs own FY-end median | 1.4x | 0.8x |
| | P/E (lenders P/B) vs peer median | 1.5x | 0.8x |
| | PEG on forward EPS growth (non-financial) | 3.0 | 1.0 |
| | Free cash flow yield, last FY (non-financial) | 0% | 5% |

Upside to the model's own target is deliberately not scored. Scoring it would let the target
raise the score that the quality gate then uses to confirm the target.
| Technical trend (15%) | Price vs 200-DMA | -15% | +10% |
| | Price vs 50-DMA | -10% | +8% |
| | 50-DMA vs 200-DMA | -8% | +5% |
| | RSI (14) | 100 between 45 and 65; 0 at 25 or below and at 80 or above | |
| | MACD histogram | 25 if negative | 75 if positive |
| Relative strength (10%) | 3, 6 and 12-month return minus Nifty 50 return | -15 pts | +15 pts |
| Risk (10%) | Annualised volatility | 50% | 18% |
| | Maximum drawdown (1 year) | -50% | -12% |
| | Beta | 1.6 | 0.7 |

## 6. Rating

| Step | Rule |
|---|---|
| Base | BUY: upside of 15% or more. HOLD: -5% to below 15%. SELL: below -5%. |
| Quality gate | BUY with composite score below 50 becomes HOLD. |
| Weak-stock gate | HOLD with composite score below 35 and upside below 5% becomes SELL. |
| Provisional gate | The rating is provisional when any of these holds: only one valuation method is usable; the company profile, annual income statement or quarterly results download failed; a quarter is past its SEBI LODR results deadline but missing from the data; results were filed with the exchange, or considered at a results board meeting, for a quarter that is not in the data; Claude's research recorded `newer_results` or `data_conflicts`. A provisional BUY is cut to HOLD. HOLD and SELL keep their label but are marked provisional. Conviction is Low. |
| No target | If no method produces a usable value, the rating is HOLD (not rated on valuation), conviction Low. |
| Conviction | Low if provisional, if fewer than two methods are used, if dispersion exceeds 60%, or if an excluded method conflicts (section 4). High if BUY with score of 65 or more (or SELL with score of 40 or less) and dispersion of 35% or less. Otherwise Medium. |

Claude's commentary can only make a rating more cautious (through the provisional gate). It
cannot raise a rating or change any number.

The upside bands follow the rating key used in Indian broker research notes (for example
BUY 15%+, HOLD -5% to 15%, SELL below -5%).

## 7. Known limitations

| Limitation | Severity | Mitigation |
|---|---|---|
| Yahoo Finance data is unofficial, can lag, and is occasionally inconsistent | High | Quarterly figures from NSE filings; Yahoo compared with the filing; consistency checks; date-matched quarters; freshness gate. Annual statements, consensus and peers still come from Yahoo |
| The NSE and BSE endpoints are website pages, not documented APIs; they can change or block automated access, and their terms of use restrict it | High | Optional layer, read-only, a few requests per report; any failure falls back to Yahoo with a data note; `--no-exchange` switch |
| Quarterly results can be published days or weeks before the source carries them | Medium | NSE filings and results meeting dates checked on every run; SEBI LODR deadline check; mandatory filing search when the exchange check fails |
| Filed quarters and Yahoo's annual figures can classify one-offs differently (for example Dixon FY26: Rs 704 crore in Yahoo's annual unusual items against Rs 388 crore identified in the filed quarters) | Medium | Both shown in the digest; Claude explains material gaps |
| Integrated filings start with the December 2024 quarter; older quarters still come from Yahoo | Low | Only the latest 5 quarters are used |
| On claude.ai, the exchange domains must be allowed for code execution | Medium | Without them the report runs on Yahoo alone and says so |
| One-off detection is an estimate from the source's line items, not the company's own adjusted figures | Medium | Shown as "estimated" next to reported figures; Claude compares with the company's adjusted numbers |
| Customer and segment concentration, incentive receivables and notes to accounts are not in the data | Medium | Required items in Claude's research checklist |
| When NSE cannot be reached, holdings fall back to Yahoo's split, which is not the exchange shareholding pattern and has no pledge data | Low | Labelled in the report; Claude is instructed to look up the pattern |
| Statement history is limited to about 4 to 5 years | Medium | CAGRs capped at 3 years |
| Bank-specific metrics (NIM, GNPA, CASA, capital adequacy) are not in the source | Medium | Claude adds them from results releases in the commentary |
| Conglomerates and holding companies are not valued on a sum of the parts | Medium | Stated in the report; analyst commentary can discuss |
| Cyclical companies: historical P/E can mislead at the top or bottom of the cycle | Medium | Forward EPS cap; DCF outlier exclusion; Claude flags cycle position |
| Fixed peer groups can go out of date after demergers and renames | Low | Peers with no data are dropped automatically |
| The model does not include news; Claude's commentary does, but cannot change the numbers | By design | Keeps the rating reproducible |
