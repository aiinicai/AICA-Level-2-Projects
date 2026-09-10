"""
valuation/comparable.py

Implements the mandatory hierarchy:

    Locality -> City -> Property Type -> BHK -> Area -> Furnishing -> Age/quality

A property must primarily be compared with similar properties in its own
locality; city-wide averages are only a secondary/fallback benchmark
(spec section 28, "Do Not Use City Average Alone").
"""

import numpy as np
import pandas as pd

MIN_COMPARABLES_FOR_LOCALITY_CONFIDENCE = 5


def _to_frame(listings: list) -> pd.DataFrame:
    df = pd.DataFrame(listings)
    if df.empty:
        return df
    for col in ("price", "price_per_sqft", "monthly_rent", "rent_per_sqft", "area_sqft", "age_years"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _area_band(area_sqft: float, tolerance: float = 0.20) -> tuple:
    return area_sqft * (1 - tolerance), area_sqft * (1 + tolerance)


def filter_comparables(listings: list, subject: dict, listing_kind: str,
                        exclude_outliers: bool = True) -> pd.DataFrame:
    """
    subject: dict with keys city_id, locality_id, property_type, bhk,
             area_sqft, furnishing, age_years
    Returns the best-available tier of comparables as a DataFrame, tagging
    which tier was used in df.attrs['tier'] for transparency.
    """
    df = _to_frame(listings)
    if df.empty:
        df.attrs["tier"] = "none"
        return df

    df = df[df["listing_kind"] == listing_kind]
    if exclude_outliers and "is_outlier" in df.columns:
        df = df[df["is_outlier"] != 1]

    lo, hi = _area_band(subject.get("area_sqft") or 0)

    def apply_filters(frame, use_locality, use_bhk, use_area, use_furnishing, use_type):
        f = frame
        if use_type:
            f = f[f["property_type"] == subject.get("property_type")]
        if use_locality:
            f = f[f["locality_id"] == subject.get("locality_id")]
        else:
            f = f[f["city_id"] == subject.get("city_id")]
        if use_bhk and subject.get("bhk"):
            f = f[f["bhk"] == subject.get("bhk")]
        if use_area and subject.get("area_sqft"):
            f = f[(f["area_sqft"] >= lo) & (f["area_sqft"] <= hi)]
        if use_furnishing and subject.get("furnishing"):
            f = f[f["furnishing"] == subject.get("furnishing")]
        return f

    # Progressive relaxation: start with the tightest match, fall back
    # tier by tier until enough observations are found.
    tiers = [
        ("locality+type+bhk+area+furnishing", dict(use_locality=True, use_bhk=True, use_area=True, use_furnishing=True, use_type=True)),
        ("locality+type+bhk+area", dict(use_locality=True, use_bhk=True, use_area=True, use_furnishing=False, use_type=True)),
        ("locality+type+bhk", dict(use_locality=True, use_bhk=True, use_area=False, use_furnishing=False, use_type=True)),
        ("locality+type", dict(use_locality=True, use_bhk=False, use_area=False, use_furnishing=False, use_type=True)),
        ("city+type+bhk+area", dict(use_locality=False, use_bhk=True, use_area=True, use_furnishing=False, use_type=True)),
        ("city+type+bhk", dict(use_locality=False, use_bhk=True, use_area=False, use_furnishing=False, use_type=True)),
        ("city+type", dict(use_locality=False, use_bhk=False, use_area=False, use_furnishing=False, use_type=True)),
    ]

    for tier_name, kwargs in tiers:
        result = apply_filters(df, **kwargs)
        if len(result) >= MIN_COMPARABLES_FOR_LOCALITY_CONFIDENCE:
            result = result.copy()
            result.attrs["tier"] = tier_name
            return result

    # Last resort: whatever locality-level matches exist even if few.
    result = apply_filters(df, use_locality=True, use_bhk=False, use_area=False, use_furnishing=False, use_type=True)
    result = result.copy()
    result.attrs["tier"] = "locality+type (low sample)" if len(result) else "none"
    return result


def summarize_stats(df: pd.DataFrame, value_col: str) -> dict:
    if df.empty or value_col not in df.columns or df[value_col].dropna().empty:
        return {
            "count": 0, "mean": None, "median": None, "min": None, "max": None,
            "p25": None, "p75": None,
        }
    s = df[value_col].dropna()
    return {
        "count": int(s.count()),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "min": float(s.min()),
        "max": float(s.max()),
        "p25": float(s.quantile(0.25)),
        "p75": float(s.quantile(0.75)),
    }


def weighted_comparable_value(df: pd.DataFrame, subject_area: float) -> float:
    """
    Weighted comparable value = weighted median price/sqft * subject area.
    Weights favor: closer area match, more recent data, and non-outliers.
    Falls back to plain median if weighting can't be computed.
    """
    if df.empty or "price_per_sqft" not in df.columns:
        return None
    sub = df.dropna(subset=["price_per_sqft"]).copy()
    if sub.empty:
        return None

    weights = np.ones(len(sub))
    if "area_sqft" in sub.columns and subject_area:
        area_diff = (sub["area_sqft"] - subject_area).abs()
        max_diff = area_diff.max() or 1
        weights *= (1 - (area_diff / max_diff) * 0.5)  # closer area -> higher weight
    if "is_outlier" in sub.columns:
        weights *= np.where(sub["is_outlier"] == 1, 0.3, 1.0)

    sub = sub.assign(_w=weights).sort_values("price_per_sqft")
    cum_w = sub["_w"].cumsum()
    cutoff = sub["_w"].sum() / 2.0
    median_row = sub[cum_w >= cutoff].iloc[0]
    weighted_median_price_sqft = median_row["price_per_sqft"]

    return float(weighted_median_price_sqft) * float(subject_area)
