
import pandas as pd
import plotly.express as px
import streamlit as st

# ==============================
# Load Data (AUTO delimiter detect)
# ==============================
file_path = "20apr26screener.csv"
df = pd.read_csv(file_path, sep=None, engine='python')

# ==============================
# Clean Column Names
# ==============================
df.columns = df.columns.str.strip()

# ==============================
# Column Mapping
# ==============================
name_col = "Funds"
category_col = "Category"
rating_col = "RupeeVestRating"

return_cols = [
    "Return (%)1 mo",
    "Return (%)3 mo",
    "Return (%)6 mo",
    "Return (%)1 yr",
    "Return (%)2 yrs",
    "Return (%)3 yrs",
    "Return (%)5 yrs",
    "Return (%)10 yrs"
]

risk_col = "Standard Deviation"
expense_col = "ExpenseRatio (%)"

# ==============================
# CLEAN RETURN COLUMNS (CRITICAL FIX)
# ==============================
for col in return_cols:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace('%', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors='coerce')

# ==============================
# CLEAN EXPENSE RATIO
# ==============================
if expense_col in df.columns:
    df[expense_col] = (
        df[expense_col]
        .astype(str)
        .str.replace('%', '', regex=False)
    )
    df[expense_col] = pd.to_numeric(df[expense_col], errors='coerce')

# ==============================
# CLEAN RATING COLUMN
# ==============================
if rating_col in df.columns:
    df[rating_col] = df[rating_col].astype(str).str.extract('(\d+)')
    df[rating_col] = pd.to_numeric(df[rating_col], errors='coerce')
    
    
   # ==============================
# CLEAN AUM COLUMN (CRITICAL FIX)
# ==============================
aum_col = "AUM(in Rs. cr)"

if aum_col in df.columns:
    df[aum_col] = (
        df[aum_col]
        .astype(str)
        .str.replace(',', '', regex=False)   # remove commas
        .str.replace('₹', '', regex=False)   # remove rupee symbol if any
        .str.strip()
    )
    df[aum_col] = pd.to_numeric(df[aum_col], errors='coerce')

# ==============================
# CLEAN RISK COLUMN
# ==============================
risk_col = "Standard Deviation"

if risk_col in df.columns:
    df[risk_col] = pd.to_numeric(df[risk_col], errors='coerce')

# ==============================
# Streamlit Setup
# ==============================
st.set_page_config(page_title="Mutual Fund Dashboard", layout="wide")

st.title("📊 Mutual Fund Advisory Dashboard")

# ==============================
# Sidebar Filters
# ==============================

# Return selector
selected_return = st.sidebar.selectbox(
    "Select Return Period",
    return_cols,
    index=3  # default 1 yr
)

# Category filter
categories = df[category_col].dropna().unique()
selected_categories = st.sidebar.multiselect(
    "Select Category",
    categories,
    default=categories
)

filtered_df = df[df[category_col].isin(selected_categories)]

# Rating filter
min_rating = st.sidebar.selectbox("Minimum Rating", [0,1,2,3,4,5], index=3)

filtered_df = filtered_df[
    filtered_df[rating_col].fillna(0) >= min_rating
]

# ==============================
# Metrics
# ==============================
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Funds", len(filtered_df))
col2.metric("Avg Return (%)", round(filtered_df[selected_return].mean(), 2))
col3.metric("Max Return (%)", round(filtered_df[selected_return].max(), 2))
col4.metric("Avg Expense Ratio", round(filtered_df[expense_col].mean(), 2))

# ==============================
# Top Funds
# ==============================
st.subheader("🏆 Top 10 Performing Funds")

top_funds = filtered_df.sort_values(by=selected_return, ascending=False).head(10)

fig_top = px.bar(
    top_funds,
    x=selected_return,
    y=name_col,
    orientation='h',
    color=selected_return,
    title=f"Top 10 Funds ({selected_return})"
)

st.plotly_chart(fig_top, use_container_width=True)

