# Prompt Log

**Tool:** Google AI Studio (Build mode) with Gemini
**App:** Personal Trades Terminal — Indian Equity Analysis Platform (called ArthaTerminal, then TechnoFundaTrades Terminal, during the build)

The app was built entirely by conversation. I typed what I wanted, Gemini edited the code and rebuilt the app, I checked the result in the preview, and then gave the next instruction. The prompts below are reproduced as I typed them, in order, including my typing mistakes.

Where a prompt says `image.png`, I attached a screenshot. Several times the session stopped with an error and the instruction "There was an unexpected error. Finish what you were doing." was sent to resume; those are noted but not repeated.

## Phase 1: The starting prompt

> I want you to build an investment analysis platform for INDIAN STOCKS (NSE/BSE). It should be able to analyze investments and have a lot of options. You should add those three connectors as well. It should be better than any investment analysis application in the world. It should do technical, fundamental, and the full gamut of analysis. Prices in INR, indices like NIFTY 50 / NIFTY 500 / Sensex as benchmarks, NSE trading calendar and Indian market hours (IST).
>
> EXCLUSIONS
>
> - Do NOT include any Valuation or DCF module (no intrinsic value, fair value, DCF models, or price targets).
>
> 1. 52-WEEK HIGH BREAKOUT SCANNER (variable lookback)
>
> - Detect stocks making a new 52-week high for the first time in N months, where N is user-configurable (e.g., 3, 6, 9, 12, 18, 24 months; free numeric input).
>   - Condition: today's close (or high, user-selectable) > prior 52-week high AND the stock has NOT made a new 52-week high in the last N months.
> - Optional filters: breakout volume ≥ X× 50-day average volume (default 1.5×), minimum price, minimum average daily turnover (₹ crore), market-cap bucket (large/mid/small/micro), sector/industry.
> - Show: breakout date, months since last 52W high, % above prior high, volume ratio, base length/depth.
> - Run on daily scheduled scans across NSE universe; allow saving scans and adding results to watchlist; trigger alerts on new breakouts.
>
> 2. MARK MINERVINI INVESTMENT CRITERIA (SEPA)
>
> a) Trend Template screener (all conditions shown pass/fail per stock, thresholds editable):
>
> 1. Price > 150-day and 200-day SMA
> 2. 150-day SMA > 200-day SMA
> 3. 200-day SMA trending up for at least 1 month (configurable; ideally 4–5 months)
> 4. 50-day SMA > 150-day and 200-day SMA
> 5. Price > 50-day SMA
> 6. Price ≥ 30% above 52-week low
> 7. Price within 25% of 52-week high
> 8. Relative Strength rating ≥ 70 (compute IBD-style RS percentile vs NIFTY 500 universe, weighted 12-month performance)
>
> b) Stage Analysis: classify each stock into Stage 1–4.
>
> c) VCP (Volatility Contraction Pattern) detection: identify successive contractions (e.g., 25% → 15% → 8% → 3%), number of contractions (T count), volume dry-up near pivot, pivot buy point, and flag pivot breakouts on volume.
>
> d) SEPA fundamental checks: quarterly EPS growth (YoY) and acceleration, revenue growth and acceleration, margin expansion, earnings surprises, annual EPS growth trend, institutional (FII/DII/MF) holding changes, promoter holding/pledge.
>
> e) Risk management: suggested stop-loss (default 7–8% below entry, editable), position sizing from account risk % per trade, risk/reward calculation, and "Minervini score" combining all of the above.
>
> 3. MY CUSTOM INDICATORS
>
> - Include the following custom indicators (name, formula/logic, parameters, how to plot/signal):
>   - [Indicator 1: name — formula — parameters — buy/sell signal rules]
>   - [Indicator 2: ...]
>   - [Indicator 3: ...]
> - Also provide a Custom Indicator Builder: users can define new indicators with formulas over OHLCV and existing indicators, set parameters, plot them on charts, use them in screeners, backtest them, and attach alerts.
>
> 4. NOTIFICATIONS
>
> Create a notification component to show price alerts or news updates for assets in the user's watchlist (including 52W breakout alerts, Trend Template pass/fail changes, VCP pivot breakouts, and custom indicator signals).
>
> 5. KEYBOARD SHORTCUTS
>
> Implement global keyboard shortcuts (e.g., '/', 'Esc') to quickly focus the ticker search and close modals or drawers for a more efficient institutional workflow.
>
> 6. PORTFOLIO & RISK MODULE
>
> - Suggest trade adjustments to reach target asset allocations.
> - Treemap visualization using d3 to display portfolio asset allocation by market value and daily return.
> - 'Automatic Rebalancing' engine that compares the current portfolio distribution against target weightings and generates a list of suggested buy/sell orders to restore target allocations, including estimated Indian transaction costs (brokerage, STT, exchange charges, SEBI fees, stamp duty, GST, DP charges).
> - 'Scenario Analysis' tool to simulate portfolio performance under predefined market shocks (e.g., +20% inflation, -10% market drop, INR depreciation, RBI rate hike) and historical Indian events (2008 GFC, 2016 demonetisation, 2020 COVID crash, etc.).
> - 'Generate PDF Report' button producing a snapshot summary of current holdings, risk metrics, and rebalancing recommendations.
>
> 7. FUNDAMENTAL LAB MODULE
>
> - 'Dividend Analysis' view that projects future dividend yields and payout sustainability based on current free cash flow trends.

