from decimal import Decimal
from utils.formatting import to_decimal, round_decimal


def calculate_temporary_difference(carrying_amount, tax_base, places=2):
    carrying_amount = to_decimal(carrying_amount)
    tax_base = to_decimal(tax_base)
    return round_decimal(carrying_amount - tax_base, places)


def calculate_deferred_tax(carrying_amount, tax_base, tax_rate, places=2):
    carrying_amount = to_decimal(carrying_amount)
    tax_base = to_decimal(tax_base)
    tax_rate = to_decimal(tax_rate)

    temporary_difference = carrying_amount - tax_base
    deferred_tax = abs(temporary_difference) * tax_rate / Decimal(100)

    if temporary_difference > 0:
        dt_type = "Deferred Tax Liability"
    elif temporary_difference < 0:
        dt_type = "Deferred Tax Asset"
    else:
        dt_type = "None"
        deferred_tax = Decimal("0")

    return {
        "carrying_amount": round_decimal(carrying_amount, places),
        "tax_base": round_decimal(tax_base, places),
        "temporary_difference": round_decimal(temporary_difference, places),
        "tax_rate": tax_rate,
        "deferred_tax": round_decimal(deferred_tax, places),
        "deferred_tax_type": dt_type,
    }