# ==============================
# Category Analysis
# ==============================
st.subheader("📊 Category-wise Returns")

cat_avg = filtered_df.groupby(category_col)[selected_return].mean().reset_index()

fig_cat = px.bar(
    cat_avg,
    x=category_col,
    y=selected_return,
    color=selected_return,
    title=f"Category Returns ({selected_return})"
)

st.plotly_chart(fig_cat, use_container_width=True)

# ==============================
# Risk vs Return
# ==============================
st.subheader("⚖️ Risk vs Return Analysis")

scatter_df = filtered_df.dropna(subset=[risk_col, selected_return, aum_col])

fig_scatter = px.scatter(
    scatter_df,
    x=risk_col,
    y=selected_return,
    size=aum_col,
    color=category_col,
    hover_data=[name_col, expense_col, rating_col],
    title="Risk vs Return (Bubble = AUM)"
)

st.plotly_chart(fig_scatter, use_container_width=True)
# ==============================
# SORTINO VS RETURN CHART
# ==============================

st.subheader("📊 Sortino vs Return (Risk-Adjusted Performance)")

sortino_col = "Sortino"

# Ensure numeric conversion (IMPORTANT)
filtered_df[sortino_col] = pd.to_numeric(filtered_df[sortino_col], errors='coerce')
filtered_df[selected_return] = pd.to_numeric(filtered_df[selected_return], errors='coerce')

# Drop missing values
chart_df = filtered_df.dropna(subset=[sortino_col, selected_return])

# ==============================
# Scatter Plot
# ==============================
fig_sortino = px.scatter(
    chart_df,
    x=sortino_col,
    y=selected_return,
    color=category_col,
    size="AUM(in Rs. cr)",
    hover_data=[name_col, "Sharpe", "Standard Deviation"],
    title=f"Sortino vs Return ({selected_return})"
)

st.plotly_chart(fig_sortino, use_container_width=True)
# Add quadrant lines (average)
avg_return = chart_df[selected_return].mean()
avg_sortino = chart_df[sortino_col].mean()

fig_sortino.add_hline(y=avg_return, line_dash="dash")
fig_sortino.add_vline(x=avg_sortino, line_dash="dash")

st.plotly_chart(fig_sortino, use_container_width=True)

# ==============================
# Multi-period Comparison
# ==============================
st.subheader("📈 Top 5 Funds Across Time")

top5 = filtered_df.sort_values(by=selected_return, ascending=False).head(5)

comparison_df = top5[[name_col] + return_cols].set_index(name_col).T

fig_line = px.line(
    comparison_df,
    markers=True,
    title="Performance Across Time Periods"
)

st.plotly_chart(fig_line, use_container_width=True)

# ==============================
# Expense vs Return
# ==============================
st.subheader("💸 Expense Ratio vs Return")

fig_exp = px.scatter(
    filtered_df,
    x=expense_col,
    y=selected_return,
    color=category_col,
    hover_data=[name_col],
    title="Expense vs Return"
)

st.plotly_chart(fig_exp, use_container_width=True)
# ==============================
# CLEAN FINANCIAL RATIO COLUMNS
# ==============================

