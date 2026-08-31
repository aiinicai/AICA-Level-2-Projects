"""
capex_npv.model
===============
Core valuation engine: builds a 10-year Free Cash Flow projection
from a set of Capex-appraisal assumptions (sales growth, margins,
tax, WACC, etc.) and values it via NPV, IRR, Payback Period and
Profitability Index.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# -------------------------------------------------------------
# 1. CORE MODEL CLASS
# -------------------------------------------------------------
class CapexNPVModel:
    def __init__(
        self,
        initial_capex: float,
        base_revenue: float,
        sales_growth,              # float OR list of 10 floats (as decimals, e.g. 0.08)
        ebitda_margin,              # float OR list of 10 floats (as decimals, e.g. 0.20)
        tax_rate: float,            # decimal, e.g. 0.25
        discount_rate: float,       # WACC, decimal, e.g. 0.12
        useful_life: int,           # years over which capex is depreciated (straight line)
        years: int = 10,
        maintenance_capex_pct: float = 0.0,   # % of revenue, ongoing capex
        wc_pct_of_sales: float = 0.0,         # working capital as % of incremental sales
        terminal_growth: float = 0.0,         # perpetuity growth after year N
        salvage_value: float = 0.0,           # post-tax salvage value at end of horizon
    ):
        self.initial_capex = initial_capex
        self.base_revenue = base_revenue
        self.years = years
        self.sales_growth = self._to_array(sales_growth, years)
        self.ebitda_margin = self._to_array(ebitda_margin, years)
        self.tax_rate = tax_rate
        self.discount_rate = discount_rate
        self.useful_life = useful_life
        self.maintenance_capex_pct = maintenance_capex_pct
        self.wc_pct_of_sales = wc_pct_of_sales
        self.terminal_growth = terminal_growth
        self.salvage_value = salvage_value

        self.projection = None  # filled by build_projection()

    @staticmethod
    def _to_array(value, years):
        """Allow user to pass either a single flat rate or a list of per-year rates."""
        if isinstance(value, (list, tuple, np.ndarray)):
            arr = np.array(value, dtype=float)
            if len(arr) != years:
                raise ValueError(f"Expected {years} values, got {len(arr)}")
            return arr
        return np.full(years, float(value))

    # ---------------------------------------------------------
    # 2. BUILD THE 10-YEAR PROJECTION
    # ---------------------------------------------------------
    def build_projection(self):
        n = self.years
        revenue = np.zeros(n)
        revenue[0] = self.base_revenue * (1 + self.sales_growth[0])
        for t in range(1, n):
            revenue[t] = revenue[t - 1] * (1 + self.sales_growth[t])

        ebitda = revenue * self.ebitda_margin

        # Straight-line depreciation of the initial capex over useful_life years
        dep_per_year = self.initial_capex / self.useful_life if self.useful_life > 0 else 0
        depreciation = np.array([
            dep_per_year if t < self.useful_life else 0.0 for t in range(n)
        ])

        ebit = ebitda - depreciation
        tax = np.maximum(ebit, 0) * self.tax_rate     # simplifying assumption: no tax shield on losses
        nopat = ebit - tax

        maintenance_capex = revenue * self.maintenance_capex_pct

        prev_revenue = np.concatenate(([self.base_revenue], revenue[:-1]))
        delta_wc = (revenue - prev_revenue) * self.wc_pct_of_sales

        fcf = nopat + depreciation - maintenance_capex - delta_wc

        df = pd.DataFrame({
            "Year": np.arange(1, n + 1),
            "Revenue": revenue,
            "EBITDA": ebitda,
            "Depreciation": depreciation,
            "EBIT": ebit,
            "Tax": tax,
            "NOPAT": nopat,
            "Maintenance Capex": maintenance_capex,
            "Change in WC": delta_wc,
            "FCF": fcf,
        })

        # Discount factors & present values
        df["Discount Factor"] = 1 / (1 + self.discount_rate) ** df["Year"]
        df["PV of FCF"] = df["FCF"] * df["Discount Factor"]

        self.projection = df
        return df

    # ---------------------------------------------------------
    # 3. VALUATION METRICS
    # ---------------------------------------------------------
    def terminal_value(self):
        """Gordon growth terminal value, discounted back to present, at end of horizon."""
        if self.projection is None:
            self.build_projection()
        last_fcf = self.projection["FCF"].iloc[-1]
        if self.discount_rate <= self.terminal_growth:
            raise ValueError("Discount rate must exceed terminal growth rate.")
        tv_at_horizon = last_fcf * (1 + self.terminal_growth) / (self.discount_rate - self.terminal_growth)
        pv_tv = tv_at_horizon / (1 + self.discount_rate) ** self.years
        return tv_at_horizon, pv_tv

    def npv(self, include_terminal_value: bool = True):
        if self.projection is None:
            self.build_projection()
        pv_fcf = self.projection["PV of FCF"].sum()
        pv_salvage = self.salvage_value / (1 + self.discount_rate) ** self.years

        pv_tv = 0.0
        if include_terminal_value and self.terminal_growth > 0:
            _, pv_tv = self.terminal_value()

        return -self.initial_capex + pv_fcf + pv_tv + pv_salvage

    def irr(self, include_terminal_value: bool = True, guess: float = 0.1):
        """Bisection-based IRR solver (no external dependency needed)."""
        if self.projection is None:
            self.build_projection()

        cashflows = [-self.initial_capex] + list(self.projection["FCF"])
        if include_terminal_value and self.terminal_growth > 0:
            tv_at_horizon, _ = self.terminal_value()
            cashflows[-1] += tv_at_horizon
        cashflows[-1] += self.salvage_value

        def npv_at_rate(r):
            return sum(cf / (1 + r) ** t for t, cf in enumerate(cashflows))

        low, high = -0.99, 5.0
        if npv_at_rate(low) * npv_at_rate(high) > 0:
            return None  # no sign change -> IRR not found in range
        for _ in range(200):
            mid = (low + high) / 2
            if abs(npv_at_rate(mid)) < 1e-6:
                return mid
            if npv_at_rate(low) * npv_at_rate(mid) < 0:
                high = mid
            else:
                low = mid
        return mid

    def payback_period(self):
        if self.projection is None:
            self.build_projection()
        cum_fcf = self.projection["FCF"].cumsum()
        remaining = self.initial_capex
        for t, fcf in zip(self.projection["Year"], self.projection["FCF"]):
            if remaining <= fcf:
                return (t - 1) + remaining / fcf
            remaining -= fcf
        return None  # not paid back within horizon

    def profitability_index(self):
        pv_inflows = self.npv() + self.initial_capex
        return pv_inflows / self.initial_capex

    # ---------------------------------------------------------
    # 4. SENSITIVITY TABLE
    # ---------------------------------------------------------
    def sensitivity_table(self, wacc_range, growth_range):
        """
        NPV sensitivity grid: rows = WACC, columns = flat sales-growth assumption.
        Uses a flat growth rate across all years for each scenario.
        """
        results = pd.DataFrame(index=[f"{w:.1%}" for w in wacc_range],
                                columns=[f"{g:.1%}" for g in growth_range])
        for w in wacc_range:
            for g in growth_range:
                temp_model = CapexNPVModel(
                    initial_capex=self.initial_capex,
                    base_revenue=self.base_revenue,
                    sales_growth=g,
                    ebitda_margin=self.ebitda_margin,
                    tax_rate=self.tax_rate,
                    discount_rate=w,
                    useful_life=self.useful_life,
                    years=self.years,
                    maintenance_capex_pct=self.maintenance_capex_pct,
                    wc_pct_of_sales=self.wc_pct_of_sales,
                    terminal_growth=self.terminal_growth,
                    salvage_value=self.salvage_value,
                )
                temp_model.build_projection()
                results.loc[f"{w:.1%}", f"{g:.1%}"] = round(temp_model.npv(), 0)
        return results

    # ---------------------------------------------------------
    # 5. REPORTING
    # ---------------------------------------------------------
    def summary(self):
        npv_val = self.npv()
        irr_val = self.irr()
        payback = self.payback_period()
        pi = self.profitability_index()
        print("=" * 55)
        print("CAPEX APPRAISAL SUMMARY")
        print("=" * 55)
        print(f"Initial Capex          : {self.initial_capex:,.0f}")
        print(f"Discount Rate (WACC)    : {self.discount_rate:.1%}")
        print(f"NPV                     : {npv_val:,.0f}")
        print(f"IRR                     : {irr_val:.1%}" if irr_val is not None else "IRR : n/a")
        print(f"Payback Period          : {payback:.2f} years" if payback else "Payback : beyond horizon")
        print(f"Profitability Index     : {pi:.2f}")
        print(f"Decision                : {'ACCEPT' if npv_val > 0 else 'REJECT'} (NPV {'>' if npv_val>0 else '<='} 0)")
        print("=" * 55)
        return {"NPV": npv_val, "IRR": irr_val, "Payback": payback, "PI": pi}

    def plot_cashflows(self, save_path: str = None, show: bool = True):
        if self.projection is None:
            self.build_projection()
        df = self.projection
        fig, ax1 = plt.subplots(figsize=(9, 5))
        ax1.bar(df["Year"], df["FCF"], color="#4C72B0", label="Free Cash Flow")
        ax1.set_xlabel("Year")
        ax1.set_ylabel("FCF")
        ax1.axhline(0, color="black", linewidth=0.8)

        ax2 = ax1.twinx()
        cum_pv = df["PV of FCF"].cumsum() - self.initial_capex
        ax2.plot(df["Year"], cum_pv, color="#C44E52", marker="o", label="Cumulative PV (NPV build-up)")
        ax2.set_ylabel("Cumulative PV of Cash Flows")

        fig.suptitle("Free Cash Flow Profile & NPV Build-up")
        fig.legend(loc="upper left", bbox_to_anchor=(0.1, 0.88))
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150)
        if show:
            plt.show()
        return fig
