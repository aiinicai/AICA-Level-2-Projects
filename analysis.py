"""Calculations and charts for the Stage 1 comparative dashboard."""
from __future__ import annotations

import re
import numpy as np
import pandas as pd
import plotly.express as px


def indian_amount(value: float, unit: str = "₹") -> str:
    divisor = {"₹": 1, "₹ lakh": 100_000, "₹ crore": 10_000_000}[unit]
    suffix = {"₹": "", "₹ lakh": " lakh", "₹ crore": " crore"}[unit]
    return f"₹{value / divisor:,.2f}{suffix}"


def variance_analysis(current: pd.DataFrame, previous: pd.DataFrame) -> pd.DataFrame:
    """Compare TB movement amounts. Credit movements are presented as positive activity."""
    cols = ["Ledger Code", "Ledger", "Group", "Debit", "Credit"]
    c = current[cols].copy() if current is not None and not current.empty else pd.DataFrame(columns=cols)
    p = previous[cols].copy() if previous is not None and not previous.empty else pd.DataFrame(columns=cols)
    for frame in (c, p):
        frame["Movement"] = frame["Debit"].fillna(0).abs() + frame["Credit"].fillna(0).abs()
    c = c[["Ledger Code", "Ledger", "Group", "Movement"]].rename(columns={"Movement": "Current Period"})
    p = p[["Ledger Code", "Ledger", "Group", "Movement"]].rename(columns={"Movement": "Previous Period"})
    result = c.merge(p, on=["Ledger Code", "Ledger", "Group"], how="outer").fillna(0)
    result["Variance"] = result["Current Period"] - result["Previous Period"]
    result["Variance %"] = np.where(result["Previous Period"] != 0, result["Variance"] / result["Previous Period"] * 100, np.nan)
    return result.sort_values("Variance", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


def flag_variances(variance: pd.DataFrame, percent: float, amount: float) -> pd.DataFrame:
    output = variance.copy()
    output["Flag"] = ((output["Variance"].abs() >= amount) & (output["Variance %"].abs() >= percent)).map({True: "Review", False: ""})
    return output


def monthly_trend(daybook: pd.DataFrame, selected_ledgers: list[str]) -> pd.DataFrame:
    data = daybook[daybook["Ledger"].isin(selected_ledgers)].copy()
    data["Month"] = data["Date"].dt.to_period("M").astype(str)
    # Expenses/debits and income/credits are both shown as positive transaction values.
    return data.groupby(["Month", "Ledger"], as_index=False)["Amount"].sum()


def trend_chart(trend: pd.DataFrame):
    return px.line(trend, x="Month", y="Amount", color="Ledger", markers=True,
                   title="Month-wise activity", template="plotly_white", color_discrete_sequence=px.colors.qualitative.Bold)


def top_ledgers_chart(daybook: pd.DataFrame, count: int):
    totals = daybook.groupby("Ledger", as_index=False)["Amount"].sum().nlargest(count, "Amount")
    return px.bar(totals.sort_values("Amount"), x="Amount", y="Ledger", orientation="h", title=f"Top {count} ledgers by transaction value",
                  template="plotly_white", color="Amount", color_continuous_scale="Viridis")


def voucher_mix_chart(daybook: pd.DataFrame):
    mix = daybook.groupby("Voucher Type (Friendly)", as_index=False).size().rename(columns={"size": "Lines"})
    return px.pie(mix, names="Voucher Type (Friendly)", values="Lines", title="Voucher-type mix", hole=.4,
                  color_discrete_sequence=px.colors.qualitative.Set2)


def party_table(daybook: pd.DataFrame, count: int) -> pd.DataFrame:
    return (daybook[daybook["Party"].str.strip() != ""].groupby("Party", as_index=False)["Amount"].sum()
            .nlargest(count, "Amount"))


def group_summary(tb: pd.DataFrame) -> pd.DataFrame:
    return tb.groupby("Group", as_index=False).agg(Debit=("Debit", "sum"), Credit=("Credit", "sum"), Closing=("Closing", "sum"))

# --- STAGE 2: EXCEPTION TESTS ---

def test_round_amounts(df: pd.DataFrame, thresholds: list[int]) -> pd.DataFrame:
    results = []
    for t in sorted(set(thresholds)):
        if t <= 0:
            continue
        hits = df[(df["Amount"] > 0) & (df["Amount"] % t == 0)].copy()
        hits["Exception"] = f"Multiple of {t:,}"
        results.append(hits)
    return pd.concat(results).drop_duplicates(subset=["Row ID"], keep="last") if results else pd.DataFrame()

def test_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Flag weekend entries and entries in the last five days of month, quarter, or year."""
    result = df.copy()
    if result.empty:
        result["Exception"] = pd.Series(dtype="object")
        return result

    dates = pd.to_datetime(result["Date"], errors="coerce")
    labels = pd.Series("", index=result.index, dtype="object")
    labels.loc[dates.dt.weekday >= 5] = "Weekend Entry"

    month_end = dates.dt.day > (dates.dt.days_in_month - 5)
    quarter_end = month_end & dates.dt.month.isin([3, 6, 9, 12])
    year_end = month_end & (dates.dt.month == 12)

    for mask, label in (
        (month_end, "Month-End Entry"),
        (quarter_end, "Quarter-End Entry"),
        (year_end, "Year-End Entry"),
    ):
        labels.loc[mask] = labels.loc[mask].map(
            lambda value: f"{value}, {label}" if value else label
        )

    result["Exception"] = labels
    return result.loc[result["Exception"] != ""].copy()


def test_narrations(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    """Flag blank/short narrations and narrations containing selected keywords."""
    df = df.copy()

    narration = df["Narration"].fillna("").astype(str).str.strip()

    # Blank or short narration
    blank_mask = (narration == "") | (narration.str.len() < 5)

    # Ignore empty keywords and escape special regex characters
    clean_keywords = [
        str(k).strip()
        for k in keywords
        if str(k).strip()
    ]

    if clean_keywords:
        pattern = "|".join(
            re.escape(k) for k in clean_keywords
        )
        keyword_mask = narration.str.contains(
            pattern, case=False, na=False, regex=True
        )
    else:
        keyword_mask = pd.Series(False, index=df.index)

    hits = df.loc[blank_mask | keyword_mask].copy()    

    blank_hits = blank_mask.loc[hits.index]
    keyword_hits = keyword_mask.loc[hits.index]

    hits["Exception"] = np.select(
        [blank_hits, keyword_hits],
        ["Blank/Short Narration", "Keyword Hit"],
        default="Narration Review"
    )

    return hits

def test_thresholds(
    df: pd.DataFrame,
    cash_limit: float,
    audit_limit: float
) -> pd.DataFrame:
    """
    Flag cash transactions above the cash limit and transactions
    falling within 5% below the audit threshold.
    """
    df = df.copy()

    # Identify cash ledger entries safely, including missing ledger names
    cash_ledgers = ["cash", "petty cash"]
    is_cash = df["Ledger"].fillna("").astype(str).str.contains(
        "|".join(cash_ledgers),
        case=False,
        na=False,
        regex=True
    )

    # Cash transactions exceeding the cash limit
    over_cash = is_cash & (df["Amount"] > cash_limit)

    # Transactions within 5% below the audit threshold
    just_under = (
        (df["Amount"] >= audit_limit * 0.95)
        & (df["Amount"] < audit_limit)
    )

    # Filter first, then create labels using matching row indexes
    hits = df.loc[over_cash | just_under].copy()

    # Recalculate conditions on the filtered rows
    cash_hits = (
        hits["Ledger"].fillna("").astype(str).str.contains(
            "|".join(cash_ledgers),
            case=False,
            na=False,
            regex=True
        )
        & (hits["Amount"] > cash_limit)
    )

    hits["Exception"] = np.where(
        cash_hits,
        f"Cash > {cash_limit:,.2f}",
        f"Just below {audit_limit:,.2f}"
    )

    return hits


def test_benford(df: pd.DataFrame):
    """Compare first-digit frequencies of positive amounts with Benford's law.

    Returns (digit_summary, Plotly figure), as expected by the Streamlit app.
    """
    amounts = pd.to_numeric(df.get("Amount", pd.Series(dtype=float)), errors="coerce")
    amounts = amounts[amounts > 0].dropna()
    expected = np.array([np.log10(1 + 1 / digit) * 100 for digit in range(1, 10)])

    if amounts.empty:
        observed = np.zeros(9, dtype=float)
    else:
        first_digits = amounts.map(
            lambda value: next((int(char) for char in str(abs(value)) if char.isdigit() and char != "0"), 0)
        )
        first_digits = first_digits[first_digits.between(1, 9)]
        counts = first_digits.value_counts().reindex(range(1, 10), fill_value=0)
        observed = counts.to_numpy(dtype=float) / max(len(first_digits), 1) * 100

    summary = pd.DataFrame({
        "First Digit": range(1, 10),
        "Observed %": observed,
        "Benford Expected %": expected,
    })
    plot_data = summary.melt(
        id_vars="First Digit", var_name="Distribution", value_name="Percent"
    )
    fig = px.bar(
        plot_data, x="First Digit", y="Percent", color="Distribution",
        barmode="group", title="First-digit distribution vs Benford's Law",
        template="plotly_white",
    )
    return summary, fig


def test_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flag transactions belonging to ledger-month combinations
    whose monthly total exceeds the ledger mean by more than
    two standard deviations.
    """
    df = df.copy()

    # Ensure the date column is usable
    df["Month"] = pd.to_datetime(df["Date"]).dt.to_period("M")

    # Calculate monthly totals per ledger
    monthly = (
        df.groupby(["Ledger", "Month"], dropna=False)["Amount"]
        .sum()
        .reset_index()
    )

    # Calculate each ledger's monthly mean and standard deviation
    stats = (
        monthly.groupby("Ledger", dropna=False)["Amount"]
        .agg(["mean", "std"])
        .reset_index()
    )

    monthly = monthly.merge(stats, on="Ledger", how="left")

    # A spike requires a valid standard deviation
    spike_mask = (
        monthly["std"].notna()
        & (monthly["Amount"] > monthly["mean"] + 2 * monthly["std"])
    )

    spikes = monthly.loc[spike_mask, ["Ledger", "Month"]].drop_duplicates()

    # Return only rows belonging to flagged ledger-month combinations
    flagged = df.merge(
        spikes.assign(_spike=True),
        on=["Ledger", "Month"],
        how="inner"
    )

    flagged["Exception"] = "Monthly Spike Detected"

    return flagged.drop(columns=["_spike"], errors="ignore")
