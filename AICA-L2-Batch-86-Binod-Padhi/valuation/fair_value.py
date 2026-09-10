"""
valuation/fair_value.py

Combines three independent valuation methods into an Estimated Fair
Value Range, per spec section 9. Never presents a single point estimate
as "the" value.
"""

from valuation import rental_yield as ry

# Adjustment factors are illustrative, application-defined multipliers —
# NOT derived from a regression model (none is available without a large
# labeled transaction dataset). They are conservative and configurable.
ADJUSTMENT_FACTORS = {
    "floor_high": 0.02,          # +2% for a high floor with view/light, if applicable
    "floor_ground_penalty": -0.02,
    "new_construction": 0.05,    # +5% if "New" vs "Resale"
    "furnished": 0.04,
    "semi_furnished": 0.02,
    "gated_community": 0.03,
    "lift": 0.01,
    "parking": 0.015,
    "old_property_penalty_per_year": -0.004,  # -0.4%/year beyond 10 years, capped
    "old_property_threshold_years": 10,
    "old_property_penalty_cap": -0.15,
}


def comparable_method_value(comparable_value: float) -> float:
    return comparable_value


def rental_capitalization_value(monthly_rent: float, target_yield: float) -> float:
    """target_yield as a decimal, e.g. 0.04 for 4%."""
    if not target_yield:
        return None
    return ry.annual_rent(monthly_rent) / target_yield


def adjusted_value(base_value: float, subject: dict) -> (float, list):
    """
    Applies qualitative adjustments to a base value (typically the
    comparable value). Returns (adjusted_value, list_of_applied_adjustments)
    for transparency in reports.
    """
    if base_value is None:
        return None, []

    total_pct = 0.0
    notes = []

    floor = subject.get("floor")
    total_floors = subject.get("total_floors")
    if floor is not None and total_floors and total_floors > 0:
        if floor == 0:
            total_pct += ADJUSTMENT_FACTORS["floor_ground_penalty"]
            notes.append("Ground floor: -2%")
        elif floor / total_floors >= 0.7:
            total_pct += ADJUSTMENT_FACTORS["floor_high"]
            notes.append("High floor: +2%")

    if str(subject.get("new_or_resale", "")).lower() == "new":
        total_pct += ADJUSTMENT_FACTORS["new_construction"]
        notes.append("New construction: +5%")

    furnishing = str(subject.get("furnishing", "")).lower()
    if furnishing == "furnished":
        total_pct += ADJUSTMENT_FACTORS["furnished"]
        notes.append("Furnished: +4%")
    elif furnishing == "semi-furnished":
        total_pct += ADJUSTMENT_FACTORS["semi_furnished"]
        notes.append("Semi-furnished: +2%")

    if subject.get("gated_community"):
        total_pct += ADJUSTMENT_FACTORS["gated_community"]
        notes.append("Gated community: +3%")
    if subject.get("lift"):
        total_pct += ADJUSTMENT_FACTORS["lift"]
        notes.append("Lift available: +1%")
    if subject.get("parking"):
        total_pct += ADJUSTMENT_FACTORS["parking"]
        notes.append("Parking available: +1.5%")

    age = subject.get("age_years") or 0
    threshold = ADJUSTMENT_FACTORS["old_property_threshold_years"]
    if age > threshold:
        penalty = (age - threshold) * ADJUSTMENT_FACTORS["old_property_penalty_per_year"]
        penalty = max(penalty, ADJUSTMENT_FACTORS["old_property_penalty_cap"])
        total_pct += penalty
        notes.append(f"Age {age:.0f} yrs beyond {threshold}: {penalty*100:.1f}%")

    return base_value * (1 + total_pct), notes


def estimate_fair_value_range(comparable_val, rental_val, adjusted_val) -> (float, float, float):
    """
    Returns (low, high, midpoint) across the available method estimates.
    Any method that returned None is excluded. If all are None, returns
    (None, None, None).
    """
    values = [v for v in (comparable_val, rental_val, adjusted_val) if v is not None and v > 0]
    if not values:
        return None, None, None
    low = min(values) * 0.97   # small buffer to express range rather than false precision
    high = max(values) * 1.03
    mid = sum(values) / len(values)
    return low, high, mid
