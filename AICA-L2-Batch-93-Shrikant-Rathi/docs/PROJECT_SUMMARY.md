# Project summary: LookThrough

**AICA Level 2 capstone · Individual project · Built on the course's Modules 1, 2, 5, 6, 7, 9 and 10**

## 1. Problem statement
Family offices hold listed equity both directly and through many mutual funds, across several entities: individuals, an HUF and an LLP. Investment policies set limits on single stocks, sectors, concentration and cost. The combined exposure, direct plus inside every fund, is rarely visible. The same bank can sit in the direct book and inside six funds, two funds with different names can hold nearly identical portfolios, and a policy breach can go unnoticed for months. Building the look-through by hand means reconciling a dozen AMC portfolio spreadsheets every month, so in practice it isn't done.

## 2. Objective
Give the investment committee (the CIO and the analyst) a verifiable, current answer to three questions:
1. *What do we really own?*
2. *Are we within the policy?*
3. *What changed since last month?*

Let them ask questions in plain English without the AI being able to invent a number.

## 3. Solution
| Layer | What it does |
|---|---|
| **Data bridge** (Python) | Downloads AMFI NAVs, AMC monthly portfolio disclosures (with URL, time and SHA-256 recorded) and prices; builds one dataset |
| **Engine and app** (JavaScript, single offline HTML) | FIFO holdings, XIRR, look-through, concentration (HHI, top 10), sectors, overlap, fund risk metrics, company ratios and F-score, stress tests, indicative tax, policy alerts |
| **Reference engine** (pandas) | Recomputes every metric independently; reconciled against the app on 4,664 values |
| **MCP server** | Exposes the reference engine to Claude as 11 read-only tools, an `ic_note` prompt and a `verify_note` QC gate |
| **Data entry and sign-in** (bridge) | Entities and transactions entered in the app, validated server-side (priced instrument, no oversell, no future dates) and saved with an audit trail; viewer / analyst / admin roles with hashed passwords and lockout; sign-out after 30 minutes idle; script-hash Content-Security-Policy; installable (PWA) with a service worker that caches no portfolio data |
| **Contract-note import** (bridge) | Reads a broker's PDF contract note (incl. password-protected), proposes the trades with charges allocated to cost (not STT), reconciles them to the note's net amount and checks each rate against market prices; nothing is saved until a person confirms, then all trades are recorded together or none |
| **CAS import** (bridge) | Reads a CAMS / KFintech detailed CAS; reconciles each folio's unit balance line by line and to the closing balance; matches scheme and plan by ISIN; flags untracked schemes, opening balances, implausible NAVs and transactions already recorded; nothing saved until confirmed |
| **Scheme master** (bridge) | Adds mutual-fund schemes from AMFI's list (Direct and Regular Growth codes, checked against AMFI), fetches their NAV history and rebuilds; equity-oriented funds only, so the tax view stays correct |
| **Security master** (bridge) | Adds NSE-listed companies (prices and, where available, statements fetched for that company only); fund holdings known only by weight are priced on demand; sector editable because it drives the sector limit |
| **n8n workflow** | Monthly: validates the PC's results, compares with the last run, logs every run, emails the committee on a breach or a resolved breach |

## 4. Methodology
- **Look-through:** each fund's rupee value × its disclosed weight in each stock, added to direct holdings. Debt and cash inside funds are kept separate. Funds without a disclosure are reported as "not looked through", never estimated.
- **Returns:** XIRR on dated cash flows (the result is accepted only if it actually solves the cash flows); CAGR on month-end NAVs; Direct-plan NAVs for fund metrics.
- **Risk:** annualised volatility; Sharpe and Sortino at a risk-free rate of 6.5% (a policy input); maximum drawdown; beta, alpha, tracking error and information ratio against the scheme benchmark; up- and down-capture ratios; 12-month rolling beat rate.
- **Concentration:** HHI and effective number of stocks, top-10 share, sector weights, pairwise fund overlap (the sum of the smaller common weights).
- **Equity screen:** ROE, ROCE, growth, leverage, interest cover, CFO/PAT, Piotroski F-score, P/E and P/B against sector medians. Lenders are tested on a separate set. The output is a screening label, never a buy/sell call.
- **Tax (indicative):** FIFO lots, a 12-month holding period for listed equity, short-term losses set off against long-term gains, a Rs 1.25 lakh exemption per assessee. Income-tax Act, 2025, ss. 196 and 198 (tax year 2026-27).

