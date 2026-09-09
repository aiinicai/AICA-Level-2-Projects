"""
Business Risk Assessment Tool - Financial Ratio Analysis
Client: Trident Engineering Pvt. Ltd. (Manufacturing)
Prepared for: AICA Level 2 Capstone Project
Purpose: Computes key financial ratios over 3 years, assigns risk scores
         based on standard benchmarks, and derives a Composite Business
         Risk Score with a plain-English summary.

Note: All financial figures below are illustrative/fictional.
Benchmark thresholds are general in nature and should be adjusted per
industry norms and professional judgment before use in an actual
client engagement.
"""

# ---------------------------------------------------------------------------
# TASK 1: SAMPLE FINANCIAL DATA (3 years)
# ---------------------------------------------------------------------------
# Figures are in INR Lakhs, illustrative for a mid-sized manufacturing company.

financial_data = {
    "FY 2023-24": {
        "current_assets": 480,
        "current_liabilities": 380,
        "inventory": 150,
        "total_debt": 420,
        "total_equity": 260,
        "ebit": 95,
        "interest_expense": 55,
        "net_profit": 32,
        "revenue": 1100,
        "capital_employed": 680,
        "operating_cash_flow": 60,
        "average_inventory": 140,
        "average_debtors": 160,
        "total_assets": 900,
    },
    "FY 2024-25": {
        "current_assets": 520,
        "current_liabilities": 370,
        "inventory": 160,
        "total_debt": 400,
        "total_equity": 300,
        "ebit": 115,
        "interest_expense": 50,
        "net_profit": 48,
        "revenue": 1250,
        "capital_employed": 700,
        "operating_cash_flow": 85,
        "average_inventory": 155,
        "average_debtors": 150,
        "total_assets": 960,
    },
    "FY 2025-26": {
        "current_assets": 560,
        "current_liabilities": 340,
        "inventory": 165,
        "total_debt": 360,
        "total_equity": 360,
        "ebit": 140,
        "interest_expense": 42,
        "net_profit": 66,
        "revenue": 1400,
        "capital_employed": 720,
        "operating_cash_flow": 110,
        "average_inventory": 162,
        "average_debtors": 130,
        "total_assets": 1020,
    },
}

years = list(financial_data.keys())

# ---------------------------------------------------------------------------
# TASK 2: RATIO CALCULATION FUNCTIONS
# ---------------------------------------------------------------------------

def current_ratio(d):
    return round(d["current_assets"] / d["current_liabilities"], 2)

def quick_ratio(d):
    return round((d["current_assets"] - d["inventory"]) / d["current_liabilities"], 2)

def debt_equity_ratio(d):
    return round(d["total_debt"] / d["total_equity"], 2)

def interest_coverage_ratio(d):
    return round(d["ebit"] / d["interest_expense"], 2)

def net_profit_margin(d):
    return round((d["net_profit"] / d["revenue"]) * 100, 2)

def roce(d):
    return round((d["ebit"] / d["capital_employed"]) * 100, 2)

def roe(d):
    return round((d["net_profit"] / d["total_equity"]) * 100, 2)

def inventory_turnover_ratio(d):
    return round(d["revenue"] / d["average_inventory"], 2)

def debtors_turnover_ratio(d):
    return round(d["revenue"] / d["average_debtors"], 2)

def asset_turnover_ratio(d):
    return round(d["revenue"] / d["total_assets"], 2)

def ocf_to_debt_ratio(d):
    return round(d["operating_cash_flow"] / d["total_debt"], 2)


# Map of ratio name -> (function, category)
RATIO_FUNCTIONS = {
    "Current Ratio": (current_ratio, "Liquidity"),
    "Quick Ratio": (quick_ratio, "Liquidity"),
    "Debt-Equity Ratio": (debt_equity_ratio, "Solvency"),
    "Interest Coverage Ratio": (interest_coverage_ratio, "Solvency"),
    "Net Profit Margin (%)": (net_profit_margin, "Profitability"),
    "ROCE (%)": (roce, "Profitability"),
    "ROE (%)": (roe, "Profitability"),
    "Inventory Turnover Ratio": (inventory_turnover_ratio, "Efficiency"),
    "Debtors Turnover Ratio": (debtors_turnover_ratio, "Efficiency"),
    "Asset Turnover Ratio": (asset_turnover_ratio, "Efficiency"),
    "OCF to Total Debt Ratio": (ocf_to_debt_ratio, "Solvency"),
}

