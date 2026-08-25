"""Tests for app/analysis/peers.py."""

from __future__ import annotations

from app.core.enums import DataStatus, UnitOfMeasure
from app.core.models import MetricResult
from app.analysis.peers import (
    PEER_SET_SONA_BLW,
    PeerCompanyMultiples,
    compare_to_own_history,
    compare_to_peers,
)


def _mr(name: str, value: float | None, status: DataStatus = DataStatus.OK) -> MetricResult:
    return MetricResult(
        metric_name=name, formula="test", inputs={}, value=value,
        unit=UnitOfMeasure.RATIO, period="FY2026", status=status,
    )


class TestPeerSetReference:
    def test_peer_set_contains_all_specified_companies(self):
        assert "Uno Minda" in PEER_SET_SONA_BLW
        assert "Gabriel India" in PEER_SET_SONA_BLW
        assert "Lumax Auto Technologies" in PEER_SET_SONA_BLW
        assert "Lumax Industries" in PEER_SET_SONA_BLW
        assert len(PEER_SET_SONA_BLW) == 7


class TestCompareToPeers:
    def test_premium_calculated_correctly(self):
        company = {"P/E": _mr("P/E", 40.0)}
        peers = [
            PeerCompanyMultiples(company_name="A", period="FY2026", pe=20.0, source="test"),
            PeerCompanyMultiples(company_name="B", period="FY2026", pe=30.0, source="test"),
            PeerCompanyMultiples(company_name="C", period="FY2026", pe=40.0, source="test"),
        ]
        results = compare_to_peers(company, peers)
        assert len(results) == 1
        r = results[0]
        assert r.peer_median == 30.0
        assert r.status == DataStatus.OK
        assert abs(r.premium_discount_pct - round((40.0 - 30.0) / 30.0, 4)) < 1e-6

    def test_discount_is_negative(self):
        company = {"P/E": _mr("P/E", 15.0)}
        peers = [
            PeerCompanyMultiples(company_name="A", period="FY2026", pe=20.0, source="test"),
            PeerCompanyMultiples(company_name="B", period="FY2026", pe=20.0, source="test"),
        ]
        results = compare_to_peers(company, peers)
        assert results[0].premium_discount_pct < 0

    def test_missing_company_value_returns_missing_input(self):
        company = {"P/E": _mr("P/E", None, status=DataStatus.MISSING_INPUT)}
        peers = [PeerCompanyMultiples(company_name="A", period="FY2026", pe=20.0, source="test")]
        results = compare_to_peers(company, peers)
        assert results[0].status == DataStatus.MISSING_INPUT
        assert results[0].peer_median is None

    def test_no_peer_data_for_multiple_returns_unavailable(self):
        company = {"EV/Sales": _mr("EV/Sales", 3.0)}
        peers = [
            PeerCompanyMultiples(company_name="A", period="FY2026", pe=20.0, source="test"),  # no ev_sales
        ]
        results = compare_to_peers(company, peers)
        assert results[0].status == DataStatus.UNAVAILABLE
        assert results[0].peer_median is None
        # company's own value must still be preserved even though comparison is unavailable
        assert results[0].company_value == 3.0

    def test_partial_peer_coverage_uses_only_peers_with_data(self):
        company = {"P/B": _mr("P/B", 5.0)}
        peers = [
            PeerCompanyMultiples(company_name="A", period="FY2026", pb=4.0, source="test"),
            PeerCompanyMultiples(company_name="B", period="FY2026", pb=None, source="test"),  # missing
            PeerCompanyMultiples(company_name="C", period="FY2026", pb=6.0, source="test"),
        ]
        results = compare_to_peers(company, peers)
        assert results[0].peer_count == 3
        assert results[0].peers_with_data == 2
        assert results[0].peer_median == 5.0  # median of [4.0, 6.0]

    def test_unrecognized_multiple_name_skipped_not_crashed(self):
        company = {"Some Custom Metric": _mr("Some Custom Metric", 1.0)}
        peers = [PeerCompanyMultiples(company_name="A", period="FY2026", pe=20.0, source="test")]
        results = compare_to_peers(company, peers)
        assert results == []  # not a known multiple -> silently skipped, no crash

    def test_zero_peer_median_does_not_raise_division_error(self):
        company = {"EV/Sales": _mr("EV/Sales", 5.0)}
        peers = [
            PeerCompanyMultiples(company_name="A", period="FY2026", ev_sales=0.0, source="test"),
            PeerCompanyMultiples(company_name="B", period="FY2026", ev_sales=0.0, source="test"),
        ]
        results = compare_to_peers(company, peers)  # median = 0.0 -> must not raise
        assert results[0].premium_discount_pct is None


class TestCompareToOwnHistory:
    def test_historical_median_comparison(self):
        current = _mr("P/E", 45.0)
        history = [_mr("P/E", 30.0), _mr("P/E", 35.0), _mr("P/E", 40.0)]
        result = compare_to_own_history(current, history)
        assert result.peer_median == 35.0
        assert result.status == DataStatus.OK
        assert result.premium_discount_pct > 0

    def test_empty_history_returns_unavailable(self):
        current = _mr("P/E", 45.0)
        result = compare_to_own_history(current, [])
        assert result.status == DataStatus.UNAVAILABLE
        assert result.company_value == 45.0
