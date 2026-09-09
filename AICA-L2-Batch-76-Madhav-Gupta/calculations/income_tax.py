from decimal import Decimal
from utils.formatting import to_decimal, round_decimal

def calculate_block_income_tax_depreciation(opening_wdv, additions_full_rate=0, additions_half_rate=0,
                                             disposal_proceeds=0, rate=0, places=2):
    """
    Standard Indian Income-tax Act Section 32 calculation at the block level.
    """
    opening_wdv = to_decimal(opening_wdv)
    add_full = to_decimal(additions_full_rate)
    add_half = to_decimal(additions_half_rate)
    disposals = to_decimal(disposal_proceeds)
    tax_rate = to_decimal(rate)

    # WDV for the block before providing depreciation
    wdv_before_dep = opening_wdv + add_full + add_half - disposals

    short_term_gain = Decimal("0")
    depreciation = Decimal("0")
    
    if wdv_before_dep < 0:
        # Case: Proceeds exceed block value = Short Term Capital Gain
        short_term_gain = abs(wdv_before_dep)
        wdv_before_dep = Decimal("0")
        closing_wdv = Decimal("0")
    elif wdv_before_dep > 0:
        # Step 1: Calculate depreciation on assets used < 180 days (Half Rate)
        # This is restricted to the available WDV
        limit_for_half_rate = min(wdv_before_dep, add_half)
        dep_on_half = limit_for_half_rate * (tax_rate / Decimal("200"))
        
        # Step 2: Calculate depreciation on balance WDV (Full Rate)
        remaining_wdv = wdv_before_dep - limit_for_half_rate
        dep_on_full = remaining_wdv * (tax_rate / Decimal("100"))
        
        depreciation = dep_on_half + dep_on_full
        
        # Safety check: Dep cannot exceed available WDV
        if depreciation > wdv_before_dep:
            depreciation = wdv_before_dep
            
        closing_wdv = wdv_before_dep - depreciation
    else:
        closing_wdv = Decimal("0")

    return {
        "opening_wdv": round_decimal(opening_wdv, places),
        "additions": round_decimal(add_full + add_half, places),
        "disposals": round_decimal(disposals, places),
        "wdv_before_depreciation": round_decimal(wdv_before_dep, places),
        "depreciation": round_decimal(depreciation, places),
        "closing_wdv": round_decimal(closing_wdv, places),
        "short_term_capital_gain": round_decimal(short_term_gain, places),
    }