numeric_cols = [
    "Sharpe",
    "Sortino",
    "Alpha",
    "Beta",
    "Standard Deviation",
    "PE Ratio",
    "PB Ratio",
    "Turnover Ratio (%)",
    "Avg. Market Cap(in Rs. cr)"
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(',', '', regex=False)
            .str.replace('%', '', regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors='coerce')
# ==============================
# LONG-TERM RECOMMENDATION ENGINE
# ==============================

st.subheader("🧠 Long-Term Investment Recommendations (5–10 Years)")

rec_df = filtered_df.copy()

# Use long-term return columns
long_term_cols = ["Return (%)3 yrs", "Return (%)5 yrs", "Return (%)10 yrs"]

# Drop missing important data
rec_df = rec_df.dropna(subset=long_term_cols + [risk_col, rating_col, expense_col, "Sharpe"])

# ==============================
# Create Composite Return (Long-term focus)
# ==============================
rec_df["long_term_return"] = (
    0.4 * rec_df["Return (%)5 yrs"] +
    0.3 * rec_df["Return (%)3 yrs"] +
    0.3 * rec_df["Return (%)10 yrs"]
)

# ==============================
# Normalize Function
# ==============================
def normalize(series):
    series = pd.to_numeric(series, errors='coerce')
    
    # Handle all NaN or constant values
    if series.dropna().empty or series.max() == series.min():
        return pd.Series([0]*len(series), index=series.index)
    
    return (series - series.min()) / (series.max() - series.min())

# ==============================
# Create Scores
# ==============================
rec_df["return_score"] = normalize(rec_df["long_term_return"])
rec_df["sharpe_score"] = normalize(rec_df["Sharpe"])
rec_df["risk_score"] = 1 - normalize(rec_df[risk_col])   # lower risk better
rec_df["expense_score"] = 1 - normalize(rec_df[expense_col])
rec_df["rating_score"] = rec_df[rating_col] / 5

# ==============================
# Final Score (Long-term focused weights)
# ==============================
rec_df["final_score"] = (
    0.30 * rec_df["return_score"] +
    0.25 * rec_df["sharpe_score"] +
    0.20 * rec_df["risk_score"] +
    0.15 * rec_df["rating_score"] +
    0.10 * rec_df["expense_score"]
)

# ==============================
# Classification (BUY / HOLD / AVOID)
# ==============================
rec_df["Recommendation"] = rec_df["final_score"].apply(
    lambda x: "🟢 BUY" if x > 0.75 else ("🟡 HOLD" if x > 0.55 else "🔴 AVOID")
)

# ==============================
# Top Funds
# ==============================
top_recommendations = rec_df.sort_values(by="final_score", ascending=False).head(7)

# ==============================
# Display Table
# ==============================
st.write("### 🏆 Best Funds for Long-Term Investing")

st.dataframe(
    top_recommendations[
        [
            name_col,
            category_col,
            "long_term_return",
            "Sharpe",
            risk_col,
            expense_col,
            rating_col,
            "final_score",
            "Recommendation"
        ]
    ].round(2)
)

# ==============================
# Visualization
# ==============================
fig = px.bar(
    top_recommendations,
    x="final_score",
    y=name_col,
    color="Recommendation",
    orientation='h',
    title="Top Long-Term Investment Funds"
)

st.plotly_chart(fig, use_container_width=True)
# ==============================
# Raw Data
# ==============================
st.subheader("📁 Raw Data")
st.dataframe(filtered_df)

# ==============================
# PORTFOLIO ALLOCATOR
# ==============================

st.subheader("📊 Portfolio Allocator (Client-Ready)")

# ==============================
# User Inputs
# ==============================
investment_amount = st.number_input("💰 Investment Amount (₹)", value=100000, step=5000)

risk_profile = st.selectbox(
    "Select Risk Profile",
    ["Conservative", "Moderate", "Aggressive"]
)

# ==============================
# Select Top Funds
# ==============================
portfolio_df = rec_df.sort_values(by="final_score", ascending=False).copy()

# Ensure diversification: max 2 funds per category
portfolio_df["rank_in_category"] = portfolio_df.groupby(category_col)["final_score"].rank(ascending=False)
portfolio_df = portfolio_df[portfolio_df["rank_in_category"] <= 2]

# Take top 5–7 funds
portfolio_df = portfolio_df.head(6)

# ==============================
# Allocation Logic
# ==============================

if risk_profile == "Conservative":
    weights = [0.25, 0.20, 0.18, 0.15, 0.12, 0.10]

elif risk_profile == "Moderate":
    weights = [0.22, 0.20, 0.18, 0.16, 0.14, 0.10]

else:  # Aggressive
    weights = [0.20, 0.18, 0.17, 0.16, 0.15, 0.14]

# Adjust if fewer funds
weights = weights[:len(portfolio_df)]

# Normalize weights to 100%
weights = [w / sum(weights) for w in weights]

portfolio_df["Weight"] = weights

# ==============================
# Calculate Investment Allocation
# ==============================
portfolio_df["Investment (₹)"] = portfolio_df["Weight"] * investment_amount

# Expected return (based on selected return period)
portfolio_df["Expected Return (₹)"] = (
    portfolio_df["Investment (₹)"] * portfolio_df[selected_return] / 100
)

# ==============================
# Display Portfolio
# ==============================
st.write("### 🧾 Recommended Portfolio")

st.dataframe(
    portfolio_df[
        [
            name_col,
            category_col,
            selected_return,
            "Weight",
            "Investment (₹)",
            "Expected Return (₹)"
        ]
    ].round(2)
)

# ==============================
# Portfolio Summary
# ==============================
total_expected_return = portfolio_df["Expected Return (₹)"].sum()

st.metric("📈 Expected Annual Return (₹)", round(total_expected_return, 2))

# ==============================
# Visualization
# ==============================
fig_pie = px.pie(
    portfolio_df,
    values="Investment (₹)",
    names=name_col,
    title="Portfolio Allocation"
)

st.plotly_chart(fig_pie, use_container_width=True)
# ==============================
# SHORT-TERM MOMENTUM PORTFOLIO
# ==============================

st.subheader("⚡ Short-Term Momentum Portfolio (1–6 Months)")

# ==============================
# User Inputs
# ==============================
investment_amount_st = st.number_input(
    "💰 Investment Amount for Momentum (₹)",
    value=100000,
    step=5000,
    key="short_term_amt"
)

top_n = st.slider("Number of Funds", 3, 8, 5)

# ==============================
# Prepare Data
# ==============================
momentum_df = filtered_df.copy()

momentum_cols = ["Return (%)1 mo", "Return (%)3 mo", "Return (%)6 mo"]

momentum_df = momentum_df.dropna(subset=momentum_cols + ["Sharpe", risk_col])
# ==============================
# FORCE NUMERIC (FINAL SAFETY)
# ==============================

momentum_df["Sharpe"] = pd.to_numeric(momentum_df["Sharpe"], errors='coerce')
momentum_df[risk_col] = pd.to_numeric(momentum_df[risk_col], errors='coerce')

for col in ["Return (%)1 mo", "Return (%)3 mo", "Return (%)6 mo"]:
    momentum_df[col] = pd.to_numeric(momentum_df[col], errors='coerce')

# ==============================
# Momentum Score
# ==============================
momentum_df["momentum_return"] = (
    0.5 * momentum_df["Return (%)1 mo"] +
    0.3 * momentum_df["Return (%)3 mo"] +
    0.2 * momentum_df["Return (%)6 mo"]
)

# Normalize function (safe)
def normalize(series):
    if series.max() == series.min():
        return pd.Series([0]*len(series), index=series.index)
    return (series - series.min()) / (series.max() - series.min())

momentum_df["momentum_score"] = normalize(momentum_df["momentum_return"])
momentum_df["sharpe_score"] = normalize(momentum_df["Sharpe"])
momentum_df["risk_score"] = 1 - normalize(momentum_df[risk_col])

# Final momentum score
momentum_df["final_momentum_score"] = (
    0.6 * momentum_df["momentum_score"] +
    0.25 * momentum_df["sharpe_score"] +
    0.15 * momentum_df["risk_score"]
)

# ==============================
# Select Top Momentum Funds
# ==============================
top_momentum = momentum_df.sort_values(
    by="final_momentum_score", ascending=False
).head(top_n)

# ==============================
# Allocation (Equal + Slight Tilt)
# ==============================
weights = [1/len(top_momentum)] * len(top_momentum)

top_momentum["Weight"] = weights

top_momentum["Investment (₹)"] = (
    top_momentum["Weight"] * investment_amount_st
)

top_momentum["Expected Short-Term Return (₹)"] = (
    top_momentum["Investment (₹)"] *
    top_momentum["Return (%)3 mo"] / 100
)

# ==============================
# Display Portfolio
# ==============================
st.write("### ⚡ Momentum Portfolio")

st.dataframe(
    top_momentum[
        [
            name_col,
            category_col,
            "Return (%)1 mo",
            "Return (%)3 mo",
            "Return (%)6 mo",
            "Sharpe",
            "final_momentum_score",
            "Investment (₹)",
            "Expected Short-Term Return (₹)"
        ]
    ].round(2)
)

# ==============================
# Summary
# ==============================
total_return_st = top_momentum["Expected Short-Term Return (₹)"].sum()

st.metric("⚡ Expected Short-Term Return (₹)", round(total_return_st, 2))

# ==============================
# Visualization
# ==============================
fig_momentum = px.bar(
    top_momentum,
    x="final_momentum_score",
    y=name_col,
    orientation='h',
    title="Top Momentum Funds"
)

st.plotly_chart(fig_momentum, use_container_width=True)

fig_pie_st = px.pie(
    top_momentum,
    values="Investment (₹)",
    names=name_col,
    title="Momentum Portfolio Allocation"
)

st.plotly_chart(fig_pie_st, use_container_width=True)
# ==============================
# FUND MANAGER ANALYSIS ENGINE
# ==============================

st.subheader("👨‍💼 Fund Manager Ranking (Based on Your Data)")

fm_col = "Fund Manager"

# Ensure required columns are numeric
cols_to_clean = [
    "Return (%)3 yrs",
    "Return (%)5 yrs",
    "Return (%)10 yrs",
    "Sharpe",
    "Standard Deviation",
    "ExpenseRatio (%)",
    "RupeeVestRating"
]

for col in cols_to_clean:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Drop rows with missing key data
fm_df = df.dropna(subset=[
    fm_col,
    "Return (%)3 yrs",
    "Return (%)5 yrs",
    "Return (%)10 yrs",
    "Sharpe",
    "Standard Deviation"
])

# ==============================
# Create Long-Term Return Score
# ==============================
fm_df["long_term_return"] = (
    0.4 * fm_df["Return (%)5 yrs"] +
    0.3 * fm_df["Return (%)3 yrs"] +
    0.3 * fm_df["Return (%)10 yrs"]
)

# ==============================
# Normalize Function
# ==============================
def normalize(series):
    series = pd.to_numeric(series, errors='coerce')
    if series.max() == series.min():
        return pd.Series([0]*len(series), index=series.index)
    return (series - series.min()) / (series.max() - series.min())

# ==============================
# Create Scores
# ==============================
fm_df["return_score"] = normalize(fm_df["long_term_return"])
fm_df["sharpe_score"] = normalize(fm_df["Sharpe"])
fm_df["risk_score"] = 1 - normalize(fm_df["Standard Deviation"])
fm_df["expense_score"] = 1 - normalize(fm_df["ExpenseRatio (%)"])
fm_df["rating_score"] = fm_df["RupeeVestRating"] / 5

# ==============================
# Final Score per Fund
# ==============================
fm_df["final_score"] = (
    0.30 * fm_df["return_score"] +
    0.25 * fm_df["sharpe_score"] +
    0.20 * fm_df["risk_score"] +
    0.15 * fm_df["rating_score"] +
    0.10 * fm_df["expense_score"]
)

# ==============================
# Aggregate by Fund Manager
# ==============================
fm_summary = fm_df.groupby(fm_col).agg({
    "final_score": "mean",
    "long_term_return": "mean",
    "Sharpe": "mean",
    "Standard Deviation": "mean",
    "Funds": "count"
}).reset_index()

fm_summary = fm_summary.rename(columns={"Funds": "No_of_Funds"})

# Rank managers
fm_summary = fm_summary.sort_values(by="final_score", ascending=False)

# ==============================
# Display Top Managers
# ==============================
st.write("### 🏆 Top Fund Managers")

st.dataframe(
    fm_summary.head(10).round(2)
)

# ==============================
# Visualization
# ==============================
fig_fm = px.bar(
    fm_summary.head(10),
    x="final_score",
    y=fm_col,
    orientation='h',
    title="Top Fund Managers (Data-Based Ranking)"
)

st.plotly_chart(fig_fm, use_container_width=True)
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ==============================
# EFFICIENT FRONTIER (FINAL)
# ==============================

st.subheader("📈 Efficient Frontier (Portfolio Optimization)")

# ------------------------------
# Prepare Data
# ------------------------------
ef_df = filtered_df.copy()

# Ensure numeric
ef_df[selected_return] = pd.to_numeric(ef_df[selected_return], errors='coerce')
ef_df[risk_col] = pd.to_numeric(ef_df[risk_col], errors='coerce')

# Drop missing
ef_df = ef_df.dropna(subset=[selected_return, risk_col])

# Limit top funds (stability)
ef_df = ef_df.sort_values(by=selected_return, ascending=False).head(15)

returns = ef_df[selected_return].values / 100
risks = ef_df[risk_col].values / 100
fund_names = ef_df[name_col].values

# ------------------------------
# Simulation
# ------------------------------
num_portfolios = 3000
results = []

for _ in range(num_portfolios):
    weights = np.random.random(len(returns))
    weights /= np.sum(weights)

    port_return = np.sum(weights * returns)
    port_risk = np.sqrt(np.sum((weights * risks) ** 2))

    sharpe = port_return / port_risk if port_risk != 0 else 0

    results.append({
        "Return": port_return,
        "Risk": port_risk,
        "Sharpe": sharpe,
        "Weights": weights
    })

ef_results = pd.DataFrame(results)

# ------------------------------
# Best Portfolio
# ------------------------------
best_idx = ef_results["Sharpe"].idxmax()
best_port = ef_results.loc[best_idx]
best_weights = best_port["Weights"]

# ------------------------------
# Plot Frontier
# ------------------------------
fig = px.scatter(
    ef_results,
    x="Risk",
    y="Return",
    color="Sharpe",
    title="Efficient Frontier (Simulated)"
)

fig.add_scatter(
    x=[best_port["Risk"]],
    y=[best_port["Return"]],
    mode="markers",
    marker=dict(size=12, color="red"),
    name="Max Sharpe"
)

st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# Portfolio Summary
# ------------------------------
st.write("### 🏆 Optimal Portfolio Summary")

st.write({
    "Expected Return (%)": round(best_port["Return"] * 100, 2),
    "Risk (%)": round(best_port["Risk"] * 100, 2),
    "Sharpe Ratio": round(best_port["Sharpe"], 2)
})

# ------------------------------
# Allocation Table
# ------------------------------
alloc_df = pd.DataFrame({
    "Fund": fund_names,
    "Weight (%)": best_weights * 100
})

# Remove very small weights
alloc_df = alloc_df[alloc_df["Weight (%)"] > 2]
alloc_df = alloc_df.sort_values(by="Weight (%)", ascending=False)

# ------------------------------
# Investment Input (UNIQUE KEY)
# ------------------------------
investment = st.number_input(
    "💰 Investment Amount (₹)",
    value=100000,
    step=5000,
    key="ef_investment_final"
)

alloc_df["Investment (₹)"] = alloc_df["Weight (%)"] / 100 * investment

# ------------------------------
# Display Allocation
# ------------------------------
st.write("### 📊 Recommended Portfolio Allocation")
st.dataframe(alloc_df.round(2))

# ------------------------------
# Pie Chart
# ------------------------------
fig_pie = px.pie(
    alloc_df,
    values="Investment (₹)",
    names="Fund",
    title="Portfolio Allocation"
)

st.plotly_chart(fig_pie, use_container_width=True)
