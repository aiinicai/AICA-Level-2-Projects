"""
data/validators.py

Row-level and dataset-level validation / cleaning rules (see spec section
"Data Quality Rules"). Operates on plain dicts (one row) or pandas
DataFrames (a batch), and never mutates in place silently — it returns
(clean_df, rejected_df) so raw data is always preservable.
"""

import numpy as np
import pandas as pd

from config import (
    MIN_REALISTIC_AREA_SQFT, MAX_REALISTIC_AREA_SQFT,
    MIN_REALISTIC_RENT, MAX_REALISTIC_RENT,
    MIN_REALISTIC_PRICE, MAX_REALISTIC_PRICE,
    IQR_OUTLIER_MULTIPLIER,
)

RESIDENTIAL_TYPES = {"apartment", "independent house", "villa", "builder floor", "penthouse"}


def validate_row(row: dict) -> (bool, str):
    """Returns (is_valid, rejection_reason). Does not flag statistical outliers
    (that is a batch-level concern, see flag_outliers)."""

    if not row.get("city_id") and not row.get("city"):
        return False, "Missing city"
    if not row.get("locality_id") and not row.get("locality"):
        return False, "Missing locality"

    ptype = (row.get("property_type") or "").strip().lower()
    if not ptype:
        return False, "Missing property type"
    if ptype not in RESIDENTIAL_TYPES:
        return False, f"Non-residential or unrecognized property type: {ptype}"

    area = row.get("area_sqft")
    if area is None or area <= 0:
        return False, "Missing/zero area"
    if area < MIN_REALISTIC_AREA_SQFT or area > MAX_REALISTIC_AREA_SQFT:
        return False, f"Unrealistic area value: {area} sqft"

    kind = row.get("listing_kind")
    if kind == "sale":
        price = row.get("price")
        if price is None or price <= 0:
            return False, "Missing/zero sale price"
        if price < MIN_REALISTIC_PRICE or price > MAX_REALISTIC_PRICE:
            return False, f"Unrealistic sale price: {price}"
    elif kind == "rent":
        rent = row.get("monthly_rent")
        if rent is None or rent <= 0:
            return False, "Missing/zero rent"
        if rent < MIN_REALISTIC_RENT or rent > MAX_REALISTIC_RENT:
            return False, f"Unrealistic rent value: {rent}"
    else:
        return False, "listing_kind must be 'sale' or 'rent'"

    return True, ""


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Removes exact duplicate listings (same source/city/locality/bhk/area/price/rent)."""
    subset = [c for c in [
        "source_id", "city_id", "locality_id", "property_type", "bhk",
        "area_sqft", "listing_kind", "price", "monthly_rent",
    ] if c in df.columns]
    if not subset:
        return df
    return df.drop_duplicates(subset=subset, keep="first")


def flag_outliers(df: pd.DataFrame, value_col: str, group_cols=None) -> pd.DataFrame:
    """
    Adds/updates an `is_outlier` column using the IQR rule, computed
    WITHIN each (city, locality, bhk, listing_kind) group where possible,
    so a legitimately expensive locality doesn't get flagged just because
    it's expensive relative to the whole city.
    """
    df = df.copy()
    if "is_outlier" not in df.columns:
        df["is_outlier"] = 0
    if value_col not in df.columns:
        return df

    group_cols = group_cols or [c for c in ["city_id", "locality_id", "bhk", "listing_kind"] if c in df.columns]

    def _flag(group):
        vals = group[value_col].dropna()
        if len(vals) < 5:
            return group  # too few points to judge outliers reliably
        q1, q3 = vals.quantile(0.25), vals.quantile(0.75)
        iqr = q3 - q1
        lo = q1 - IQR_OUTLIER_MULTIPLIER * iqr
        hi = q3 + IQR_OUTLIER_MULTIPLIER * iqr
        mask = (group[value_col] < lo) | (group[value_col] > hi)
        group.loc[mask, "is_outlier"] = 1
        return group

    if group_cols:
        df = df.groupby(group_cols, group_keys=False, dropna=False).apply(_flag)
    else:
        df = _flag(df)
    return df


def winsorize(series: pd.Series, limits=(0.05, 0.05)) -> pd.Series:
    """Caps extreme values at the given lower/upper percentiles rather than
    dropping them — reduces the influence of extreme (but not necessarily
    invalid) values on averages."""
    lower = series.quantile(limits[0])
    upper = series.quantile(1 - limits[1])
    return series.clip(lower=lower, upper=upper)


def clean_dataframe(df: pd.DataFrame) -> (pd.DataFrame, pd.DataFrame):
    """
    Full cleaning pipeline for an imported batch.
    Returns (clean_df, rejected_df). `clean_df` still contains is_outlier
    flags (rows are NOT dropped for being outliers, only flagged, per spec:
    "Use robust statistical methods ... Outlier flags").
    """
    df = df.copy()
    valid_mask = []
    reasons = []
    for _, row in df.iterrows():
        ok, reason = validate_row(row.to_dict())
        valid_mask.append(ok)
        reasons.append(reason)
    df["is_valid"] = [1 if v else 0 for v in valid_mask]
    df["rejection_reason"] = reasons

    df = deduplicate(df)

    clean_df = df[df["is_valid"] == 1].copy()
    rejected_df = df[df["is_valid"] == 0].copy()

    if "price_per_sqft" in clean_df.columns:
        clean_df = flag_outliers(clean_df, "price_per_sqft")
    if "rent_per_sqft" in clean_df.columns:
        clean_df = flag_outliers(clean_df, "rent_per_sqft")

    return clean_df, rejected_df