## 5. AI methodology
- **Tools, not free text.** Claude answers only through tool calls to the reconciled engine. Every response carries the valuation date, the basis and caveats.
- **Tagged reasoning.** Each statement is labelled FACT, CALC, ASSUMPTION or VIEW.
- **A deterministic QC gate.** `verify_note` extracts every figure from Claude's draft and binds it to one field a tool returned in that session: the value must match within the note's rounding; the unit must match (only crore/lakh and fraction/% restatements are allowed); the tool cited on the line must be the one that returned it; and the words around the figure must name that field and not a sibling field of the same record ("total" written as "held directly"). Each refusal gives the reason. Code checks the model; it is not a second model's opinion.
- **Maker-checker extraction.** The LLM extracts annual-report figures to schema-checked JSON with the source line for each figure. A person approves the figures before they are used.

## 6. Evaluation
| Test | Result |
|---|---|
| App vs reference engine | 4,664 values reconciled, 72 not-computable cases agreed, 20/20 check groups |
| Independent oracle tests (raw data, not via either engine) | 12/12 |
| Sign-in, roles and data entry against a real bridge (isolated temp data) | 49/49; guards mutation-tested |
| Browser flow: setup, sign-in, add entity, record trade, oversell blocked, contract-note and CAS import, add a scheme and a company, users, audit, sign-out | 32/32 |
| Security master (validation, pricing rule, statements optional, fund holdings priced on demand, edit, removal) | 22/22; guards mutation-tested |
| Scheme master (search, validation, NAV-history rule, use, edit, removal) | 28/28; guards mutation-tested |
| CAS reader (CAMS and KFintech layouts, encrypted copy, 7 rejection cases, bridge import and duplicate detection) | 32/32; guards mutation-tested |
| Contract-note reader (2 broker layouts, encrypted copy, 8 rejection cases, bridge import) | 37/37; guards mutation-tested |
| Functional tests (parsers, import round-trip, policy controls, simulator, missing data, ISIN) | 23/23 |
| Smoke test (15 screens × 6 entities, dark theme, phone width) | 0 errors, 0 horizontal scroll |
| MCP tool tie-out, QC-gate binding tests (coincidence, citation, unit, field swap), input validation, live stdio session | 42/42; six binding rules mutation-tested |
| Sample IC note through `verify_note` | 32 figures bound to their fields, 0 untraced |
| n8n workflow (pinned test data) | New and resolved breaches and the value change detected; a malformed payload rejected with all 4 reasons |

## 7. Results (demo family, 31-Aug-2026)
The portfolio is worth Rs 47.17 cr, with an XIRR of 7.96%. All 12 funds are looked through, covering 501 companies. On the combined (look-through) basis there are **two policy breaches and three warnings**:
- Breach: HDFC Bank at 12.56% of equity (limit 10%). Rs 1.87 cr of its Rs 5.71 cr sits inside mutual funds, and neither the direct book nor any single fund factsheet shows that.
- Breach: Financial Services at 33.39% of equity (limit 30%).
- Warnings: three held fund pairs overlap above the 50% limit: ICICI Prudential Large Cap and Nippon India Large Cap (54.56%, return correlation 0.976), and each of them with the UTI Nifty 50 Index Fund (63.95% and 61.02%), so two expense ratios are paid for largely the same stocks.

Market-cap mix of look-through equity (size known for 97.5%): large cap 77.5% against a 60% target, mid cap 12.9% against 25%, small cap 7.1% against 15%, all outside the 5-point band. A 20% market fall is estimated to cost Rs 8.74 cr (19.21% of equity) at a portfolio beta of 0.96.

