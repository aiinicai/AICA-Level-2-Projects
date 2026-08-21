from decimal import Decimal
from utils.formatting import to_decimal, round_decimal
from calculations.common import period_fraction


def calculate_slm_depreciation(cost, residual_value, useful_life_years, period_start, period_end,
                                basis="DAYS", year_days=365, opening_accum_dep=0, places=2):
    cost = to_decimal(cost)
    residual_value = to_decimal(residual_value)
    opening_accum_dep = to_decimal(opening_accum_dep)
    useful_life_years = to_decimal(useful_life_years)
    if useful_life_years <= 0:
        raise ValueError("Useful life must be greater than zero for SLM depreciation.")

    depreciable_amount = cost - residual_value
    annual_depreciation = depreciable_amount / useful_life_years
    fraction = period_fraction(period_start, period_end, basis, year_days)
    period_depreciation = annual_depreciation * fraction

    remaining_depreciable = depreciable_amount - opening_accum_dep
    if remaining_depreciable < 0:
        remaining_depreciable = Decimal("0")
    period_depreciation = min(period_depreciation, remaining_depreciable)
    if period_depreciation < 0:
        period_depreciation = Decimal("0")

    return {
        "depreciable_amount": round_decimal(depreciable_amount, places),
        "annual_depreciation": round_decimal(annual_depreciation, places),
        "period_fraction": fraction,
        "period_depreciation": round_decimal(period_depreciation, places),
    }


def calculate_wdv_depreciation(opening_wdv, rate, residual_value, period_start, period_end,
                                basis="DAYS", year_days=365, places=2):
    opening_wdv = to_decimal(opening_wdv)
    rate = to_decimal(rate)
    residual_value = to_decimal(residual_value)

    annual_depreciation = opening_wdv * rate / Decimal(100)
    fraction = period_fraction(period_start, period_end, basis, year_days)
    period_depreciation = annual_depreciation * fraction

    max_allowable = opening_wdv - residual_value
    if max_allowable < 0:
        max_allowable = Decimal("0")
    period_depreciation = min(period_depreciation, max_allowable)
    if period_depreciation < 0:
        period_depreciation = Decimal("0")

    closing_wdv = opening_wdv - period_depreciation
    return {
        "annual_depreciation": round_decimal(annual_depreciation, places),
        "period_fraction": fraction,
        "period_depreciation": round_decimal(period_depreciation, places),
        "closing_wdv": round_decimal(closing_wdv, places),
    }


def calculate_carrying_amount(opening_carrying_amount, period_depreciation, places=2):
    opening_carrying_amount = to_decimal(opening_carrying_amount)
    period_depreciation = to_decimal(period_depreciation)
    return round_decimal(opening_carrying_amount - period_depreciation, places)

def calculate_wdv_rate_from_life(cost, residual_value, useful_life_years):
    """
    Standard formula: Rate = [1 - (Residual/Cost)^(1/Life)] * 100
    """
    cost = to_decimal(cost)
    residual = to_decimal(residual_value)
    life = to_decimal(useful_life_years)

    if cost <= 0 or life <= 0:
        return Decimal("0")
    
    # Residual cannot be 0 for the formula (usually taken as 0.01 or 5% minimum)
    # If 0 is provided, we use a tiny value to avoid math error
    if residual <= 0:
        residual = Decimal("0.01")

    # Math: 1 - (residual/cost)^(1/life)
    ratio = float(residual / cost)
    exponent = 1.0 / float(life)
    rate = (1.0 - (ratio ** exponent)) * 100
    
    return round_decimal(rate, 2)