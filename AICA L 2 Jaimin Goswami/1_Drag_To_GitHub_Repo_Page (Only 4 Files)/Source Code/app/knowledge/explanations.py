"""Comprehensive Financial Event Intelligence & Market Impact Knowledge Engine.
Provides detailed explanations covering:
  - 1. The Concept & Definition
  - 2. What It Means in Practice
  - 3. What It Effects (Equities, Bonds, Currency/Forex, Borrowing Costs)
  - 4. Relevance & Strategic Significance
  - 5. How to Interpret Readings (Beat vs Miss Playbook)
"""

def get_event_deep_explanation(event: dict) -> dict:
    title = event.get("title", "").lower()
    kind = event.get("kind", "")
    category = event.get("category", "")
    authority = event.get("authority", "")
    indicator = event.get("indicator", "")

    # 1. RBI MPC Policy Rate Decision
    if any(k in title for k in ("rbi", "repo", "monetary policy committee", "mpc")) or indicator == "Policy Repo Rate":
        return {
            "concept": "The Policy Repo Rate is the benchmark lending rate at which the Reserve Bank of India (RBI) lends overnight funds to commercial banks against pledged government securities under the Liquidity Adjustment Facility (LAF). It serves as the primary instrument for monetary policy implementation in India, anchoring all short-term money market rates and the broader cost of capital across the financial system.",
            "what_it_means": "An RBI MPC policy decision determines the benchmark borrowing cost for commercial banks. When the MPC adjusts the repo rate (e.g., maintaining the benchmark at 5.50% with Standing Deposit Facility [SDF] at 5.25% and MSF/Bank Rate at 5.75%), commercial bank deposit and lending rates adjust accordingly. A stance of 'Calibrated Tightening' indicates heightened vigilance against inflation upside, whereas a 'Neutral' stance offers equal flexibility for rate increases or cuts based on incoming high-frequency macroeconomic data.",
            "what_it_effects": {
                "equities": "Lower rates reduce corporate discount rates and borrowing overheads, boosting equity valuations. High-beta and rate-sensitive sectors (Banking, Non-Banking Financial Companies [NBFCs], Real Estate, Automobiles, and Infrastructure) typically rally strongly. Bank Net Interest Margins (NIMs) may temporarily compress if lending rates reprice faster than deposit liabilities.",
                "bonds": "Benchmark 10-year Indian Government Bond (G-Sec) yields decline, triggering capital appreciation across bond portfolios. Shorter-term treasury yields drop immediately, leading to a steeper yield curve.",
                "currency": "Rate cuts narrow the interest rate differential between India and the US, which can put mild short-term depreciation pressure on the Indian Rupee (INR) against the USD unless counterbalanced by strong foreign portfolio investment (FPI) equity inflows.",
                "borrowers": "External Benchmark Lending Rates (EBLR) linked directly to the repo rate adjust downward immediately, leading to lower monthly EMIs for home loans, vehicle loans, and floating-rate MSME advances within 30 days."
            },
            "relevance": "The repo rate is the single most influential economic variable in India. It directly influences GDP growth velocity, aggregate consumer demand, wholesale capital expenditure, corporate debt servicing capabilities, and sovereign borrowing costs for the Government of India.",
            "interpretation": "ACTUAL < FORECAST: Dovish surprise; stimulates stock market rallies and rallies bond prices. ACTUAL > FORECAST: Hawkish surprise; bond yields spike, equities face downward pressure. STANCE PIVOT TO NEUTRAL: Precursor to an easing cycle, highly favorable for domestic capital markets."
        }

    # 2. Consumer Price Index (CPI) Inflation
    if any(k in title for k in ("cpi", "consumer price index", "inflation")):
        return {
            "concept": "The Consumer Price Index (CPI) measures the average change over time in the prices paid by urban and rural consumers for a representative market basket of consumer goods and services. In India, the National Statistical Office (MoSPI) publishes the All-India Consumer Price Index (Combined) with base year 2012=100. The basket is heavily weighted toward Food and Beverages (45.86%), followed by Miscellaneous Services (28.32%), Housing (10.07%), Fuel and Light (6.84%), and Clothing/Footwear (6.53%).",
            "what_it_means": "CPI quantifies retail purchasing power erosion. Under the statutory Flexible Inflation Targeting (FIT) framework, the RBI is mandated to maintain headline CPI inflation at 4.0% with a tolerance band of +/- 2% (2.0% to 6.0%). A print above 6.0% represents a regulatory breach requiring official explanation to the Government of India.",
            "what_it_effects": {
                "equities": "Elevated inflation compresses operating margins across FMCG, consumer durables, and manufacturing companies due to higher raw material and wage costs. It forces the central bank to maintain higher interest rates, compressing market price-to-earnings (P/E) multiples.",
                "bonds": "Higher inflation erodes real bond yields. Fixed-income investors demand higher yields, leading to bond sell-offs and rising G-sec yields across maturities.",
                "currency": "Persistent high inflation weakens domestic purchasing power, generating long-term depreciation pressure on the Rupee via Purchasing Power Parity (PPP) dynamics.",
                "borrowers": "High CPI keeps central bank policy rates elevated, maintaining high interest rates on personal loans, housing finance, and commercial borrowings."
            },
            "relevance": "Retail inflation is the primary economic scorecard for central bankers. It dictates interest rate cycles, wage renegotiations, cost-of-living adjustments, and government subsidy expenditures.",
            "interpretation": "ACTUAL < FORECAST: Disinflationary; paves the way for central bank rate cuts, triggering market-wide rallies. ACTUAL > FORECAST: Inflationary shock; increases probability of rate hikes or delayed rate cuts, triggering sell-offs in bond and rate-sensitive equity markets."
        }

    # 3. Gross Domestic Product (GDP)
    if any(k in title for k in ("gdp", "gross domestic product")):
        return {
            "concept": "Gross Domestic Product (GDP) represents the total monetary value of all finished goods and services produced within a country's geographical borders over a specific quarterly or annual period. Real GDP adjusts nominal output for price inflation using the GDP deflator, reflecting genuine volume expansion across Agriculture, Industry, and Services sectors.",
            "what_it_means": "GDP growth is the definitive indicator of national economic health. Growth rates above 7.0% categorize India among the fastest-growing major global economies, signaling robust corporate revenue generation, active capital investment, and expanding consumer demand.",
            "what_it_effects": {
                "equities": "Strong GDP prints directly correlate with double-digit corporate revenue growth and earnings per share (EPS) expansion. Attracts substantial Foreign Institutional Investor (FII) and Foreign Portfolio Investor (FPI) equity inflows.",
                "bonds": "Robust economic expansion can increase credit demand across the private sector, competing with government borrowing and causing bond yields to firm up slightly.",
                "currency": "Strong growth fundamentals boost international confidence in the economy, attracting foreign direct investment (FDI) and strengthening the Indian Rupee against major trading currencies.",
                "borrowers": "High growth boosts consumer confidence, increases capacity utilization across manufacturing plants, and stimulates commercial bank lending."
            },
            "relevance": "GDP dictates sovereign credit ratings (Moody's, S&P, Fitch), determines the debt-to-GDP fiscal consolidation trajectory, and guides global asset allocators in country-weighting decisions.",
            "interpretation": "ACTUAL > FORECAST: Economic acceleration; prompts institutional upgrades to market earnings targets and drives broad-based equity surges. ACTUAL < FORECAST: Growth slowdown; triggers concerns over corporate revenue deceleration and prompts defensive asset reallocations."
        }

    # 4. Corporate Earnings & Financial Results
    if kind == "Corporate" or any(k in title for k in ("results", "financial results", "quarterly", "q1", "q2", "q3", "q4", "earnings")):
        company = event.get("company") or "the listed company"
        return {
            "concept": f"Statutory financial results disclosure mandated under Regulation 33 of SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015. Listed entities must publish audited or limited reviewed quarterly and annual financial statements, accompanied by segment revenue, EBITDA, profit after tax (PAT), and management commentary.",
            "what_it_means": f"Discloses the actual operational and financial performance of {company} for the reporting quarter. It reveals whether revenue growth, margin realization, and debt servicing capabilities met, exceeded, or fell short of institutional consensus projections.",
            "what_it_effects": {
                "equities": f"Triggers immediate price discovery and volatility in {company}'s stock price during market hours or next open. Substantial beats prompt broker upgrades and target price revisions; misses can cause rapid deratings of 5% to 15% in single-day trading.",
                "bonds": f"For debt-issuing corporates, strong cash generation improves interest coverage ratios, lowering credit default swap (CDS) spreads and commercial paper yields.",
                "currency": "For export-heavy conglomerates (IT services, Pharmaceuticals), foreign exchange realization and cross-currency headwinds are revealed, impacting hedging strategies.",
                "borrowers": "Strong balance sheet deleveraging allows corporations to negotiate finer borrowing spreads with consortia of commercial banks."
            },
            "relevance": "Corporate earnings are the ultimate fundamental bedrock of stock market valuations. Multiple consecutive quarterly earnings beats drive sustained multi-year re-ratings.",
            "interpretation": "ACTUAL > FORECAST: Earnings beat; stock typically opens with a gap up, driven by institutional accumulation. ACTUAL < FORECAST: Earnings miss; triggered by margin compression or slowing volume, leading to immediate institutional selling."
        }

    # 5. Dividends & Corporate Actions
    if any(k in title for k in ("dividend", "bonus", "split", "buyback", "record date", "ex-date")):
        return {
            "concept": "A corporate action initiated by a company's Board of Directors that brings a material change to the company and affects its stakeholders. Cash dividends distribute accumulated retained earnings to equity shareholders; stock splits and bonus issues alter capital share structure without changing aggregate market capitalization.",
            "what_it_means": "The announcement confirms dividend payout quantum, Record Date, and Ex-Date. On the Ex-Date, the stock begins trading without the entitlement to the declared dividend, causing an automatic theoretical price adjustment at market open equal to the declared dividend amount.",
            "what_it_effects": {
                "equities": "Provides direct cash yields to shareholders. High-dividend declarations attract income-oriented institutional funds, mutual funds, and long-term retail investors.",
                "bonds": "Substantial cash outflows for dividends reduce corporate liquidity, carefully tracked by corporate bond credit rating agencies.",
                "currency": "Foreign institutional shareholders receiving substantial INR dividends may repatriate funds, creating periodic localized forex demand.",
                "borrowers": "Reflects management confidence in ongoing cash flow generation and low near-term leverage distress."
            },
            "relevance": "Dividend consistency reflects balance sheet strength, corporate governance quality, and capital allocation discipline.",
            "interpretation": "Higher-than-expected dividend payouts signal surplus cash generation and reward shareholders; dividend omissions or cuts indicate capital conservation or operating stress."
        }

    # 6. SEBI & Exchange Regulatory Circulars
    if kind == "Regulatory" or any(k in title for k in ("sebi", "circular", "lodr", "regulation", "compliance", "board meeting")):
        return {
            "concept": "Statutory circulars, notifications, and directives issued by the Securities and Exchange Board of India (SEBI) under the SEBI Act, 1992, or by stock exchanges (NSE/BSE). These directives govern market microstructure, disclosure standards, corporate governance norms, trading surveillance, and investor protection.",
            "what_it_means": "Establishes mandatory compliance frameworks, filing deadlines, capital adequacy norms, or insider trading guardrails for listed companies, registered intermediaries, asset management companies, and market participants.",
            "what_it_effects": {
                "equities": "Changes in margin rules, derivatives contract sizes (e.g. index F&O contract revisions), or surveillance frameworks (ASM/GSM) directly alter market liquidity, speculative trading volumes, and brokerage revenues.",
                "bonds": "Regulations on corporate bond market infrastructure, mandatory credit rating disclosures, or debenture trustee frameworks influence private placement bond liquidity.",
                "currency": "Foreign portfolio investor (FPI) registration and disclosure norms affect foreign capital inflow friction.",
                "borrowers": "Mandated corporate governance norms improve transparency and reduce the risk premium demanded by domestic and international lenders."
            },
            "relevance": "Regulatory directives define the rules of engagement for capital markets, safeguarding systemic integrity, preventing market manipulation, and ensuring fair price discovery.",
            "interpretation": "Regulatory easing encourages product innovation and market participation; tighter compliance mandates may cause temporary trading volume compression while strengthening long-term institutional trust."
        }

    # 7. Generic Fallback
    return {
        "concept": f"An official financial event in the {category} category published by {authority}. Financial market participants track these releases to gauge economic momentum, corporate health, and regulatory compliance.",
        "what_it_means": f"This scheduled or published milestone records official disclosures submitted to exchanges, regulatory authorities, or statistical bureaus. It provides verifiable primary source documentation for market evaluation.",
        "what_it_effects": {
            "equities": "Influences market sentiment, sector-specific valuation multiples, and institutional capital reallocations depending on whether the release aligns with market consensus.",
            "bonds": "Shapes interest rate expectations and risk premiums across government and corporate debt instruments.",
            "currency": "Influences international trade expectations, capital flow momentum, and foreign exchange valuations.",
            "borrowers": "Acts as an input into commercial lending benchmarks, corporate credit spreads, and institutional funding conditions."
        },
        "relevance": "Provides primary-source fundamental data required for risk assessment, quantitative trading models, and fiduciary compliance.",
        "interpretation": "Compare the reported reading or filing disclosure against historical trends and consensus forecasts to determine directional impact."
    }
