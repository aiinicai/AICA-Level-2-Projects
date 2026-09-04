"""
capex_npv.cli
=============
Interactive command-line entry point.

Run with:
    capex-npv-cli
or:
    python -m capex_npv.cli
"""

import pandas as pd
from .model import CapexNPVModel


def _ask(prompt, default):
    val = input(f"{prompt} [{default}]: ").strip()
    return float(val) if val else default


def get_user_inputs():
    print("Enter your Capex project assumptions (press Enter to use default in [brackets]):\n")

    initial_capex = _ask("Initial Capex outlay", 500_000)
    base_revenue = _ask("Current (Year 0) Revenue", 400_000)

    growth_mode = input(
        "Sales growth: same rate every year, or custom per year? (same/custom) [custom]: "
    ).strip().lower() or "custom"

    if growth_mode == "custom":
        default_growth = [15, 10, 10, 8, 8, 8, 8, 8, 8, 8]
        sales_growth = [_ask(f"  Sales growth % Year {i}", default_growth[i-1]) / 100 for i in range(1, 11)]
    else:
        sales_growth = _ask("Flat sales growth % for all 10 years", 8) / 100

    ebitda_margin = _ask("EBITDA margin %", 20) / 100
    tax_rate = _ask("Tax rate %", 25) / 100
    discount_rate = _ask("Discount rate / WACC %", 12) / 100
    useful_life = int(_ask("Useful life of asset (years)", 10))
    maintenance_capex_pct = _ask("Ongoing/maintenance capex as % of revenue", 2) / 100
    wc_pct_of_sales = _ask("Working capital as % of incremental sales", 5) / 100
    terminal_growth = _ask("Terminal growth rate % (0 if none)", 0) / 100
    salvage_value = _ask("Salvage value at end of Year 10", 0)

    return dict(
        initial_capex=initial_capex,
        base_revenue=base_revenue,
        sales_growth=sales_growth,
        ebitda_margin=ebitda_margin,
        tax_rate=tax_rate,
        discount_rate=discount_rate,
        useful_life=useful_life,
        maintenance_capex_pct=maintenance_capex_pct,
        wc_pct_of_sales=wc_pct_of_sales,
        terminal_growth=terminal_growth,
        salvage_value=salvage_value,
    )


def main():
    inputs = get_user_inputs()
    model = CapexNPVModel(**inputs)

    projection = model.build_projection()
    pd.set_option("display.float_format", lambda x: f"{x:,.0f}")
    print("\n10-YEAR PROJECTION\n")
    print(projection.to_string(index=False))
    print()

    model.summary()

    print("\nSENSITIVITY: NPV vs WACC (rows) and Sales Growth (columns)\n")
    wacc_range = [model.discount_rate - 0.02, model.discount_rate, model.discount_rate + 0.02]
    growth_range = [0.04, 0.08, 0.12]
    print(model.sensitivity_table(wacc_range, growth_range))

    model.plot_cashflows(save_path="capex_fcf_chart.png")


if __name__ == "__main__":
    main()
