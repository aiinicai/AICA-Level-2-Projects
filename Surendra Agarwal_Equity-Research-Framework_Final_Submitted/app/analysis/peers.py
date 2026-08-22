"""Peer relative valuation — Module 7.

This module NEVER fetches or fabricates peer multiples itself. Peer
data (P/E, EV/EBITDA, P/B, EV/Sales for each named peer) must be
supplied by the caller as PeerCompanyMultiples objects — typically
sourced from the same market-data/financial-statement pipeline used for
the subject company, or entered manually by the analyst. This keeps
peer selection and peer data provenance an explicit, auditable input
(Principle 4: no silent assumptions) rather than something this module
silently decides on its own.

The person's specified peer set for Sona BLW (auto-ancillary /
EV-driveline): Samvardhana Motherson, Uno Minda, Endurance Technologies,
Gabriel India, Varroc Engineering, Lumax Auto Technologies, Lumax
Industries — see PEER_SET_SONA_BLW below as a labeled reference list,
not a source of actual multiple values.
"""

from __future__ import annotations

import statistics

from pydantic import BaseModel, Field

from app.core.enums import ConfidenceLevel, DataStatus, UnitOfMeasure
from app.core.models import MetricResult

# Reference peer list only — a name list, not a data source. Actual
# multiples for each peer must be supplied separately (see
# PeerCompanyMultiples) with their own lineage/confidence, never
# assumed or interpolated from this list.
PEER_SET_SONA_BLW: list[str] = [
    "Samvardhana Motherson International",
    "Uno Minda",
    "Endurance Technologies",
    "Gabriel India",
    "Varroc Engineering",
    "Lumax Auto Technologies",
    "Lumax Industries",
]


class PeerCompanyMultiples(BaseModel):
    """Externally supplied valuation multiples for one peer company.

    Every field is optional and independently nullable — a peer with a
    missing EV/EBITDA (e.g. negative EBITDA) should not block using its
    P/E, and vice versa.
    """

    company_name: str
    period: str = Field(..., description="e.g. 'FY2026' or 'TTM' — must match the subject company's period for a fair comparison")
    pe: float | None = None
    ev_ebitda: float | None = None
    pb: float | None = None
    ev_sales: float | None = None
    source: str = Field(..., description="Where this peer's multiples came from, e.g. 'Screener.in, 2026-08-10'")
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class PeerComparisonResult(BaseModel):
    """Company multiple vs. peer median, for one multiple type."""

    multiple_name: str
    company_value: float | None
    peer_median: float | None
    peer_count: int
    peers_with_data: int
    premium_discount_pct: float | None = Field(
        default=None, description="(company_value - peer_median) / peer_median; positive = trading at a premium"
    )
    status: DataStatus


def compare_to_peers(
    company_multiples: dict[str, MetricResult],
    peers: list[PeerCompanyMultiples],
) -> list[PeerComparisonResult]:
    """Compare the subject company's multiples (as produced by
    valuation/multiples.py) against the median of the supplied peer set.

    Args:
        company_multiples: dict keyed by multiple name ("P/E", "EV/EBITDA",
            "P/B", "EV/Sales") -> that MetricResult, e.g. the output of
            valuation.multiples.compute_all_multiples() filtered/keyed
            by metric_name.
        peers: externally supplied peer data — never fetched here.

    Returns:
        One PeerComparisonResult per multiple type present in
        company_multiples.
    """
    results: list[PeerComparisonResult] = []
    field_map = {"P/E": "pe", "EV/EBITDA": "ev_ebitda", "P/B": "pb", "EV/Sales": "ev_sales"}

    for multiple_name, company_result in company_multiples.items():
        field_name = field_map.get(multiple_name)
        if field_name is None:
            continue  # not a multiple this module knows how to compare against peers

        peer_values = [
            getattr(p, field_name) for p in peers if getattr(p, field_name) is not None
        ]

        if company_result.status != DataStatus.OK or company_result.value is None:
            results.append(
                PeerComparisonResult(
                    multiple_name=multiple_name, company_value=None, peer_median=None,
                    peer_count=len(peers), peers_with_data=len(peer_values),
                    status=DataStatus.MISSING_INPUT,
                )
            )
            continue

        if not peer_values:
            results.append(
                PeerComparisonResult(
                    multiple_name=multiple_name, company_value=company_result.value,
                    peer_median=None, peer_count=len(peers), peers_with_data=0,
                    status=DataStatus.UNAVAILABLE,
                )
            )
            continue

        peer_median = statistics.median(peer_values)
        premium_discount = (
            (company_result.value - peer_median) / peer_median if peer_median != 0 else None
        )
        results.append(
            PeerComparisonResult(
                multiple_name=multiple_name, company_value=company_result.value,
                peer_median=round(peer_median, 2), peer_count=len(peers),
                peers_with_data=len(peer_values),
                premium_discount_pct=round(premium_discount, 4) if premium_discount is not None else None,
                status=DataStatus.OK,
            )
        )

    return results


def compare_to_own_history(
    current_result: MetricResult, historical_results: list[MetricResult]
) -> PeerComparisonResult:
    """Compare a current multiple against the company's own historical
    median for that same multiple (e.g. current P/E vs its 5-year median
    P/E) — same shape as peer comparison, so report generation can treat
    both the same way."""
    historical_values = [r.value for r in historical_results if r.status == DataStatus.OK and r.value is not None]

    if current_result.status != DataStatus.OK or current_result.value is None:
        return PeerComparisonResult(
            multiple_name=current_result.metric_name, company_value=None, peer_median=None,
            peer_count=len(historical_results), peers_with_data=len(historical_values),
            status=DataStatus.MISSING_INPUT,
        )
    if not historical_values:
        return PeerComparisonResult(
            multiple_name=current_result.metric_name, company_value=current_result.value,
            peer_median=None, peer_count=len(historical_results), peers_with_data=0,
            status=DataStatus.UNAVAILABLE,
        )

    hist_median = statistics.median(historical_values)
    premium_discount = (current_result.value - hist_median) / hist_median if hist_median != 0 else None
    return PeerComparisonResult(
        multiple_name=current_result.metric_name, company_value=current_result.value,
        peer_median=round(hist_median, 2), peer_count=len(historical_results),
        peers_with_data=len(historical_values),
        premium_discount_pct=round(premium_discount, 4) if premium_discount is not None else None,
        status=DataStatus.OK,
    )