## 8. Limitations
- Prices, company statements and indices come from Yahoo Finance (a secondary source). The indices are price indices, not total-return indices, which flatters fund-versus-benchmark comparisons. One benchmark (Smallcap) is substituted by the Nifty 500.
- Company statements come from Yahoo Finance, a secondary source that can be wrong. Where it is known to be wrong, the company's own audited figures replace it through `data/config/official_financials.json`, with the filing linked beside the figures. HDFC Bank is the first case: Yahoo overstated its net worth, which put its ROE at 8.9%; on its audited standalone figures (SEC Form 6-K) the ROE is 14.1%. Other companies' statements still need checking against their annual reports before anyone relies on them.
- Portfolio disclosures are loaded for all 12 schemes. Most are downloaded by `bridge/fetch_amc.py`; Kotak's download server blocks automated access, so its files are downloaded by hand and registered with `fetch_amc.py --local` (the file must read as that scheme and month; the manifest records the page, original name and SHA-256). UTI's consolidated all-scheme file is read block by block.
- Expense ratios are not loaded, so the weighted-expense-ratio test is NOT COMPUTABLE.
- Infosys reports in USD, so its ratios are excluded rather than mis-stated. Lenders show "Insufficient data" until GNPA, NNPA and CAR are entered.
- The offline `LookThrough.html` is a read-only snapshot: anyone with the file can read it. Sign-in and data entry work only through the local data bridge.
- The contract-note reader is tested on two fictitious layouts only; each broker's real note should be tried once and checked line by line. It reads equity notes (not F&O) and electronic PDFs (not scans). The CAS reader handles the CAMS / KFintech detailed CAS; NSDL/CDSL depository CAS and summary statements are refused with what to request instead, and only the schemes the app tracks can be recorded (others can be added from AMFI's list).
- Only equity-oriented schemes can be added: the tax view applies listed-equity rules to every fund. Debt, liquid, gold, international and fund-of-funds schemes (taxed as specified mutual funds at slab rates) and hedged categories are refused until the tax engine models them. An added scheme is looked through only once its AMC portfolio file is applied.
- Size classes use market-cap thresholds set in the policy (large from Rs 1,00,000 cr, mid from Rs 33,000 cr) as an approximation of SEBI's rank-based categories (top 100 / 101-250 / rest, per AMFI's half-yearly list; SEBI circular of 6 October 2017). The large-cap threshold matches rank 100 in the data (Rs 1,00,156 cr); both should be checked against AMFI's latest list.
- 49 fund holdings are still unpriced: 6 foreign stocks and recent listings with under 13 months of prices. They are 2.4% of look-through equity and are shown as unclassified.
- `verify_note` binds figures by value, unit, citation and wording; it does not judge the argument. A correctly bound figure can still be used in a weak argument, which is why every statement is also tagged FACT, CALC, ASSUMPTION or VIEW for the committee. Before binding was added, a stale note passed two of its three wrong figures by coincidence (0.94 was also the cash held in funds); with binding, all three are refused with a reason.
- Only NSE-listed shares can be added (the app prices through NSE symbols); BSE-only companies are refused with the reason.
- ISIN changes (e.g. after a split) are resolved by the issuer code: an old equity ISIN no longer on NSE's list is read as the same issuer's current equity share, and each such mapping is listed in the data warnings (two in the current files: TD Power Systems, Kirloskar Pneumatic, which had shown as false sells in fund-manager activity). An issuer with more than one listed equity line is not mapped.
- Not yet done: keyboard access to chart elements.
- Analytics are at the month-end valuation date (31-Aug-2026), because AMC portfolio disclosures are monthly and returns, risk and the reconciliation are built on month-end prices. With the bridge running, value, gain and the concentration limits are also shown at latest prices, beside the month-end figures and refreshed every 5 minutes; each fund's latest NAV is spread over its last disclosed holdings. Every such figure names its price and NAV dates (Yahoo NSE quotes are about 15 minutes delayed, not a licensed real-time feed; AMFI publishes NAVs once each business day). Never in the offline snapshot. When fund holdings are a month older than the prices (the first days of each month, before the AMCs publish), every look-through screen and MCP tool says so.
- Fund holdings are month-end snapshots. Tax is indicative and excludes surcharge, cess and brought-forward losses.

## 9. Responsible AI
- **No confidential data.** A fictitious family on public market data. Nothing sensitive is entered into any AI platform (ICAI AICA guideline).
- **Decision support, not advice.** Screening labels replace buy/sell language, and every tool response and note carries the disclaimer. The committee decides.
- **No invented numbers.** Figures come from tools and are verified by code. Missing data is never estimated or shown as compliant.
- **Transparency.** Sources are labelled official or secondary, and every AMC file carries its SHA-256. MCP calls and monitor runs have audit logs.
- **Independent review.** A financial-logic review and a UI/UX audit were run before submission; every Critical and Major finding was fixed and is guarded by an oracle test.
- **Least privilege.** Viewer, analyst and admin roles; passwords stored only as salted PBKDF2 hashes; every change audited. MCP tools are read-only. The n8n webhook requires a token kept outside the code, and the alert recipient cannot be changed by the incoming data.

## 10. Future work
Total-return benchmarks from NSE Indices. Company statements verified against annual reports, with a maker-checker record. Expense ratios loaded from AMFI. AMC file downloads automated where the AMC provides a stable link. Testing the offline-LLM extraction with LM Studio. Per-entity policy limits. Publishing the app as a PWA with authentication.