**Result:** the first version of the platform, built to this specification.

## Phase 2: Sectors and full market coverage

1. > include trending sector tab on technical parameters identify and score trending sectors and subsectors
2. > custom indicators tab isnt working. remove it if you cant fix it
3. > only limited stocks coming. it should be able to cover ticker analysis for any indian stock i select
4. > revisit and see if you want to make any changes to make it best possible stock trading identification terminal
5. > Top 10 TechnoFunda Buy Recommendations are out of how many stocks
6. > do not show full text of minor resistence breakout support minor support major support on chart. just lines are enough
7. > Top 10 TechnoFunda Buy Recommendations should scan 1000 stocks including all nse 500 stocks all f&o stocks all nifty midcap all nifty small cap stocks
8. > Top 10 TechnoFunda Buy Recommendations and all screnners should scan more than top 1000 stocks including all nse 500 stocks all f&o stocks all nifty midcap all nifty small cap stocks

**Result:** a Trending Sectors screen and coverage widened from a small sample to about 1,100 NSE stocks. Prompt 1 was sent twice, and the session had to be resumed twice after errors.

## Phase 3: Indicators, shareholding and charts

9. > add donchian channel indicator with recent buy and sell alerts
10. > Multi-Indicator Signal Matrix to also include donchian channel indicator status, supertrend status, Mark Minervini SEPA Checklist score, RSI 55–80 Bullish. Also Multi-Indicator Signal Matrix score summary before chart while keeping details where it is
    >
    > at the end of each stock analysis add after SPEA Fundamental anaysis, Shareholding Strength Check: Review the last 4 quarters of shareholding data for [STOCK NAME]. Check whether (1) Promoter stake is increasing (and verify promoter pledging is low/zero), (2) DII stake is increasing, (3) FII stake is increasing, and (4) Public/Retail stake is decreasing. Conclude with a quick verdict on whether "smart money" (promoters + institutions) is accumulating or distributing the stock, noting if any shift is due to dilution rather than open-market buying.
11. > show RS vs NIFTY 500 outperformance breakouts in green zone fill and undeperforming vs NIFTY 500 in red zone fill
12. > Top 10 TechnoFunda Buy Recommendations is still Ranked out of 123 live-scanned NSE stocks. did you not fix my earlier command to cover all nse 500 stocks all f&o stocks all nifty midcap all nifty small cap stocks and more if possible
13. > add option to show candles to show as volume candles on chart and make that as default
    >
    > Something is wrong with your 52 weeks breakout screen. It's not showing any stocks.
    >
    > Move Donchian Channel (20D) · Recent Buy & Sell Alerts tables at the end irrespective of DC(20) selection and show last 2 only and not 5 rows. In Summary and elsewehre, when mentining Upper Channel Last: BUY (18D ago) also add DC Buy Price.
    >
    > Create one more tab for DC channel breakouts. Show the latest DC channel breakouts happening in this week, including today, in that scanner.
    >
    > Portfolio Import & Periodic Updates (Portfolio & Risk Tab): Add two quick-import options so users can upload or refresh their holdings anytime: (1) Excel/CSV Upload supporting standard columns (Ticker, Quantity, Avg. Buy Price, optional Stop-Loss), and (2) Comma-Separated Ticker Input (TradingView-style, e.g., NSE:RELIANCE, NSE:TCS, NSE:INFY) for rapid watchlist/portfolio entry. Include an option to overwrite or merge with the existing portfolio on re-upload, automatically recalculating position weights, sector concentration, and portfolio risk metrics.
    >
    > in trending sectors tab include heatmap of all nifty sector indices like attached for today, this week, this month
    >
    > image.png
    >
    > Include Smart Money (Prom + DII + FII) verdict including 4Q Δ % on top before the chart
14. > I see one dashed line on the chart for the current price of the day.
15. > On the chart screen, give an option to save the default template, like TradingView allows us to, to show only the selected saved indicators as default out of all the indicators available. Also I still dont see volume candles option on the chart - fix it. Portfolio & Risk Management tab show high alerts to exit on my portfolio stocks where trend has shifted to negative or sell, including Multi-Indicator Signal Matrix Summary for below 200 SMA, DC Channel and Supertrend has turnd to sell, etc etc.
16. > In the 'Trending Sectors' tab, add a new section that displays a heatmap of P/E ratios across different Nifty sector indices, helping to visualize sector valuations against their long-term averages.
    >
    > ignore last task for In the 'Trending Sectors' tab, add a new section that displays a heatmap of P/E ratios across different Nifty sector indices, helping to visualize sector valuations against their long-term averages.
