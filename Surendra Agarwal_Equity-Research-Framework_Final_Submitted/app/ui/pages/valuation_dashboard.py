"""Valuation Dashboard page - current price, multiples, DCF, peer comparison.

Peer comparison and DCF scenarios/sensitivity are built on top of
already-tested engines (app/analysis/peers.py, app/valuation/scenarios.py,
app/valuation/dcf.py) - this page only uploads/collects inputs and
displays results; it performs no financial calculations itself.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import streamlit as st

from app.core.enums import DataStatus
from app.core.models import FinancialStatement

logger = logging.getLogger(__name__)


def multiples_to_rows(metrics: list) -> list[dict]:
    """Pure function: MetricResult list -> table rows."""
    rows = []
    for m in metrics:
        value_str = f"{m.value:,.2f}" if m.value is not None else "N/A"
        rows.append({"Multiple": m.metric_name, "Value": value_str, "Status": m.status.value})
    return rows


def extract_company_multiples_dict(valuation_metrics: list) -> dict:
    """Pure function: valuation_metrics list -> {metric_name: MetricResult},
    filtered to just the four multiples peers.py knows how to compare
    (Market Cap and Enterprise Value are inputs to those, not themselves
    comparable multiples)."""
    comparable_names = {"P/E", "EV/EBITDA", "P/B", "EV/Sales"}
    return {m.metric_name: m for m in valuation_metrics if m.metric_name in comparable_names}


def build_peer_multiples_from_workbook(excel_path: Path, peer_company_name: str):
    """Pure function: parse a peer's Screener.in Excel export and compute
    its multiples for the latest period, returning a PeerCompanyMultiples
    object. Reuses the exact same loaders/multiples pipeline used for the
    subject company - a peer's P/E is computed identically, not estimated
    differently."""
    from app.data.loaders import load_screener_excel
    from app.data.financial_data import build_canonical_statements
    from app.valuation.multiples import compute_all_multiples
    from app.analysis.peers import PeerCompanyMultiples

    raw = load_screener_excel(excel_path, company_name=peer_company_name)
    statements = build_canonical_statements(raw)
    if not statements:
        return None
    latest = statements[-1]
    multiples = {m.metric_name: m for m in compute_all_multiples(latest)}

    def _val(name):
        m = multiples.get(name)
        return m.value if m and m.status == DataStatus.OK else None

    return PeerCompanyMultiples(
        company_name=peer_company_name, period=latest.period,
        pe=_val("P/E"), ev_ebitda=_val("EV/EBITDA"), pb=_val("P/B"), ev_sales=_val("EV/Sales"),
        source=excel_path.name,
    )


def peer_comparisons_to_rows(comparisons: list) -> list[dict]:
    """Pure function: PeerComparisonResult list -> table rows."""
    rows = []
    for c in comparisons:
        rows.append({
            "Multiple": c.multiple_name,
            "Company": f"{c.company_value:,.2f}" if c.company_value is not None else "N/A",
            "Peer Median": f"{c.peer_median:,.2f}" if c.peer_median is not None else "N/A",
            "Premium/Discount": f"{c.premium_discount_pct:+.1%}" if c.premium_discount_pct is not None else "N/A",
            "Peers w/ Data": f"{c.peers_with_data}/{c.peer_count}",
            "Status": c.status.value,
        })
    return rows


def build_sensitivity_range(center: float, step: float, count: int = 5) -> list[float]:
    """Pure function: symmetric range of `count` values around `center`,
    spaced by `step`. E.g. center=0.12, step=0.02, count=5 ->
    [0.08, 0.10, 0.12, 0.14, 0.16]."""
    half = count // 2
    return [round(center + (i - half) * step, 4) for i in range(count)]


def sensitivity_grid_to_rows(grid: dict) -> list[dict]:
    """Pure function: sensitivity_analysis()'s nested dict ->
    table rows, one row per WACC with a column per terminal growth rate."""
    rows = []
    for wacc_key, row in grid.items():
        row_data = {"WACC": wacc_key}
        for tg_key, value in row.items():
            row_data[f"g={tg_key}"] = f"{value:,.2f}" if value is not None else "N/A"
        rows.append(row_data)
    return rows


def scenario_set_to_rows(scenario_set) -> list[dict]:
    """Pure function: ScenarioSet -> table rows for display."""
    rows = []
    for label, result, note in (
        ("Bear", scenario_set.bear, scenario_set.bear_status_note),
        ("Base", scenario_set.base, scenario_set.base_status_note),
        ("Bull", scenario_set.bull, scenario_set.bull_status_note),
    ):
        if result is not None:
            rows.append({"Scenario": label, "Value Per Share": f"₹{result.value_per_share:,.2f}"})
        else:
            rows.append({"Scenario": label, "Value Per Share": f"N/A ({note})"})
    return rows


def render() -> None:
    st.header("Valuation Dashboard")

    company = st.session_state.get("company")
    if company is None:
        st.info("Load a company on the Company Input page first.")
        return

    valuation_metrics = st.session_state.get("valuation_metrics", [])
    if valuation_metrics:
        st.subheader("Relative Valuation")
        st.table(multiples_to_rows(valuation_metrics))
    else:
        st.info("No valuation multiples computed yet.")

    # ----------------------------------------------------------------
    # Peer comparison
    # ----------------------------------------------------------------
    st.subheader("Peer Comparison")
    st.caption(
        "Upload one or more peer companies' Screener.in Excel exports. Each "
        "peer's multiples are computed with the exact same pipeline used for "
        "the subject company. The uploaded file's name (minus extension) is "
        "used as the peer's display name — name your files accordingly "
        "(e.g. 'Uno Minda.xlsx')."
    )
    peer_files = st.file_uploader(
        "Peer Financials (Screener.in Excel exports)", type=["xlsx"], accept_multiple_files=True,
    )

    if st.button("Compute Peer Comparison"):
        if not peer_files:
            st.error("Upload at least one peer Excel file first.")
        else:
            peers = []
            with tempfile.TemporaryDirectory() as tmpdir:
                for f in peer_files:
                    peer_name = Path(f.name).stem
                    tmp_path = Path(tmpdir) / f.name
                    tmp_path.write_bytes(f.getvalue())
                    try:
                        peer = build_peer_multiples_from_workbook(tmp_path, peer_name)
                        if peer is not None:
                            peers.append(peer)
                    except Exception as exc:
                        logger.warning("Failed to parse peer file %s: %s", f.name, exc)
                        st.warning(f"Could not parse {f.name}: {exc}")

            if peers:
                from app.analysis.peers import compare_to_peers

                company_multiples = extract_company_multiples_dict(valuation_metrics)
                comparisons = compare_to_peers(company_multiples, peers)
                st.session_state["peer_comparisons"] = comparisons
                st.session_state["peers"] = peers
                st.success(f"Loaded {len(peers)} peer(s): {', '.join(p.company_name for p in peers)}")
            else:
                st.error("No peer files could be parsed successfully.")

    peer_comparisons = st.session_state.get("peer_comparisons", [])
    if peer_comparisons:
        st.table(peer_comparisons_to_rows(peer_comparisons))
        peers_loaded = st.session_state.get("peers", [])
        if peers_loaded:
            st.caption(f"Peers: {', '.join(p.company_name for p in peers_loaded)}")

    # ----------------------------------------------------------------
    # DCF
    # ----------------------------------------------------------------
    st.subheader("DCF Valuation")
    st.caption(
        "Run a DCF with your own assumptions. Every input below is an explicit "
        "assumption — there is no hidden default."
    )

    statements = st.session_state.get("statements", [])
    if not statements:
        st.info("Load financials first to run a DCF.")
        return

    with st.form("dcf_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            revenue_growth = st.number_input("Revenue Growth Rate", value=0.12, step=0.01, format="%.2f")
            ebitda_margin = st.number_input("EBITDA Margin", value=0.22, step=0.01, format="%.2f")
        with col2:
            wacc = st.number_input("WACC", value=0.12, step=0.01, format="%.2f")
            terminal_growth = st.number_input("Terminal Growth Rate", value=0.05, step=0.01, format="%.2f")
        with col3:
            tax_rate = st.number_input("Tax Rate", value=0.25, step=0.01, format="%.2f")
            projection_years = st.number_input("Projection Years", value=5, min_value=1, max_value=10)

        run_dcf_clicked = st.form_submit_button("Run DCF")

    if run_dcf_clicked:
        from app.valuation.dcf import DCFAssumptions, DCFResult, run_dcf

        try:
            assumptions = DCFAssumptions(
                projection_years=int(projection_years), revenue_growth_rate=revenue_growth,
                ebitda_margin=ebitda_margin, depreciation_pct_of_revenue=0.06,
                capex_pct_of_revenue=0.08, wc_change_pct_of_revenue_change=0.03,
                tax_rate=tax_rate, wacc=wacc, terminal_growth_rate=terminal_growth,
            )
        except ValueError as exc:
            st.error(str(exc))
            return

        result = run_dcf(statements[-1], assumptions)
        st.session_state["last_dcf_assumptions"] = assumptions
        if isinstance(result, DCFResult):
            st.success(f"DCF Value Per Share: ₹{result.value_per_share:,.2f}")
            st.caption(result.DISCLAIMER)
            for note in result.data_quality_notes:
                st.warning(note)
        else:
            st.error(f"DCF could not be computed: {'; '.join(result.data_quality_notes)}")

    base_assumptions = st.session_state.get("last_dcf_assumptions")
    if base_assumptions is None:
        st.info("Run a DCF above first to unlock scenarios and sensitivity analysis.")
        return

    # ----------------------------------------------------------------
    # Bear / Base / Bull scenarios
    # ----------------------------------------------------------------
    st.markdown("---")
    st.subheader("Bear / Base / Bull Scenarios")
    st.caption(
        "Base uses the assumptions from the DCF form above. Bear/Bull are "
        "explicit haircuts/uplifts to growth and margin — adjust the "
        "magnitudes below; nothing is auto-derived."
    )

    with st.form("scenario_form"):
        col1, col2 = st.columns(2)
        with col1:
            growth_haircut = st.number_input("Bear: Growth Haircut", value=0.06, step=0.01, format="%.2f")
            margin_haircut = st.number_input("Bear: Margin Haircut", value=0.04, step=0.01, format="%.2f")
        with col2:
            growth_uplift = st.number_input("Bull: Growth Uplift", value=0.05, step=0.01, format="%.2f")
            margin_uplift = st.number_input("Bull: Margin Uplift", value=0.03, step=0.01, format="%.2f")
        run_scenarios_clicked = st.form_submit_button("Run Bear/Base/Bull Scenarios")

    if run_scenarios_clicked:
        from app.valuation.scenarios import (
            build_conservative_bear_case, build_optimistic_bull_case, run_scenarios,
        )

        bear = build_conservative_bear_case(base_assumptions, growth_haircut=growth_haircut, margin_haircut=margin_haircut)
        bull = build_optimistic_bull_case(base_assumptions, growth_uplift=growth_uplift, margin_uplift=margin_uplift)
        scenario_set = run_scenarios(
            statements[-1], bear_assumptions=bear, base_assumptions=base_assumptions, bull_assumptions=bull,
        )
        st.session_state["scenario_set"] = scenario_set

    scenario_set = st.session_state.get("scenario_set")
    if scenario_set:
        cols = st.columns(3)
        rows = scenario_set_to_rows(scenario_set)
        for col, row in zip(cols, rows):
            col.metric(row["Scenario"], row["Value Per Share"])
        st.caption(
            "Decision-support estimates under stated assumptions, not a guarantee "
            "or prediction of future price."
        )

    # ----------------------------------------------------------------
    # Sensitivity analysis
    # ----------------------------------------------------------------
    st.markdown("---")
    st.subheader("Sensitivity Analysis (WACC x Terminal Growth)")

    with st.form("sensitivity_form"):
        col1, col2 = st.columns(2)
        with col1:
            wacc_step = st.number_input("WACC Step", value=0.01, step=0.005, format="%.3f")
        with col2:
            terminal_step = st.number_input("Terminal Growth Step", value=0.01, step=0.005, format="%.3f")
        run_sensitivity_clicked = st.form_submit_button("Run Sensitivity Analysis")

    if run_sensitivity_clicked:
        from app.valuation.dcf import sensitivity_analysis

        wacc_range = build_sensitivity_range(base_assumptions.wacc, wacc_step, 5)
        wacc_range = [w for w in wacc_range if w > 0]
        tg_range = build_sensitivity_range(base_assumptions.terminal_growth_rate, terminal_step, 5)
        tg_range = [g for g in tg_range if g >= 0]

        grid = sensitivity_analysis(
            statements[-1], base_assumptions, wacc_range=wacc_range, terminal_growth_range=tg_range,
        )
        st.session_state["sensitivity_grid"] = grid

    sensitivity_grid = st.session_state.get("sensitivity_grid")
    if sensitivity_grid:
        st.caption("Rows = WACC, columns = Terminal Growth Rate. Value per share (₹). 'N/A' = WACC <= terminal growth (invalid combination).")
        st.table(sensitivity_grid_to_rows(sensitivity_grid))
