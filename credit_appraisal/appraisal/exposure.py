"""
exposure.py
===========
Existing-exposure profiling, pro-forma (post-loan) leverage/coverage metrics, a repayment
schedule for the proposed facility and a simple stress-testing grid.

Pro-forma conventions (conservative, stated so the credit committee can challenge them):
* Starting debt is the lender-wise outstanding in the debt schedule (more current than the balance sheet).
* TNW and EBITDA are held at the latest audited level (no credit for projected growth or loan proceeds).
* Proposed facility is repaid in equal annual principal instalments after the moratorium;
  debt service is measured in the FIRST full repayment year (peak interest + principal).
* Capex deducted in the pro-forma DSCR is MAINTENANCE capex, proxied by latest-year depreciation: growth capex is
  assumed to be funded by the proposed loan itself, so deducting it again would double-count. (Historical DSCRs
  in ratios.py deduct ACTUAL capex, exactly as per the policy formula.)
* Refinance portion of the new loan retires existing debt pro-rata (existing principal & interest scaled down).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .ingestion import ApplicantData
from .ratios import RatioBundle


def _sf(a, b):
    """Safe float division."""
    return float(a) / float(b) if b and not np.isnan(b) and b != 0 else np.nan


# --------------------------------------------------------------------------- #
# Existing exposure profile
# --------------------------------------------------------------------------- #
def exposure_profile(data: ApplicantData, bundle: RatioBundle) -> dict:
    ed = data.existing_debt
    outstanding = float(ed["Outstanding"].sum())
    sanctioned = float(ed["Sanctioned Limit"].sum())
    by_lender = (ed.groupby("Lender")[["Sanctioned Limit", "Outstanding", "Annual Principal", "Annual Interest"]]
                 .sum().sort_values("Outstanding", ascending=False))
    by_lender["Share of debt"] = by_lender["Outstanding"] / outstanding if outstanding else np.nan
    by_type = (ed.groupby("Facility Type")[["Sanctioned Limit", "Outstanding", "Annual Principal", "Annual Interest"]]
               .sum().sort_values("Outstanding", ascending=False))

    wc = ed[ed["Facility Type"] == "Working Capital CC/OD"]
    cc_util = _sf(wc["Outstanding"].sum(), wc["Sanctioned Limit"].sum()) if len(wc) else np.nan
    bs_debt = float(bundle.fin["total_debt"].iloc[-1])
    return dict(
        outstanding=outstanding, sanctioned=sanctioned, by_lender=by_lender, by_type=by_type,
        n_lenders=int(ed["Lender"].nunique()), top_lender_share=float(by_lender["Share of debt"].max()),
        wavg_rate=_sf((ed["Outstanding"] * ed["Interest Rate (%)"]).sum(), outstanding),
        cc_utilisation=cc_util, bs_debt=bs_debt, recon_gap_pct=_sf(outstanding - bs_debt, bs_debt),
        wc_limits=float(wc["Sanctioned Limit"].sum()),
    )


# --------------------------------------------------------------------------- #
# Pro-forma computation
# --------------------------------------------------------------------------- #
def compute_pro_forma(data: ApplicantData, bundle: RatioBundle, include_proposed: bool = True,
                      ebitda_haircut: float = 0.0, rate_shock_bps: float = 0.0) -> dict:
    """
    Pro-forma leverage & coverage metrics. ``include_proposed=False`` gives today's position on the
    same basis, so before/after comparisons are like-for-like.
    """
    f, ed, prop = bundle.fin, data.existing_debt, data.proposed
    last = f.iloc[-1]
    shock = rate_shock_bps / 10_000

    out_e = float(ed["Outstanding"].sum())
    prin_e = float(ed["Annual Principal"].sum())
    int_e = float(ed["Annual Interest"].sum())
    sanc_e = float(ed["Sanctioned Limit"].sum())

    amount = float(prop["amount"]) if include_proposed else 0.0
    refi = min(float(prop.get("refinance_amount", 0.0)), amount, out_e) if include_proposed else 0.0
    if refi > 0 and out_e > 0:                      # scale existing obligations down pro-rata
        keep = 1 - refi / out_e
        prin_e, int_e, sanc_e = prin_e * keep, int_e * keep, sanc_e * keep
        out_e = out_e - refi

    # Proposed facility: first full repayment year
    rate = float(prop["rate_pct"]) / 100 + shock
    repay_years = max(float(prop["tenure_years"]) - float(prop["moratorium_months"]) / 12, 1.0)
    prin_p = amount / repay_years
    int_p = amount * rate

    total_debt = out_e + amount
    interest = int_e + int_p + out_e * shock           # existing book assumed floating for the rate shock
    principal = prin_e + prin_p
    debt_service = principal + interest

    ebitda = float(last["ebitda"]) * (1 - ebitda_haircut)
    ebit = ebitda - float(last["dep"])
    capex = float(last["dep"])                      # maintenance-capex proxy
    tax = float(last["tax"])
    tnw = float(last["tnw"])

    return dict(
        total_debt=total_debt, existing_debt=out_e, proposed_debt=amount, refinance=refi,
        sanctioned_exposure=sanc_e + amount,
        tnw=tnw, ebitda=ebitda, ebit=ebit, capex_basis=capex, tax=tax,
        existing_interest=int_e, existing_principal=prin_e, prop_interest=int_p, prop_principal=prin_p,
        interest=interest, principal=principal, debt_service=debt_service,
        de=(total_debt / tnw) if tnw > 0 else np.inf,
        debt_ebitda=(total_debt / ebitda) if ebitda > 0 else np.inf,
        icr=_sf(ebit, interest),
        dscr=_sf(ebitda - capex - tax, debt_service),
        exposure_to_tnw=_sf(total_debt, tnw) if tnw > 0 else np.inf,
        proposed_to_tnw=_sf(amount, tnw) if tnw > 0 else np.inf,
        proposed_to_revenue=_sf(amount, last["revenue"]),
        security_cover=_sf(float(prop.get("collateral_value", 0.0)), amount) if amount else np.nan,
    )


def stress_table(data: ApplicantData, bundle: RatioBundle, limits) -> pd.DataFrame:
    """Pro-forma DSCR / ICR / Debt-EBITDA under standard shocks, with a pass/fail flag vs policy."""
    scenarios = [
        ("Base case", 0.00, 0),
        ("EBITDA -10%", 0.10, 0),
        ("EBITDA -20%", 0.20, 0),
        ("Interest rate +100 bps", 0.00, 100),
        ("EBITDA -15% and rate +100 bps", 0.15, 100),
    ]
    rows = []
    for name, hc, bps in scenarios:
        m = compute_pro_forma(data, bundle, True, hc, bps)
        rows.append({
            "Scenario": name, "DSCR": m["dscr"], "ICR": m["icr"], "Debt / EBITDA": m["debt_ebitda"],
            "DSCR >= policy": m["dscr"] >= limits.min_dscr,
            "DSCR >= 1.0x (can service)": m["dscr"] >= limits.critical_dscr,
        })
    return pd.DataFrame(rows).set_index("Scenario")


def repayment_schedule(data: ApplicantData) -> pd.DataFrame:
    """Annual principal / interest / closing balance of the proposed facility."""
    prop = data.proposed
    amount, rate = float(prop["amount"]), float(prop["rate_pct"]) / 100
    tenure = float(prop["tenure_years"])
    mor = float(prop["moratorium_months"]) / 12
    repay_years = max(tenure - mor, 1.0)
    inst = amount / repay_years

    rows, bal = [], amount
    for y in range(1, int(math.ceil(tenure)) + 1):
        interest = bal * rate
        # fraction of year y that falls after the moratorium
        share = min(max(y - mor, 0.0), 1.0)
        principal = min(inst * share, bal)
        bal -= principal
        rows.append({"Year": y, "Opening": bal + principal, "Principal": principal, "Interest": interest,
                     "Debt service": principal + interest, "Closing": bal})
    return pd.DataFrame(rows).set_index("Year")