17. > Decoupled Signal Markers (Show ST & DC Alerts Without Lines): Add an independent chart toggle (e.g., "Signal Markers Only: ST / DC") that allows users to display Supertrend (ST) and Donchian Channel (DC) Buy/Sell alert markers directly on the price candles even when the ST and DC indicators are turned off. Keep the indicator lines and channels completely hidden to maintain a clean chart, while still computing them in the background to plot compact, color-coded signal badges (e.g., ST B, ST S, DC B, DC S) with hover tooltips showing the exact trigger price and indicator values.
    >
    > Volume Candles Fix (TradingView-Style Dynamic Width Scaling): Fix the Volume Candles chart type so each candlestick's horizontal width scales proportionally to its trading volume, matching TradingView's behavior. Calculate relative volume against the visible range (or rolling average/max) so high-volume bars render noticeably wider/expanded and low-volume bars render narrower/compressed. Apply sensible min/max width clamps (e.g., 25% to 250% of standard bar width) so extreme spikes don't distort the layout and low-volume bars stay readable. Keep wicks centered on each bar, maintain standard bullish/bearish OHLC coloring, and adjust horizontal bar spacing dynamically so expanded candles never overlap adjacent bars while remaining aligned with the synchronized crosshair and indicator sub-panes.
18. > Shareholding Strength Check (Last 4 Quarters) add columns for YoY delta and QoQ % delta
19. > DC channel and supertrend lines appearing even when they are not selected. Only buy sell signal should appear when not selected but lines should not appear when not selected
20. > Turn adx line green when its in buy signal and red when its in red signal
21. > Will Ai integrartion need paid API
22. > ok add basic AI features do not require a paid API key
23. > show RSI above 60 in green on the chart
24. > volume candles instead of showing high volume candle bigger making other low volume candle smaller. thats not how it works on tradingview platform. make volume candle similar to tradingview platform
25. > show NSE Sectors Technical Scorecard and sector or sub-sector Quadrant status before each chart in Multi-Indicator Signal Matrix Summary and also make it part of Multi-Indicator Signal Matrix Summary
26. > move DC Channel breakouts tab after Minervini SEPA tab
27. > Update 52-Week High Breakout Scanner section to also show all time high breakout

**Result:** Donchian and Supertrend signals, the shareholding check, volume candles, saved chart templates, portfolio exit alerts, the DC Channel Breakouts screen, portfolio import, the sector heatmap and the first AI features. The session was resumed three times after errors.

## Phase 4: Scoring, naming, watchlists and screeners

28. > does all NSE 1102 stocks include stocks of all nifty indices
29. > Change ArthaTerminal — Indian Equity Analysis Platform name to TechnoFundaTrades Terminal — Indian Equity Analysis Platform
30. > whats the basis of Call / Score in Top 10 recommendation
31. > can you show HVE HVY and HVQ on top of the relevent bar
    >
    > image.png
32. > Multi-Indicator Signal Matrix Summary should be part of Basis of Call / Score in Top 10 Recommendations section
33. > how can I create a watchlist or import watchlist in excel or comma seperated tickers
34. > Basis of Call / Score in Top 10 Recommendations: Change call score to The Score (0–100) combines Technical & Trend Structure (60 pts) (Minervini SEPA 8-point template, Stage 2, RS Rating, and Multi-Indicator Signal Matrix ratio), Actionable Setup & Timing (15 pts) (VCP Breakout, Pocket Pivot, RS Blue-Dot, Episodic Pivot, MA Pullback, NR7 Squeeze, volume thrust, and an extension penalty if stretched far above the 50-SMA), and Fundamental Growth & Quality (25 pts) (Quarterly EPS & Revenue YoY growth, EPS acceleration, ROE, operating margin expansion, and QoQ FII/DII flow). Call is assigned as Strong Buy (Score ≥ 76, Stage 2, ≥ 7 bullish indicators, not extended), Buy (Score ≥ 62, not extended), or Accumulate on Pullback (extended above 50-SMA or Score < 62).
35. > create a seperate section to analysis up to 5 watchlists inside Portfolio & Risk Management
36. > keep minor res minor support pp/nr7 default off
37. > show call score before each chart alongside Multi-Indicator Signal Matrix Summary score shown before each chart
38. > create HVQ HVY HVE screener tab with options to filter based on Call / Score or Multi-Indicator Signal Matrix Summary score or Minervini SEPA score
39. > remove custom indicators tab
40. > auto ingest nse bhav copy feasture isnt working
41. > in Constituent Leaders part of trending sectors tab show Multi-Indicator Signal Matrix Summary score, call score

