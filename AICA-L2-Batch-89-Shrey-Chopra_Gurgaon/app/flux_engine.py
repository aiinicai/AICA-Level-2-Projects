"""
flux_engine.py
--------------
Core, UI-independent flux logic. No Flask, no Streamlit — this module can
be unit tested or reused on its own.

Design (v2):
- The user uploads TWO separate trial balance files — one for the prior
  period, one for the current period — instead of one combined file with
  a period column. Each file is a simple, flat extract:
      entity, line_item, amount
- The user works in one statement at a time: Income Statement OR Balance
  Sheet. Each has its own category vocabulary (see STATEMENT_CATEGORIES)
  and its own commentary framing (ai_commentary.py handles the wording;
  this module only decides magnitude and materiality).
- "Comparison type" is a LABEL the user picks to describe the relationship
  between the two uploaded periods (Month-over-Month, vs. Prior
  Quarter-End, vs. Prior Year-End, Year-over-Year Same Period). The
  variance math is identical regardless of label — the label only changes
  how the movement is described in commentary and on the exported report
  header, exactly as a real close calendar would frame the comparison.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import pandas as pd

REQUIRED_COLUMNS = ["entity", "line_item", "amount"]

MIN_DOLLAR_FLOOR = 1_000.0

STATEMENT_TYPES = {
    "income_statement": "Income Statement",
    "balance_sheet": "Balance Sheet",
}

# Category vocabulary shown to the user when they optionally tag lines by
# category (category is inferred from a `category` column if present,
# else every line falls into "Uncategorized" and gets neutral framing).
STATEMENT_CATEGORIES = {
    "income_statement": ["Revenue", "Cost of Sales", "Operating Expenses", "Other Income/Expense"],
    "balance_sheet": ["Assets", "Liabilities", "Equity"],
}

COMPARISON_TYPES = {
    "mom": {
        "label": "Month-over-Month",
        "phrase": "compared to the prior month",
        "short": "MoM",
    },
    "qoq_end": {
        "label": "Current Period vs. Prior Quarter-End",
        "phrase": "compared to the prior quarter-end balance",
        "short": "vs. Prior QE",
    },
    "yoy_end": {
        "label": "Current Period vs. Prior Year-End",
        "phrase": "compared to the prior year-end (opening) balance",
        "short": "vs. Prior YE",
    },
    "yoy_same": {
        "label": "Year-over-Year, Same Period",
        "phrase": "compared to the same period last year",
        "short": "YoY",
    },
}


@dataclass
class MaterialityThreshold:
    percent: float = 10.0


def load_period_file(file_like) -> pd.DataFrame:
    """Load one period's trial balance (entity, line_item, amount[, category])."""
    if hasattr(file_like, "filename") and file_like.filename.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(file_like)
    else:
        df = pd.read_csv(file_like)

    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required column(s): {missing}. Expected at least: {REQUIRED_COLUMNS} "
            "(an optional 'category' column is also supported)."
        )

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    if df["amount"].isna().any():
        bad = df[df["amount"].isna()]
        raise ValueError(f"Non-numeric amount values found in {len(bad)} row(s). Please clean the file and re-upload.")

    if "category" not in df.columns:
        df["category"] = "Uncategorized"
    df["category"] = df["category"].fillna("Uncategorized")

    df["entity"] = df["entity"].astype(str).str.strip()
    df["line_item"] = df["line_item"].astype(str).str.strip()

    return df[["entity", "category", "line_item", "amount"]]


def compute_flux(
    prior_df: pd.DataFrame,
    current_df: pd.DataFrame,
    threshold: MaterialityThreshold,
) -> pd.DataFrame:
    """Merge two period extracts on (entity, category, line_item) and compute variance."""
    prior = prior_df.groupby(["entity", "category", "line_item"], as_index=False)["amount"].sum()
    current = current_df.groupby(["entity", "category", "line_item"], as_index=False)["amount"].sum()

    merged = pd.merge(
        prior, current,
        on=["entity", "category", "line_item"],
        how="outer",
        suffixes=("_prior", "_current"),
    )
    merged["amount_prior"] = merged["amount_prior"].fillna(0.0)
    merged["amount_current"] = merged["amount_current"].fillna(0.0)

    merged["variance_usd"] = merged["amount_current"] - merged["amount_prior"]

    def pct_change(row):
        if row["amount_prior"] == 0:
            return 100.0 if row["amount_current"] != 0 else 0.0
        return (row["variance_usd"] / abs(row["amount_prior"])) * 100.0

    merged["variance_pct"] = merged.apply(pct_change, axis=1)

    merged["is_material"] = (merged["variance_usd"].abs() >= MIN_DOLLAR_FLOOR) & (
        merged["variance_pct"].abs() >= threshold.percent
    )

    # Severity tier — used by the commentary engine to pick tone/urgency
    def severity(row):
        if not row["is_material"]:
            return "none"
        if abs(row["variance_pct"]) >= threshold.percent * 3 or abs(row["variance_usd"]) >= 500_000:
            return "high"
        if abs(row["variance_pct"]) >= threshold.percent * 1.5:
            return "elevated"
        return "standard"

    merged["severity"] = merged.apply(severity, axis=1)

    merged["_abs_variance"] = merged["variance_usd"].abs()
    merged = merged.sort_values(by=["is_material", "_abs_variance"], ascending=[False, False]).drop(columns="_abs_variance")

    merged = merged.rename(columns={"amount_prior": "prior_amount", "amount_current": "current_amount"})

    # Stable row id — used by the review workflow to track status per line
    merged = merged.reset_index(drop=True)
    merged["row_id"] = merged.index.map(lambda i: f"r{i}")

    return merged[
        [
            "row_id", "entity", "category", "line_item",
            "prior_amount", "current_amount", "variance_usd", "variance_pct",
            "is_material", "severity",
        ]
    ]


def summarize_by_entity(flux_df: pd.DataFrame) -> pd.DataFrame:
    return (
        flux_df.groupby("entity")
        .agg(
            lines_reviewed=("line_item", "count"),
            material_flags=("is_material", "sum"),
            net_variance_usd=("variance_usd", "sum"),
        )
        .reset_index()
        .sort_values("material_flags", ascending=False)
    )
