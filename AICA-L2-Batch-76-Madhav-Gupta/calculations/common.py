from decimal import Decimal
from utils.formatting import to_decimal
from utils.date_utils import days_between, months_between


def period_fraction(period_start, period_end, basis="DAYS", year_days=365):
    basis = (basis or "DAYS").upper()
    if basis == "MONTHS":
        months = months_between(period_start, period_end)
        return to_decimal(months) / Decimal(12)
    elif basis == "EXACT":
        days = days_between(period_start, period_end)
        return to_decimal(days) / Decimal(year_days)
    else:  # DAYS
        days = days_between(period_start, period_end)
        return to_decimal(days) / Decimal(year_days)