**Result:** the app was renamed to TechnoFundaTrades Terminal, the 100-point Call / Score was defined (60 / 15 / 25), and the watchlist analysis and HVE / HVY / HVQ screener were added. Prompt 33 was sent twice.

## Phase 5: Polish, fixes and explanation

42. > Call Multi-Indicator Signal Matrix Summary as Indicators Matrix Summary
43. > remove (T60 · S3 · F25) or whatever text appearing after Call/score on stock analysis page
    >
    > image.png
44. > fix error
    >
    > image.png
45. > fix
    >
    > image.png
46. > give filters for top 10 technofunda buy recommendations to filter buy Score Filter Basis:
    > Call / Score
    > Indicators Matrix Summary
    > Minervini SEPA Score
    > All 3 Combined
    > ATH BO 52W BO
    > HVE HVY HVQ
    >
    > Change title from top 10 technofunda buy recommendations to top top technofunda buy recommendations
47. > how did you decide NSE Sector Scorecard
48. > on charts add option to select deselect ATH high line with number of years since last ATH was touched if the price is coming to that level after 6 months 12 months 24 months presented as ATH 2.4 Yrs e.g.
49. > TechnoFundaTrades Terminal — Indian Equity Analysis Platform
    > Institutional Indian stock analysis platform for NSE and BSE featuring 52-week high breakout scanning, Mark Minervini SEPA Trend Template and VCP detection, custom indicator formula builder and backtester, D3 portfolio treemap, Indian tax-aware automatic rebalancing, stress testing, PDF reporting, and FCF dividend sustainability analysis.
    > doesnt provide right justification. give updated text

**Result:** clearer labels, two error fixes made from screenshots, filters on the buy list, the all-time-high line on charts and an accurate app description. Prompt 46 was sent twice because the first attempt hit a usage quota limit. Gemini's answer to prompt 47 is recorded in `Supporting_Documents/Scoring_Methodology.md`.

## Phase 6: Renaming and publishing

50. > Change terminal name to Personal Trades Terminal in all places
51. > Change Top Buy Recommendations to Top Buy Watchlist in all places and files
52. > why is it taking so long
53. > Fix the errors in the app
54. > Update app description to Personal TechnoFunda equity research and trading terminal for Indian markets, covering an NSE universe of over 1,000 stocks across the NIFTY 500, F&O, Midcap and Smallcap segments. Stocks are ranked on a 100-point Call / Score on TechnoFunda basis, a 16-signal Indicators Matrix Summary and the Mark Minervini SEPA Trend Template with VCP detection, combined into one filterable list of Top TechnoFunda Buy Watchlists. It has screeners covering 52-week and all-time-high breakouts, Donchian channel breakouts and HVE / HVY / HVQ institutional volume surges, which are essesntial in identifying good trade setups. It also has a 4-pillar NSE Sector Scorecard rates each sector from 0 to 100 on trend, relative strength versus the NIFTY 500, momentum and breadth, with RRG rotation quadrants to identify right sectors for trades. The terminal also includes interactive volume-candle charts with Donchian and Supertrend signals, Trade Radar & Regime, Fundamental Lab, Closing Bell Lab, Gemini-powered AI TechnoFunda Briefs and risk reviews, and Indian STCG/LTCG tax-aware portfolio risk and rebalancing analytics. All data is refreshed through automated NSE Bhavcopy end-of-day ingestion.
55. > use personal-trades-terminal.ai.studio url if available

**Result:** the app was renamed from TechnoFundaTrades Terminal to Personal Trades Terminal, the buy list became the Top Buy Watchlist, and the app moved to https://personal-trades-terminal.ai.studio/. I then edited five files by hand in AI Studio (the app icon, `index.html` and `metadata.json`) to finish the description and icon. The session was resumed once after an error.

## What I learned about prompting

1. **Start with a detailed specification.** The first prompt set out the modules, the rules for each screen and what to leave out, and that gave a usable first version.
2. **Then change one thing at a time.** Short prompts naming the exact screen and label were the easiest to check once applied.
3. **Check the output and push back.** When the buy list was still ranking 123 stocks and not 1,000 or more, I said so and asked again until it was fixed.
4. **Use screenshots for errors.** Pasting the error and typing "fix" was usually enough.
5. **Ask the AI to explain its logic.** Questions such as "whats the basis of Call / Score" and "how did you decide NSE Sector Scorecard" let me review the method, and I then set the scoring rule explicitly in prompt 34.
6. **Remove what does not work.** The custom indicators tab was dropped when it could not be fixed.
7. **Expect interruptions.** Errors and quota limits stopped the session several times, so keeping requests small made it easy to resume.
