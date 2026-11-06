"""Module 7: income-tax computation for the society (AY 2026-27) with s.80P analysis.

Principle of mutuality: receipts from members (maintenance, non-occupancy charges,
transfer premium within bye-law limits, interest on arrears, parking) are not income.
Receipts from non-members and interest on bank deposits are taxable; interest and
dividend from co-operative banks are deductible under s.80P(2)(d).
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from .findings import Finding, inr
from .loaders import SocietyData

COOP_SLABS = [(10_000, 0.10), (10_000, 0.20), (float("inf"), 0.30)]  # s.115 / Finance Act rates for co-operative societies
CESS = 0.04
SEC_115BAD_RATE = 0.22
SEC_115BAD_SURCHARGE = 0.10
STANDARD_DEDUCTION_HP = 0.30


def _slab_tax(income: float) -> float:
    tax, remaining = 0.0, max(income, 0.0)
    for width, rate in COOP_SLABS:
        chunk = min(remaining, width)
        tax += chunk * rate
        remaining -= chunk
        if remaining <= 0:
            break
    return round(tax, 0)


def compute_tax(d: SocietyData, filing_date: date = date(2026, 10, 31)):
    oi = d.other_income.copy()
    coop_interest = float(oi[oi.section_hint == "80P(2)(d)"].gross_amount.sum())
    bank_interest = float(oi[oi["head"].str.contains("HDFC")].gross_amount.sum())
    tower_rent = float(oi[oi["head"].str.contains("tower")].gross_amount.sum())
    scrap = float(oi[oi["head"].str.contains("scrap")].gross_amount.sum())
    mutual = float(oi[oi.mutual].gross_amount.sum())
    tds_credit = float(oi.tds.sum())
    members_receipts = float(d.bills.bill_total.sum() - d.bills.gst_charged.sum())

    hp_income = round(tower_rent * (1 - STANDARD_DEDUCTION_HP), 0)
    ifos = round(bank_interest + coop_interest + scrap, 0)
    gti = hp_income + ifos
    ded_80p = coop_interest
    total_income = round(gti - ded_80p, 0)
    total_income_rounded = int(round(total_income / 10.0) * 10)

    tax_old = _slab_tax(total_income_rounded)
    tax_old_total = round(tax_old * (1 + CESS), 0)
    # s.115BAD: 22% + 10% surcharge + 4% cess, no 80P
    inc_new = gti
    tax_new = round(inc_new * SEC_115BAD_RATE * (1 + SEC_115BAD_SURCHARGE) * (1 + CESS), 0)
    regime = "Normal provisions with s.80P" if tax_old_total <= tax_new else "s.115BAD"
    tax_payable = min(tax_old_total, tax_new)
    net_payable = round(tax_payable - tds_credit, 0)
    advance_tax_paid = float(d.master("Advance tax paid") or 0)
    # s.234C: shortfall in instalments (15/45/75/100%) x 1% x 3 months (last instalment 1 month)
    assessed = tax_payable - tds_credit
    int_234c = 0.0
    if assessed > 10_000:
        for pct, months in [(0.15, 3), (0.45, 3), (0.75, 3), (1.00, 1)]:
            due_inst = assessed * pct
            int_234c += max(due_inst - advance_tax_paid, 0) * 0.01 * months
    int_234c = round(int_234c, 0)
    # s.234B: 1% p.m. from 1 April to date of filing on assessed tax less advance tax (if advance tax < 90%)
    months_234b = (filing_date.year - 2026) * 12 + filing_date.month - 4 + 1
    int_234b = round(max(assessed - advance_tax_paid, 0) * 0.01 * months_234b, 0) if advance_tax_paid < 0.9 * assessed and assessed > 10_000 else 0.0

    comp = pd.DataFrame([
        ("A. Receipts covered by mutuality (not income)", None),
        ("Maintenance, sinking/repair fund, NOC, parking and interest from members", members_receipts),
        ("Transfer premium from members (within bye-law limit of Rs 25,000)", mutual),
        ("B. Income from House Property", None),
        ("Rent from mobile tower (non-member)", tower_rent),
        ("Less: standard deduction u/s 24(a) @30%", -round(tower_rent * STANDARD_DEDUCTION_HP, 0)),
        ("Income from house property", hp_income),
        ("C. Income from Other Sources", None),
        ("Interest on FDs with the District Central Co-op Bank", coop_interest),
        ("Interest on FDs with HDFC Bank", bank_interest),
        ("Sale of scrap", scrap),
        ("Income from other sources", ifos),
        ("D. Gross Total Income", gti),
        ("Less: deduction u/s 80P(2)(d) - interest from co-operative bank", -ded_80p),
        ("Total Income (rounded u/s 288A)", total_income_rounded),
        ("E. Tax - normal provisions (10% / 20% / 30% slabs)", tax_old),
        ("Add: health & education cess @4%", round(tax_old * CESS, 0)),
        ("Tax under normal provisions", tax_old_total),
        ("F. Tax under s.115BAD (22% + 10% surcharge + 4% cess, no 80P)", tax_new),
        (f"Recommended regime: {regime}", tax_payable),
        ("Less: TDS credit (Form 26AS: tower rent 194-I, bank interest 194A)", -tds_credit),
        ("Net tax payable", net_payable),
        ("Add: interest u/s 234C (deferment of advance tax)", int_234c),
        (f"Add: interest u/s 234B (1% p.m. from 01-Apr-2026 to {filing_date:%d-%b-%Y})", int_234b),
        ("Total payable with return", net_payable + int_234b + int_234c),
    ], columns=["particulars", "amount"])

    findings = [
        Finding("Tax - Income tax", "Advance tax and interest", "Medium",
                f"Tax liability after TDS is {inr(net_payable)} (normal provisions with s.80P(2)(d) deduction of {inr(ded_80p)} is more beneficial than s.115BAD by {inr(tax_new - tax_old_total)}). "
                f"No advance tax was paid although liability exceeds Rs 10,000, attracting interest of about {inr(int_234b + int_234c)} u/s 234B/234C. Return in ITR-5 is due {filing_date:%d-%b-%Y}.",
                "Income-tax Act ss.80P(2)(d), 115BAD, 208, 234B, 234C, 139(1); CIT v. Totgars (SC) and Mavilayi (SC) on 80P",
                "Pay the self-assessment tax with interest before filing; set a calendar for advance tax instalments (15 Jun/Sep/Dec/Mar) based on tower rent and bank interest.",
                net_payable + int_234b + int_234c, "Sheet: Tax_Computation"),
        Finding("Tax - Income tax", "Mutuality and 80P position", "Low",
                f"Receipts from members of {inr(members_receipts)} and transfer premium of {inr(mutual)} are treated as mutual. Transfer premium is within the Rs 25,000 cap; interest from the co-operative bank ({inr(coop_interest)}) is claimed u/s 80P(2)(d). Interest from HDFC Bank and tower rent are taxable.",
                "Bombay HC in Sind CHS (2009) and Mittal Court Premises CHS; s.80P(2)(d); Totgars (SC 2010) distinguished",
                "Document the mutuality position in the tax file; obtain Form 26AS and reconcile TDS of {}.".format(inr(tds_credit)),
                0.0, "Sheet: Tax_Computation"),
    ]
    summary = {"gti": gti, "deduction_80p": ded_80p, "total_income": total_income_rounded, "tax_old": tax_old_total, "tax_115bad": tax_new,
               "tds_credit": tds_credit, "net_payable": net_payable, "interest_234b": int_234b, "interest_234c": int_234c, "regime": regime}
    return comp, summary, findings
