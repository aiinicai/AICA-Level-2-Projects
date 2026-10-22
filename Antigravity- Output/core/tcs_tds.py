"""
Layer C: TCS (Tax Collected at Source) and TDS (Section 194-O) Reconciliation.
Compares:
- TCS in MTR vs TCS in Payments vs Statutory Rate x Net Taxable Sales
- TDS in Payments vs Statutory Rate x Gross Sales
- Verification against User-Entered GSTR-8 (Table 4) and Form 26AS monthly figures.
"""
from decimal import Decimal
from typing import Dict, Any, List


def reconcile_tcs_tds(
    mtr_records: List[Dict[str, Any]],
    payment_records: List[Dict[str, Any]],
    tcs_statutory_rate: Decimal = Decimal("0.005"),  # 0.5% (0.25% CGST + 0.25% SGST or 0.5% IGST)
    tds_statutory_rate: Decimal = Decimal("0.001"),  # 0.1% under Section 194-O
    gstr8_net_taxable: Decimal = Decimal("0.00"),
    gstr8_tcs: Decimal = Decimal("0.00"),
    form26as_tds: Decimal = Decimal("0.00"),
    tolerance: Decimal = Decimal("1.00")
) -> Dict[str, Any]:
    """
    Perform Layer C TCS/TDS Reconciliation.
    Pure function: no Streamlit code.
    """
    # 1. MTR Figures
    mtr_net_taxable = sum((r["taxable_value"] for r in mtr_records), Decimal("0.00"))

    mtr_gross_invoice = sum((r["invoice_value"] for r in mtr_records if not r["is_return"]), Decimal("0.00"))
    mtr_tcs_total = sum((abs(r["tcs_total"]) for r in mtr_records), Decimal("0.00"))

    # 2. Payments Figures
    pay_tcs_cgst = sum((abs(p["tcs_cgst"]) for p in payment_records), Decimal("0.00"))
    pay_tcs_sgst = sum((abs(p["tcs_sgst"]) for p in payment_records), Decimal("0.00"))
    pay_tcs_igst = sum((abs(p["tcs_igst"]) for p in payment_records), Decimal("0.00"))
    pay_tcs_total = pay_tcs_cgst + pay_tcs_sgst + pay_tcs_igst

    pay_tds_total = sum((abs(p["tds"]) for p in payment_records), Decimal("0.00"))

    # 3. Statutory Expectations
    expected_tcs_statutory = (mtr_net_taxable * tcs_statutory_rate).quantize(Decimal("0.01"))
    expected_tds_statutory = (mtr_gross_invoice * tds_statutory_rate).quantize(Decimal("0.01"))

    # 4. Discrepancies
    tcs_mtr_vs_pay = mtr_tcs_total - pay_tcs_total
    tcs_mtr_vs_statutory = mtr_tcs_total - expected_tcs_statutory
    tcs_pay_vs_gstr8 = (pay_tcs_total - gstr8_tcs) if gstr8_tcs > Decimal("0.00") else Decimal("0.00")

    tds_pay_vs_statutory = pay_tds_total - expected_tds_statutory
    tds_pay_vs_26as = (pay_tds_total - form26as_tds) if form26as_tds > Decimal("0.00") else Decimal("0.00")

    # Order-level TCS/TDS anomalies
    anomalies: List[Dict[str, Any]] = []

    # Check for order-level TCS rate anomaly
    for r in mtr_records:
        if r["is_return"]:
            continue
        taxable = r["taxable_value"]
        tcs_amt = abs(r.get("tcs_total", Decimal("0.00")))
        if taxable > Decimal("0.00") and tcs_amt > Decimal("0.00"):
            implied_rate = (tcs_amt / taxable).quantize(Decimal("0.0001"))
            if abs(implied_rate - tcs_statutory_rate) > Decimal("0.002"):  # e.g. 1.0% vs 0.5%
                anomalies.append({
                    "order_id": r.get("order_id"),
                    "invoice_no": r.get("invoice_no"),
                    "type": "TCS Rate Anomaly",
                    "reason_code": "TCS/TDS",
                    "taxable_value": taxable,
                    "tcs_deducted": tcs_amt,
                    "expected_tcs": (taxable * tcs_statutory_rate).quantize(Decimal("0.01")),
                    "difference": tcs_amt - (taxable * tcs_statutory_rate).quantize(Decimal("0.01")),
                    "details": f"Implied TCS rate is {(implied_rate * 100):.2f}% vs statutory {(tcs_statutory_rate * 100):.2f}%."
                })

    return {
        "summary": {
            "mtr_net_taxable": mtr_net_taxable,
            "mtr_gross_invoice": mtr_gross_invoice,
            "expected_tcs_statutory": expected_tcs_statutory,
            "mtr_tcs_total": mtr_tcs_total,
            "pay_tcs_total": pay_tcs_total,
            "gstr8_tcs": gstr8_tcs,
            "tcs_mtr_vs_pay": tcs_mtr_vs_pay,
            "tcs_mtr_vs_statutory": tcs_mtr_vs_statutory,
            "tcs_pay_vs_gstr8": tcs_pay_vs_gstr8,
            "tcs_matched": abs(tcs_mtr_vs_pay) <= tolerance,
            "expected_tds_statutory": expected_tds_statutory,
            "pay_tds_total": pay_tds_total,
            "form26as_tds": form26as_tds,
            "tds_pay_vs_statutory": tds_pay_vs_statutory,
            "tds_pay_vs_26as": tds_pay_vs_26as,
            "tds_matched": abs(tds_pay_vs_statutory) <= tolerance
        },
        "breakdown": {
            "pay_tcs_cgst": pay_tcs_cgst,
            "pay_tcs_sgst": pay_tcs_sgst,
            "pay_tcs_igst": pay_tcs_igst
        },
        "anomalies": anomalies
    }
