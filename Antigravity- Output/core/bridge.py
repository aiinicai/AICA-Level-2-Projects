"""
Financial Bridge & Waterfall Analysis for MarketMatch.
Pure functions to build:
1. Executive Waterfall:
   Sales -> Returns -> Fees -> GST on Fees -> TCS -> TDS -> Expected Payout -> Actual Payout -> Unexplained
2. Month-wise side-by-side reconciliation bridge (Sales, GST, Payout, Explained vs Unexplained).
"""
from decimal import Decimal
from typing import Dict, Any, List
import plotly.graph_objects as go


def compute_waterfall_data(kpi_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate waterfall breakdown items:
    Gross Sales -> Returns (-) -> Fees (-) -> GST on fees (-) -> TCS (-) -> TDS (-) -> Expected Payout -> Actual Payout -> Unexplained
    """
    gross_sales = float(kpi_summary.get("total_gross_sales", Decimal("0.00")))
    returns = float(kpi_summary.get("total_refunds", Decimal("0.00")))
    selling_fees = float(kpi_summary.get("total_selling_fees", Decimal("0.00")))
    fba_fees = float(kpi_summary.get("total_fba_fees", Decimal("0.00")))
    other_fees = float(kpi_summary.get("total_other_fees", Decimal("0.00")))
    all_fees = selling_fees + fba_fees + other_fees
    gst_on_fees = float(kpi_summary.get("total_gst_on_fees", Decimal("0.00")))
    tcs = float(kpi_summary.get("total_tcs", Decimal("0.00")))
    tds = float(kpi_summary.get("total_tds", Decimal("0.00")))
    expected_payout = float(kpi_summary.get("total_expected_payout", Decimal("0.00")))
    actual_payout = float(kpi_summary.get("total_actual_payout", Decimal("0.00")))
    unexplained = float(kpi_summary.get("total_unexplained", Decimal("0.00")))

    steps = [
        {"name": "Gross Sales", "amount": gross_sales, "type": "relative"},
        {"name": "Returns & Refunds", "amount": -returns, "type": "relative"},
        {"name": "Marketplace Fees", "amount": -all_fees, "type": "relative"},
        {"name": "GST on Fees", "amount": -gst_on_fees, "type": "relative"},
        {"name": "TCS (GST)", "amount": -tcs, "type": "relative"},
        {"name": "TDS (194-O)", "amount": -tds, "type": "relative"},
        {"name": "Expected Net Payout", "amount": expected_payout, "type": "total"},
        {"name": "Discrepancy (Unexplained)", "amount": unexplained, "type": "relative"},
        {"name": "Actual Net Payout", "amount": actual_payout, "type": "total"}
    ]
    return steps


def create_waterfall_figure(waterfall_data: List[Dict[str, Any]]) -> go.Figure:
    """
    Build Plotly Waterfall Chart matching standard Indian financial themes.
    """
    x_labels = [item["name"] for item in waterfall_data]
    y_values = [item["amount"] for item in waterfall_data]
    measures = [item["type"] for item in waterfall_data]

    fig = go.Figure(go.Waterfall(
        name="Reconciliation Bridge",
        orientation="v",
        measure=measures,
        x=x_labels,
        y=y_values,
        textposition="outside",
        text=[f"₹ {abs(v):,.2f}" if v != 0 else "₹ 0" for v in y_values],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#28a745"}},
        decreasing={"marker": {"color": "#dc3545"}},
        totals={"marker": {"color": "#0d6efd"}}
    ))

    fig.update_layout(
        title="Executive Waterfall: Sales to Payout Bridge",
        waterfallgap=0.3,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="sans-serif", size=12),
        margin=dict(l=40, r=40, t=50, b=40),
        yaxis=dict(title="Amount in INR (₹)", gridcolor="#e9ecef")
    )
    return fig


def compute_month_wise_bridge(
    mtr_records: List[Dict[str, Any]],
    gst_sections: Dict[str, List[Dict[str, Any]]],
    payment_records: List[Dict[str, Any]],
    order_reconciliation: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Compute month-wise comparison table:
    Month | Gross Sales | Net Sales | GST Reported Taxable | Payout Released | Payout Deferred | Total Fees & Taxes | Explained Diff | Unexplained Diff
    """
    # Group by YYYY-MM
    months_set = set()
    for r in mtr_records:
        if r.get("invoice_date"):
            months_set.add(r["invoice_date"][:7])
    for p in payment_records:
        if p.get("settlement_date"):
            months_set.add(p["settlement_date"][:7])

    rows = []
    for ym in sorted(months_set):
        # MTR for this month
        m_rows = [r for r in mtr_records if (r.get("invoice_date") or "").startswith(ym)]
        gross_sales = sum((r["invoice_value"] for r in m_rows if not r["is_return"]), Decimal("0.00"))
        refunds = sum((abs(r["invoice_value"]) for r in m_rows if r["is_return"]), Decimal("0.00"))
        net_sales = gross_sales - refunds

        # GST reported for this month
        # Note: B2CS + B2CL + B2B
        gst_b2cs = sum((r["taxable_value"] for r in gst_sections.get("b2cs", [])), Decimal("0.00"))
        gst_b2cl = sum((r["taxable_value"] for r in gst_sections.get("b2cl", [])), Decimal("0.00"))
        gst_reported = gst_b2cs + gst_b2cl

        # Payments for this month
        p_rows = [p for p in payment_records if (p.get("settlement_date") or "").startswith(ym)]
        released = sum((p["net_payout"] for p in p_rows if not p.get("is_deferred")), Decimal("0.00"))
        deferred = sum((p["net_payout"] for p in p_rows if p.get("is_deferred")), Decimal("0.00"))
        actual_payout = released + deferred

        fees = sum((abs(p["selling_fees"]) + abs(p["fba_fees"]) + abs(p["other_transaction_fees"]) + abs(p["other"]) for p in p_rows), Decimal("0.00"))
        taxes = sum((abs(p["tcs_total"]) + abs(p["tds"]) for p in p_rows), Decimal("0.00"))

        # Orders in this month
        month_orders = [o for o in order_reconciliation if (o.get("invoice_date") or "").startswith(ym)]
        unexplained = sum((o["unexplained"] for o in month_orders), Decimal("0.00"))
        # Explained diff = net sales - actual payout - unexplained
        explained = (net_sales - actual_payout) - unexplained

        rows.append({
            "period": ym,
            "gross_sales": gross_sales,
            "refunds": refunds,
            "net_sales": net_sales,
            "gst_taxable": gst_reported,
            "payout_released": released,
            "payout_deferred": deferred,
            "payout_total": actual_payout,
            "fees_and_taxes": fees + taxes,
            "explained_difference": explained,
            "unexplained_difference": unexplained
        })

    return rows
