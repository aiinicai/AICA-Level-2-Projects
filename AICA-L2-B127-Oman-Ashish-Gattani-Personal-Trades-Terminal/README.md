# Personal Trades Terminal — Indian Equity Analysis Platform

**AICA Level 2 Capstone Project (Project Summary Document)**

| | |
|---|---|
| Participant | CA Ashish Gattani |
| Batch | AICA-L2-B127-Oman |
| Course dates | Online: 13 and 14 November 2026. Offline: 19, 20 and 21 November 2026 |
| Live app | https://personal-trades-terminal.ai.studio/ |
| Built with | Google AI Studio (Build mode) and Gemini, using natural-language prompts |

## 1. Problem statement

As an individual investor in Indian equities I could not trade or track my positions properly, and regularly ended up with losses. A large part of the problem was process, not effort:

- The information I needed was spread across many websites. I opened TradingView for charts, Screener.in for fundamentals, Chartink for screeners, and several others, and had to carry numbers from one to the other in my head.
- With no single view, I could not read the market properly. Technical strength, fundamentals, sector trend and overall market condition were never in front of me at the same time.
- With a busy schedule, I could not keep track of my open positions.
- Decisions were therefore inconsistent. There was no fixed checklist for what to buy, when to buy, how much to buy and where to exit.

## 2. Solution

Using what I learned in AICA Level 2 about building an integrated application with AI, I built one app that brings everything onto a single screen. I described what I wanted in plain English and Gemini in Google AI Studio wrote and revised the code. I did not write the code by hand.

The app covers about 1,100 NSE stocks (NIFTY 500, F&O, Midcap, Smallcap and Microcap) and answers four questions in one place:

1. **Is the market healthy?** Market regime, breadth and suggested equity exposure.
2. **Which sectors are leading?** A 4-pillar sector scorecard and sector rotation view.
3. **Which stocks qualify?** A 100-point Call / Score that combines technicals, setup timing and fundamentals.
4. **How do I act?** Entry level, position size, stop-loss and 2R / 3R target levels for each idea.

## 3. Main features

| Screen | What it does |
|---|---|
| Market Overview | NIFTY 50, NIFTY 500 and SENSEX, market regime, breadth, the Top Buy Watchlist, interactive chart, market heatmap and watchlist |
| Trending Sectors | Scores 14 sectors and 146 subsectors on trend, relative strength, momentum and breadth |
| Trade Radar & Regime | Distribution-day tracking, setup signals (Pocket Pivot, NR7, pullbacks, VCP breakouts) and position sizing |
| 52W & ATH Breakouts | Finds stocks breaking 52-week and all-time highs |
| Minervini SEPA | 8-point Trend Template, Stage 1 to 4 classification and VCP detection |
| DC Channel Breakouts | Donchian channel buy and sell alerts |
| HVE / HVY / HVQ Screener | Flags highest volume ever, in a year and in a quarter |
| Portfolio & Risk | Portfolio risk, watchlist analysis and Indian STCG / LTCG tax-aware rebalancing |
| Fundamental Lab | Profit and loss, balance sheet, cash flow, ratios, multiples and dividend sustainability |
| Closing Bell Lab | Reads the daily NSE Bhavcopy file and derives end-of-day metrics |
| AI Desk | Gemini-written TechnoFunda brief and risk review for any stock |

The scoring methodology is explained in `Supporting_Documents/Scoring_Methodology.md`.

## 4. How AI was used

- **Building the app:** every screen, calculation and fix was produced by prompting Gemini in Google AI Studio. The prompts are in `Prompts/Prompt_Log.md`.
- **Inside the app:** Gemini writes a plain-English brief on any stock and a risk review of the portfolio, with an automatic fallback to a lighter Gemini model if the first one times out.
- **Iterating:** errors were fixed by pasting a screenshot of the error and asking Gemini to fix it.

## 5. Link to the AICA Level 2 course

| Course module | How this project applies it |
|---|---|
| Module 1: prompt engineering | The whole app was specified and refined through prompts |
| Module 3: Google AI Studio | Built and configured in Google AI Studio |
| Module 7: Full-Stack Web Based App Development | Taken from idea to design, build and web deployment in Google AI Studio, with a database behind the front end |

## 6. Technology

React, TypeScript, Vite and Tailwind CSS for the screens. Node.js with Express for the server. Lightweight Charts, Recharts and D3 for charts and heatmaps. Firebase (sign-in and Firestore) for saved watchlists. Google Gemini API for the AI features. JSZip and SheetJS for reading NSE Bhavcopy and Excel / CSV files, and jsPDF for PDF reports.

## 7. How to run it

**Option A (recommended): open the live app.** Go to https://personal-trades-terminal.ai.studio/ in any browser.

**Option B: run the source code locally.**

1. Install Node.js (version 20 or later).
2. Open a terminal in the `Source_Code` folder.
3. Run `npm install`.
4. Copy `.env.example` to `.env` and enter your own Gemini API key.
5. Put your own Firebase project details in `firebase-applet-config.json`. The published copy contains placeholders, so sign-in and saved watchlists need your own Firebase project.
6. Run `npm run dev` and open http://localhost:3000.

## 8. Folder contents

| Folder / file | Contents |
|---|---|
| `README.md` | This Project Summary Document |
| `Prompts/` | Prompt log from Google AI Studio |
| `Examples/` | Screenshots of the app and a sample output |
| `Source_Code/` | The executable project exported from Google AI Studio (41 source files). Private keys and pasted chat images have been removed |
| `Supporting_Documents/` | Scoring methodology and data sources |

## 9. Outcome

I now see charts, fundamentals, screeners, sector trends and risk levels on one page instead of on many websites. Every idea is tested against the same checklist, with a predefined entry, position size and stop-loss, which brings discipline to decisions that I previously took in a scattered way.

## 10. Limitations and disclaimer

- The app is a personal research and learning tool. It is not investment advice, and its "Buy" labels are the output of rule-based screens, not recommendations to any person.
- Scores depend on the quality and timeliness of the underlying market data.
- No screening tool can guarantee profits or prevent losses. The user remains responsible for every decision.
- Broker connection for order execution is included in the design but is not connected.
