from decimal import Decimal
from calculations.deferred_tax import calculate_deferred_tax


def test_deferred_tax_liability():
    result = calculate_deferred_tax(carrying_amount=80000, tax_base=60000, tax_rate=25)
    assert result["temporary_difference"] == Decimal("20000.00")
    assert result["deferred_tax"] == Decimal("5000.00")
    assert result["deferred_tax_type"] == "Deferred Tax Liability"


def test_deferred_tax_rate_change():
    for rate, expected in [(20, Decimal("4000.00")), (25, Decimal("5000.00")), (30, Decimal("6000.00"))]:
        result = calculate_deferred_tax(80000, 60000, rate)
        assert result["deferred_tax"] == expected