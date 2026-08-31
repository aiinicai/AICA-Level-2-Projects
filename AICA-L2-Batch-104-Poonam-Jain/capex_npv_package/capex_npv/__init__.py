"""
capex_npv
=========
A small package for appraising a Capex investment using a 10-year
discounted cash flow model: NPV, IRR, Payback Period, Profitability
Index, and sensitivity analysis.

Quick start
-----------
    from capex_npv import CapexNPVModel

    model = CapexNPVModel(
        initial_capex=500_000,
        base_revenue=400_000,
        sales_growth=[0.15, 0.10, 0.10, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08],
        ebitda_margin=0.20,
        tax_rate=0.25,
        discount_rate=0.12,
        useful_life=10,
    )
    model.build_projection()
    model.summary()
"""

from .model import CapexNPVModel

__all__ = ["CapexNPVModel"]
__version__ = "1.0.0"
