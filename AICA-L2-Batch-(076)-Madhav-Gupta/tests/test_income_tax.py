from decimal import Decimal
from calculations.income_tax import calculate_block_income_tax_depreciation


def test_block_income_tax_depreciation_with_addition():
    result = calculate_block_income_tax_depreciation(
        opening_wdv=100000, additions_full_rate=20000, disposal_proceeds=0, rate=15)
    assert result["wdv_before_depreciation"] == Decimal("120000.00")
    assert result["depreciation"] == Decimal("18000.00")
    assert result["closing_wdv"] == Decimal("102000.00")


def test_block_income_tax_no_depreciation_on_sold_asset():
    # Sale proceeds reduce the block WDV; depreciation is computed on the RESULTING
    # block WDV, never on the individual sold asset.
    result = calculate_block_income_tax_depreciation(
        opening_wdv=100000, additions_full_rate=0, disposal_proceeds=40000, rate=15)
    assert result["wdv_before_depreciation"] == Decimal("60000.00")
    assert result["depreciation"] == Decimal("9000.00")


def test_block_short_term_capital_gain_when_block_extinguished():
    result = calculate_block_income_tax_depreciation(
        opening_wdv=30000, additions_full_rate=0, disposal_proceeds=50000, rate=15)
    assert result["wdv_before_depreciation"] == Decimal("-20000.00")
    assert result["depreciation"] == Decimal("0.00")
    assert result["short_term_capital_gain"] == Decimal("20000.00")