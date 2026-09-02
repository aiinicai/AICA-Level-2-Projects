"""
valuation/calculations.py

Top-level orchestrator: given a subject property + a Database handle,
runs the full pipeline described in the spec (sections 5-13, 19) and
returns a fully-populated ValuationResult plus supporting detail for
the GUI/report layers.
"""

from config import PRICE_BANDS, CITY_TARGET_YIELD, DEFAULT_TARGET_YIELD

from valuation import rental_yield as ry
from valuation import comparable as comp
from valuation import fair_value as fv
from valuation import scoring
from database.models import ValuationResult


def classify_price_band(premium_pct: float, bands=PRICE_BANDS) -> str:
    for lo, hi, label in bands:
        if lo <= premium_pct < hi:
            return label
    return "UNCLASSIFIED"


def run_valuation(property_input, db, city_name: str = None) -> dict:
    """
    property_input: database.models.PropertyInput (or dict with equivalent keys)
    db: database.database.Database
    city_name: used to look up a city-specific target rental yield; if not
               supplied, DEFAULT_TARGET_YIELD is used.

    Returns a dict: {
        "result": ValuationResult,
        "rent_stats": {...},
        "sale_stats": {...},
        "comparable_tier": str,
        "sources": [...],
        "adjustment_notes": [...],
    }
    """
    subject = property_input.__dict__ if hasattr(property_input, "__dict__") else dict(property_input)
    area = subject.get("builtup_area") or subject.get("carpet_area")

    # --- 1. Pull raw comparable pools -----------------------------------
    all_rent_listings = db.query_listings(
        city_id=subject.get("city_id"), listing_kind="rent", only_valid=True
    )
    all_sale_listings = db.query_listings(
        city_id=subject.get("city_id"), listing_kind="sale", only_valid=True
    )

    rent_df = comp.filter_comparables(all_rent_listings, {**subject, "area_sqft": area}, "rent")
    sale_df = comp.filter_comparables(all_sale_listings, {**subject, "area_sqft": area}, "sale")

    rent_stats = comp.summarize_stats(rent_df, "monthly_rent")
    sale_stats = comp.summarize_stats(sale_df, "price_per_sqft")

    market_rent_low = rent_stats["p25"] or subject.get("expected_rent") or 0
    market_rent_high = rent_stats["p75"] or subject.get("expected_rent") or 0
    market_rent_median = rent_stats["median"] or subject.get("expected_rent") or 0

    # --- 2. Three valuation methods --------------------------------------
    comparable_value = comp.weighted_comparable_value(sale_df, area) if area else None
    if comparable_value is None and sale_stats["median"] and area:
        comparable_value = sale_stats["median"] * area

    target_yield = CITY_TARGET_YIELD.get(city_name, DEFAULT_TARGET_YIELD)
    rent_for_cap = market_rent_median or subject.get("expected_rent")
    rental_cap_value = fv.rental_capitalization_value(rent_for_cap, target_yield) if rent_for_cap else None

    adjusted_val, adjustment_notes = fv.adjusted_value(comparable_value, subject)

    fair_low, fair_high, fair_mid = fv.estimate_fair_value_range(
        comparable_value, rental_cap_value, adjusted_val
    )

    # --- 3. Yield & price-to-rent on the SUBJECT's asking price -----------
    asking_price = subject.get("asking_price") or 0
    gross_yield = ry.gross_rental_yield(subject.get("expected_rent") or rent_for_cap or 0, asking_price)
    total_investment = asking_price + subject.get("stamp_duty", 0) + subject.get("brokerage", 0) + subject.get("renovation_cost", 0)
    net_yield = ry.net_rental_yield(
        subject.get("expected_rent") or rent_for_cap or 0,
        total_investment,
        maintenance_month=subject.get("maintenance_month", 0),
        property_tax_year=subject.get("property_tax_year", 0),
        insurance_year=subject.get("insurance_year", 0),
        vacancy_pct=subject.get("vacancy_pct", 0),
    )
    price_to_rent = ry.price_to_rent_ratio(asking_price, subject.get("expected_rent") or rent_for_cap or 0)

    # --- 4. Premium/discount vs fair value & verdict -----------------------
    if fair_mid:
        premium_pct = ((asking_price - fair_mid) / fair_mid) * 100
    else:
        premium_pct = 0.0
    verdict = classify_price_band(premium_pct)

    # --- 5. Confidence score -----------------------------------------------
    tier = sale_df.attrs.get("tier", "none") if hasattr(sale_df, "attrs") else "none"
    sources_used = set()
    for lst in (list(sale_df.get("source_name", []) if hasattr(sale_df, "get") else []),
                list(rent_df.get("source_name", []) if hasattr(rent_df, "get") else [])):
        sources_used.update([s for s in lst if s])
    any_sample = False
    if hasattr(sale_df, "columns") and "is_sample_data" in sale_df.columns and len(sale_df):
        any_sample = bool(sale_df["is_sample_data"].fillna(0).astype(int).max())

    collected_dates = []
    if hasattr(sale_df, "columns") and "collected_date" in sale_df.columns:
        collected_dates = list(sale_df["collected_date"].dropna())

    confidence = scoring.confidence_score(
        n_comparables=len(sale_df) if hasattr(sale_df, "__len__") else 0,
        n_rental_obs=len(rent_df) if hasattr(rent_df, "__len__") else 0,
        n_sources=max(len(sources_used), 1),
        locality_match=tier.startswith("locality"),
        bhk_match="bhk" in tier,
        tier=tier,
        collected_dates=collected_dates,
        any_sample_data=any_sample,
    )

    # --- 6. Investment score --------------------------------------------
    inv_score, inv_label = scoring.investment_score(
        price_vs_fair_value_pct=premium_pct,
        gross_yield=gross_yield,
        price_to_rent=price_to_rent,
        n_comparables=len(sale_df) if hasattr(sale_df, "__len__") else 0,
    )

    methodology_notes = (
        f"Comparable tier used: {tier}. Target rental yield for capitalization method: "
        f"{target_yield*100:.2f}%. Adjustments applied: {'; '.join(adjustment_notes) if adjustment_notes else 'none'}."
    )

    result = ValuationResult(
        property_id=subject.get("id", 0),
        market_rent_low=round(market_rent_low, 0) if market_rent_low else 0,
        market_rent_high=round(market_rent_high, 0) if market_rent_high else 0,
        market_rent_median=round(market_rent_median, 0) if market_rent_median else 0,
        comparable_value=round(comparable_value, 0) if comparable_value else 0,
        rental_cap_value=round(rental_cap_value, 0) if rental_cap_value else 0,
        adjusted_value=round(adjusted_val, 0) if adjusted_val else 0,
        fair_value_low=round(fair_low, 0) if fair_low else 0,
        fair_value_high=round(fair_high, 0) if fair_high else 0,
        gross_yield=round(gross_yield, 2),
        net_yield=round(net_yield, 2),
        price_to_rent=round(price_to_rent, 1),
        premium_pct=round(premium_pct, 1),
        verdict=verdict,
        investment_score=inv_score,
        investment_score_label=inv_label,
        confidence_pct=confidence,
        methodology_notes=methodology_notes,
        n_comparables=len(sale_df) if hasattr(sale_df, "__len__") else 0,
        n_rental_obs=len(rent_df) if hasattr(rent_df, "__len__") else 0,
        n_sources=max(len(sources_used), 1),
    )

    return {
        "result": result,
        "rent_stats": rent_stats,
        "sale_stats": sale_stats,
        "comparable_tier": tier,
        "sources": sorted(sources_used),
        "adjustment_notes": adjustment_notes,
        "target_yield": target_yield,
    }