# Compute all ratios for all years -> {ratio_name: {year: value}}
computed_ratios = {}
for ratio_name, (func, category) in RATIO_FUNCTIONS.items():
    computed_ratios[ratio_name] = {}
    for year in years:
        computed_ratios[ratio_name][year] = func(financial_data[year])


# ---------------------------------------------------------------------------
# TASK 3: RISK SCORING LOGIC
# ---------------------------------------------------------------------------

def score_ratio(name, value):
    """Return risk score: 1 = High Risk, 2 = Moderate Risk, 3 = Low Risk."""
    if name == "Current Ratio":
        if value < 1.0:
            return 1
        elif value <= 1.5:
            return 2
        else:
            return 3
    elif name == "Quick Ratio":
        if value < 0.8:
            return 1
        elif value <= 1.2:
            return 2
        else:
            return 3
    elif name == "Debt-Equity Ratio":
        if value > 2:
            return 1
        elif value >= 1:
            return 2
        else:
            return 3
    elif name == "Interest Coverage Ratio":
        if value < 1.5:
            return 1
        elif value <= 3:
            return 2
        else:
            return 3
    elif name == "Net Profit Margin (%)":
        if value < 5:
            return 1
        elif value <= 10:
            return 2
        else:
            return 3
    elif name == "ROCE (%)":
        if value < 10:
            return 1
        elif value <= 15:
            return 2
        else:
            return 3
    elif name == "ROE (%)":
        # Using similar benchmark bands to ROCE for this illustrative model
        if value < 10:
            return 1
        elif value <= 15:
            return 2
        else:
            return 3
    elif name == "Inventory Turnover Ratio":
        if value < 4:
            return 1
        elif value <= 8:
            return 2
        else:
            return 3
    elif name == "Debtors Turnover Ratio":
        if value < 6:
            return 1
        elif value <= 10:
            return 2
        else:
            return 3
    elif name == "OCF to Total Debt Ratio":
        if value < 0.1:
            return 1
        elif value <= 0.2:
            return 2
        else:
            return 3
    else:
        return 2  # default fallback


# Category weights (Cash Flow ratio grouped under Solvency per the brief)
CATEGORY_WEIGHTS = {
    "Liquidity": 0.25,
    "Solvency": 0.30,
    "Profitability": 0.25,
    "Efficiency": 0.20,
}

# Compute score for every ratio, every year -> {ratio_name: {year: score}}
ratio_scores = {}
for ratio_name, (func, category) in RATIO_FUNCTIONS.items():
    ratio_scores[ratio_name] = {}
    for year in years:
        value = computed_ratios[ratio_name][year]
        ratio_scores[ratio_name][year] = score_ratio(ratio_name, value)


def composite_risk_score(year):
    """Weighted average of category scores, scaled to 0-100."""
    category_totals = {cat: [] for cat in CATEGORY_WEIGHTS}
    for ratio_name, (func, category) in RATIO_FUNCTIONS.items():
        category_totals[category].append(ratio_scores[ratio_name][year])

    weighted_sum = 0
    for category, scores in category_totals.items():
        avg_category_score = sum(scores) / len(scores)  # scale 1-3
        weighted_sum += avg_category_score * CATEGORY_WEIGHTS[category]

    # weighted_sum is on a 1-3 scale; rescale to 0-100
    scaled_score = round(((weighted_sum - 1) / (3 - 1)) * 100, 1)
    return scaled_score


def risk_band(score):
    if score <= 40:
        return "High Risk"
    elif score <= 70:
        return "Moderate Risk"
    else:
        return "Low Risk"


