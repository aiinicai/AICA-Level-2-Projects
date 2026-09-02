"""
valuation/rental_yield.py
Gross/net rental yield and price-to-rent ratio calculations.
"""


def annual_rent(monthly_rent: float) -> float:
    return monthly_rent * 12


def gross_rental_yield(monthly_rent: float, property_value: float) -> float:
    """Returns yield as a percentage (e.g. 3.6 for 3.6%)."""
    if not property_value:
        return 0.0
    return (annual_rent(monthly_rent) / property_value) * 100


def net_annual_rent(monthly_rent: float, maintenance_month: float = 0,
                     property_tax_year: float = 0, insurance_year: float = 0,
                     vacancy_pct: float = 0, repairs_year: float = 0,
                     management_pct: float = 0) -> float:
    gross = annual_rent(monthly_rent)
    vacancy_loss = gross * (vacancy_pct / 100)
    management_fee = gross * (management_pct / 100)
    expenses = (maintenance_month * 12) + property_tax_year + insurance_year + repairs_year + management_fee
    return gross - vacancy_loss - expenses


def net_rental_yield(monthly_rent: float, total_investment: float, **expense_kwargs) -> float:
    """
    total_investment should include asking price + stamp duty/registration +
    brokerage + renovation cost (i.e. total capital deployed), per spec
    section on Net Rental Yield ("Total Property Investment").
    """
    if not total_investment:
        return 0.0
    net_rent = net_annual_rent(monthly_rent, **expense_kwargs)
    return (net_rent / total_investment) * 100


def price_to_rent_ratio(property_value: float, monthly_rent: float) -> float:
    ar = annual_rent(monthly_rent)
    if not ar:
        return 0.0
    return property_value / ar


def years_of_rent_equivalent(property_value: float, monthly_rent: float) -> float:
    return price_to_rent_ratio(property_value, monthly_rent)
