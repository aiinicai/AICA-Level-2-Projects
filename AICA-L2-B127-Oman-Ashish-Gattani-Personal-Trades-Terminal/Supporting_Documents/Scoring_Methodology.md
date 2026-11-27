# Scoring Methodology and Data Sources

## 1. Call / Score (100 points per stock)

Each stock receives one score out of 100, built from three parts:

| Part | Points | What it measures |
|---|---|---|
| Technical and trend structure | 60 | Minervini SEPA Trend Template, Stage 2 status, relative strength and the Indicators Matrix Summary |
| Actionable setup and timing | 15 | Whether there is a current entry setup, such as a pivot breakout or a volatility contraction |
| Fundamental growth and quality | 25 | Earnings and revenue growth, return on equity and institutional shareholding change |

The score is shown with a call such as "Strong Buy" or "Accumulate on Pullback". A stock trading far above its 50-day average is marked "Extended" so that it is not chased.

## 2. Indicators Matrix Summary

A panel of 16 technical signals is checked for each stock. The result is shown as a score out of 100 and as the number of bullish signals, for example "91/100 (14/16B)".

## 3. Minervini SEPA Trend Template

Each stock is tested against the 8-point Trend Template and classified into Stage 1 (basing), Stage 2 (advancing), Stage 3 (topping) or Stage 4 (declining). Volatility Contraction Patterns (VCP) and their pivot levels are detected automatically.

## 4. NSE Sector Scorecard (4 pillars)

Each sector is converted into an equal-weight index of its stocks and scored from 0 to 100 on four pillars:

| Pillar | What it looks at |
|---|---|
| Trend and moving-average structure | Position above the 21, 50, 150 and 200-day averages, a rising 200-day average, and correct stacking of the averages |
| Relative strength vs NIFTY 500 | Average relative-strength rating of the stocks, RS-Ratio and RS-Momentum |
| Momentum and directional strength | RSI (14), MACD state and ADX (14) |
| Breadth, 52-week highs and volume | Share of stocks above the 50-day average, share in Stage 2, share near 52-week highs, and volume thrust |

The default "Balanced Institutional" model weights each pillar at 25%. Scores map to regimes:

| Sector score | Regime |
|---|---|
| 78 and above | Strong Uptrend |
| 64 to 77 | Trending Bullish |
| 48 to 63 | Emerging / Base |
| 35 to 47 | Neutral / Weakening |
| Below 35 | Downtrend |

RS-Ratio and RS-Momentum also place each sector in a rotation quadrant: Leading, Improving, Weakening or Lagging.

## 5. Volume signals

| Signal | Meaning |
|---|---|
| HVE | Highest volume ever |
| HVY | Highest volume in over a year (252 trading days) |
| HVQ | Highest volume in a quarter (63 trading days) |

## 6. Risk levels

For each idea the app shows an entry level, a stop-loss, the number of shares based on risking a fixed 1% of capital, and target levels at 2 times and 3 times the risk (2R and 3R).

## 7. Data sources

| Source | Used for |
|---|---|
| NSE India daily Bhavcopy files | End-of-day prices, volumes, indices and corporate actions |
| BSE filings | SENSEX, earnings, shareholding and dividends |
| Broker connection (Zerodha Kite, Dhan, Upstox) | Holdings and orders. Included in the design but not connected |

All data used is public market data. No client or confidential data is used.
