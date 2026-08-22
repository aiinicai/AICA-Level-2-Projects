"""Tests for the Valuation Dashboard's peer-upload and DCF
scenario/sensitivity helper functions (all pure, no Streamlit calls)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.core.enums import DataStatus, UnitOfMeasure
from app.core.models import MetricResult
from app.valuation.dcf import DCFAssumptions
from app.valuation.scenarios import (
    ScenarioSet, build_conservative_bear_case, build_optimistic_bull_case, run_scenarios,
)
from app.ui.pages.valuation_dashboard import (
    build_peer_multiples_from_workbook,
    build_sensitivity_range,
    extract_company_multiples_dict,
    peer_comparisons_to_rows,
    scenario_set_to_rows,
    sensitivity_grid_to_rows,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_EXCEL = PROJECT_ROOT / "data" / "sample" / "Sona_BLW_Precis_screener_export.xlsx"


@pytest.fixture
def synthetic_peer_workbook(tmp_path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Data Sheet"
    ws.append(["COMPANY NAME", "Test Peer Co"])
    ws.append([])
    ws.append(["PROFIT & LOSS"])
    ws.append(["Report Date", datetime(2025, 3, 31), datetime(2026, 3, 31)])
    ws.append(["Sales", 1000.0, 1200.0])
    ws.append(["Net profit", 100.0, 130.0])
    ws.append(["BALANCE SHEET"])
    ws.append(["Report Date", datetime(2025, 3, 31), datetime(2026, 3, 31)])
    ws.append(["Equity Share Capital", 50.0, 50.0])
    ws.append(["Reserves", 500.0, 600.0])
    ws.append(["Borrowings", 100.0, 90.0])
    ws.append(["No. of Equity Shares", 50_000_000.0, 50_000_000.0])
    ws.append(["Face value", 10.0, 10.0])
    ws.append(["CASH FLOW:"])
    ws.append(["Report Date", datetime(2025, 3, 31), datetime(2026, 3, 31)])
    ws.append(["Cash from Operating Activity", 90.0, 110.0])
    ws.append(["PRICE:", "", 250.0])
    path = tmp_path / "peer.xlsx"
    wb.save(path)
    return path


class TestBuildPeerMultiplesFromWorkbook:
    def test_parses_peer_name_and_period(self, synthetic_peer_workbook):
        peer = build_peer_multiples_from_workbook(synthetic_peer_workbook, "Test Peer Co")
        assert peer.company_name == "Test Peer Co"
        assert peer.period == "FY2026"

    def test_pe_computed_correctly(self, synthetic_peer_workbook):
        peer = build_peer_multiples_from_workbook(synthetic_peer_workbook, "Test Peer Co")
        assert peer.pe == pytest.approx(9.62, abs=0.01)

    def test_pb_computed_correctly(self, synthetic_peer_workbook):
        peer = build_peer_multiples_from_workbook(synthetic_peer_workbook, "Test Peer Co")
        assert peer.pb == pytest.approx(1.92, abs=0.01)

    def test_ev_based_multiples_unavailable_when_cash_missing(self, synthetic_peer_workbook):
        peer = build_peer_multiples_from_workbook(synthetic_peer_workbook, "Test Peer Co")
        assert peer.ev_ebitda is None
        assert peer.ev_sales is None

    def test_source_filename_recorded(self, synthetic_peer_workbook):
        peer = build_peer_multiples_from_workbook(synthetic_peer_workbook, "Test Peer Co")
        assert peer.source == "peer.xlsx"


class TestExtractCompanyMultiplesDict:
    def test_filters_to_comparable_multiples_only(self):
        metrics = [
            MetricResult(metric_name="Market Capitalization", formula="f", inputs={}, value=1000.0,
                         unit=UnitOfMeasure.INR_CRORE, period="FY2026", status=DataStatus.OK),
            MetricResult(metric_name="P/E", formula="f", inputs={}, value=20.0,
                         unit=UnitOfMeasure.RATIO, period="FY2026", status=DataStatus.OK),
        ]
        result = extract_company_multiples_dict(metrics)
        assert "P/E" in result
        assert "Market Capitalization" not in result

    def test_empty_input_returns_empty_dict(self):
        assert extract_company_multiples_dict([]) == {}


class TestPeerComparisonRealData:
    def test_full_pipeline_real_sona_blw_vs_synthetic_peer(self, synthetic_peer_workbook):
        from app.data.loaders import load_screener_excel
        from app.data.financial_data import build_canonical_statements
        from app.valuation.multiples import compute_all_multiples
        from app.analysis.peers import compare_to_peers

        raw = load_screener_excel(SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd")
        statements = build_canonical_statements(raw)
        fy26 = statements[-1]
        val_metrics = compute_all_multiples(fy26)
        company_dict = extract_company_multiples_dict(val_metrics)

        peer = build_peer_multiples_from_workbook(synthetic_peer_workbook, "Test Peer Co")
        comparisons = compare_to_peers(company_dict, [peer])

        pe_comparison = next(c for c in comparisons if c.multiple_name == "P/E")
        assert pe_comparison.status == DataStatus.OK
        assert pe_comparison.company_value > pe_comparison.peer_median

        ev_ebitda_comparison = next(c for c in comparisons if c.multiple_name == "EV/EBITDA")
        assert ev_ebitda_comparison.status == DataStatus.UNAVAILABLE

    def test_peer_comparisons_to_rows_formats_correctly(self, synthetic_peer_workbook):
        from app.data.loaders import load_screener_excel
        from app.data.financial_data import build_canonical_statements
        from app.valuation.multiples import compute_all_multiples
        from app.analysis.peers import compare_to_peers

        raw = load_screener_excel(SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd")
        statements = build_canonical_statements(raw)
        val_metrics = compute_all_multiples(statements[-1])
        company_dict = extract_company_multiples_dict(val_metrics)
        peer = build_peer_multiples_from_workbook(synthetic_peer_workbook, "Test Peer Co")
        comparisons = compare_to_peers(company_dict, [peer])

        rows = peer_comparisons_to_rows(comparisons)
        pe_row = next(r for r in rows if r["Multiple"] == "P/E")
        assert "+" in pe_row["Premium/Discount"]


class TestBuildSensitivityRange:
    def test_symmetric_range_around_center(self):
        result = build_sensitivity_range(0.12, 0.01, 5)
        assert result == [0.10, 0.11, 0.12, 0.13, 0.14]

    def test_center_is_middle_element(self):
        result = build_sensitivity_range(0.12, 0.02, 5)
        assert result[2] == 0.12

    def test_three_element_range(self):
        result = build_sensitivity_range(0.05, 0.01, 3)
        assert result == [0.04, 0.05, 0.06]


class TestScenarioAndSensitivityDisplay:
    def _base_assumptions(self):
        return DCFAssumptions(
            projection_years=5, revenue_growth_rate=0.15, ebitda_margin=0.25,
            depreciation_pct_of_revenue=0.06, capex_pct_of_revenue=0.10,
            wc_change_pct_of_revenue_change=0.05, tax_rate=0.25, wacc=0.12, terminal_growth_rate=0.05,
        )

    def test_scenario_set_to_rows_bear_base_bull_ordering(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        base = self._base_assumptions()
        bear = build_conservative_bear_case(base, growth_haircut=0.06, margin_haircut=0.04)
        bull = build_optimistic_bull_case(base, growth_uplift=0.05, margin_uplift=0.03)
        scenario_set = run_scenarios(fy26, bear_assumptions=bear, base_assumptions=base, bull_assumptions=bull)

        rows = scenario_set_to_rows(scenario_set)
        assert len(rows) == 3
        assert rows[0]["Scenario"] == "Bear"
        assert rows[1]["Scenario"] == "Base"
        assert rows[2]["Scenario"] == "Bull"
        for row in rows:
            assert "\u20b9" in row["Value Per Share"]

    def test_scenario_set_to_rows_handles_failed_scenario(self):
        failed_set = ScenarioSet(
            bear=None, base=None, bull=None,
            bear_status_note="missing data", base_status_note="missing data", bull_status_note="missing data",
        )
        rows = scenario_set_to_rows(failed_set)
        assert all("N/A" in r["Value Per Share"] for r in rows)
        assert all("missing data" in r["Value Per Share"] for r in rows)

    def test_sensitivity_grid_to_rows_shape(self, sona_blw_statements):
        from app.valuation.dcf import sensitivity_analysis

        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        base = self._base_assumptions()
        wacc_range = build_sensitivity_range(base.wacc, 0.01, 3)
        tg_range = build_sensitivity_range(base.terminal_growth_rate, 0.01, 3)
        grid = sensitivity_analysis(fy26, base, wacc_range=wacc_range, terminal_growth_range=tg_range)

        rows = sensitivity_grid_to_rows(grid)
        assert len(rows) == 3
        assert all(len(r) == 4 for r in rows)

    def test_sensitivity_grid_invalid_combo_shows_na(self, sona_blw_statements):
        from app.valuation.dcf import sensitivity_analysis

        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        base = self._base_assumptions()
        grid = sensitivity_analysis(fy26, base, wacc_range=[0.03], terminal_growth_range=[0.05])
        rows = sensitivity_grid_to_rows(grid)
        assert rows[0]["g=5.0%"] == "N/A"