composite_scores = {year: composite_risk_score(year) for year in years}
composite_bands = {year: risk_band(composite_scores[year]) for year in years}


# ---------------------------------------------------------------------------
# TASK 4: OUTPUT / REPORTING
# ---------------------------------------------------------------------------

def trend_arrow(name, y1_val, y2_val):
    """Arrow direction; for ratios where LOWER is better (Debt-Equity),
    a decrease should show as improving (up arrow is used generically
    here to mean 'value increased'; interpretation noted separately)."""
    if y2_val > y1_val:
        return "↑"
    elif y2_val < y1_val:
        return "↓"
    else:
        return "→"


def print_ratio_table():
    print("=" * 100)
    print(f"{'RATIO TABLE - Trident Engineering Pvt. Ltd.':^100}")
    print("=" * 100)
    header = f"{'Ratio':30}" + "".join(f"{y:>18}" for y in years) + f"{'Trend':>10}"
    print(header)
    print("-" * 100)
    for ratio_name in RATIO_FUNCTIONS:
        vals = [computed_ratios[ratio_name][y] for y in years]
        arrow = trend_arrow(ratio_name, vals[0], vals[-1])
        row = f"{ratio_name:30}" + "".join(f"{v:>18}" for v in vals) + f"{arrow:>10}"
        print(row)
    print("=" * 100)
    print()


def print_risk_scoring_table():
    print("=" * 100)
    print(f"{'RISK SCORING TABLE (1=High Risk, 2=Moderate, 3=Low Risk)':^100}")
    print("=" * 100)
    header = f"{'Ratio':30}{'Category':15}" + "".join(f"{y:>15}" for y in years) + f"{'Weight':>10}"
    print(header)
    print("-" * 100)
    for ratio_name, (func, category) in RATIO_FUNCTIONS.items():
        scores = [ratio_scores[ratio_name][y] for y in years]
        weight_pct = f"{CATEGORY_WEIGHTS[category]*100:.0f}%"
        row = (f"{ratio_name:30}{category:15}"
               + "".join(f"{s:>15}" for s in scores)
               + f"{weight_pct:>10}")
        print(row)
    print("=" * 100)
    print()


def print_composite_scores():
    print("=" * 100)
    print(f"{'COMPOSITE BUSINESS RISK SCORE (Scale: 0-100)':^100}")
    print("=" * 100)
    for year in years:
        score = composite_scores[year]
        band = composite_bands[year]
        print(f"{year:15} : Score = {score:>6} / 100   |   Risk Band = {band}")
    print("=" * 100)
    print()


def generate_summary():
    first_score = composite_scores[years[0]]
    last_score = composite_scores[years[-1]]
    direction = "improving" if last_score > first_score else (
        "deteriorating" if last_score < first_score else "stable")

    # Identify weakest ratios in the latest year (score = 1, High Risk)
    latest_year = years[-1]
    weak_ratios = [name for name in RATIO_FUNCTIONS
                   if ratio_scores[name][latest_year] == 1]
    if not weak_ratios:
        weak_ratios = sorted(
            RATIO_FUNCTIONS,
            key=lambda n: ratio_scores[n][latest_year]
        )[:2]

    print("=" * 100)
    print(f"{'AUTO-GENERATED SUMMARY':^100}")
    print("=" * 100)
    print(f"Over the 3-year period ({years[0]} to {years[-1]}), the company's overall")
    print(f"business risk profile is {direction.upper()} "
          f"(Composite Score moved from {first_score} to {last_score}).")
    if weak_ratios:
        print(f"Key ratio(s) still flagged as a drag on the risk score in {latest_year}: "
              f"{', '.join(weak_ratios)}.")
    else:
        print(f"No ratios are currently flagged as High Risk in {latest_year}.")
    print("=" * 100)


# ---------------------------------------------------------------------------
# RUN THE FULL REPORT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print_ratio_table()
    print_risk_scoring_table()
    print_composite_scores()
    generate_summary()
