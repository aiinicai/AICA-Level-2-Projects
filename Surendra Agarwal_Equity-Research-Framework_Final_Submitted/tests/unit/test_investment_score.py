"""Tests for app/scoring/investment_score.py."""

from __future__ import annotations

import pytest

from app.core.enums import ConfidenceLevel, DataStatus, RiskCategory, RiskSeverity, UnitOfMeasure
from app.core.models import AIInterpretation, MetricResult, RiskItem, ScoreComponent
from app.analysis.peers import PeerComparisonResult
from app.scoring.investment_score import (
    compute_investment_score,
    score_business_management,
    score_cashflow_quality,
    score_fundamentals,
    score_risk_governance,
    score_technical,
    score_valuation,
)


def _metric(name, value, status=DataStatus.OK):
    return MetricResult(
        metric_name=name, formula="f", inputs={}, value=value,
        unit=UnitOfMeasure.RATIO, period="FY2026", status=status,
    )


class TestScoreFundamentals:
    def test_strong_fundamentals_score_high(self):
        metrics = [
            _metric("Revenue CAGR (3yr)", 0.20), _metric("EBITDA Margin", 0.28),
            _metric("ROE", 0.22), _metric("ROCE", 0.25), _metric("Debt/Equity", 0.1),
        ]
        result = score_fundamentals(metrics)
        assert result.status == DataStatus.OK
        assert result.score == 100.0
        assert result.confidence == ConfidenceLevel.HIGH

    def test_weak_fundamentals_score_low(self):
        metrics = [
            _metric("Revenue CAGR (3yr)", -0.05), _metric("EBITDA Margin", 0.05),
            _metric("ROE", 0.02), _metric("ROCE", 0.03), _metric("Debt/Equity", 2.0),
        ]
        result = score_fundamentals(metrics)
        assert result.score == 20.0

    def test_single_metric_insufficient_returns_unavailable(self):
        result = score_fundamentals([_metric("Revenue CAGR (3yr)", 0.15)])
        assert result.status == DataStatus.UNAVAILABLE
        assert result.score is None

    def test_no_metrics_returns_unavailable(self):
        result = score_fundamentals([])
        assert result.status == DataStatus.UNAVAILABLE

    def test_non_ok_metric_status_excluded(self):
        metrics = [
            _metric("Revenue CAGR (3yr)", 0.15),
            _metric("EBITDA Margin", None, status=DataStatus.MISSING_INPUT),
            _metric("ROE", 0.18),
        ]
        result = score_fundamentals(metrics)
        assert result.status == DataStatus.OK
        assert len(result.evidence_ids) == 2  # only the 2 OK metrics counted


class TestScoreCashflowQuality:
    def test_healthy_cash_conversion_scores_high(self):
        metrics = [_metric("CFO/PAT", 1.2), _metric("FCF Conversion", 0.65)]
        result = score_cashflow_quality(metrics)
        assert result.score == 100.0

    def test_negative_fcf_conversion_scores_low(self):
        metrics = [_metric("FCF Conversion", -0.5)]
        result = score_cashflow_quality(metrics)
        assert result.score == 20.0

    def test_no_data_unavailable(self):
        result = score_cashflow_quality([])
        assert result.status == DataStatus.UNAVAILABLE
        assert result.score is None

    def test_very_high_cfo_pat_tapered_not_maxed(self):
        # CFO/PAT > 1.5 is treated as a WC-timing flag, not "better than 1.1-1.5"
        high_result = score_cashflow_quality([_metric("CFO/PAT", 3.0)])
        mid_result = score_cashflow_quality([_metric("CFO/PAT", 1.3)])
        assert high_result.score < mid_result.score


class TestScoreBusinessManagement:
    def test_high_confidence_interpretations_score_high(self):
        interps = [
            AIInterpretation(claim="a", confidence=ConfidenceLevel.HIGH, model_name="m", based_on_evidence_ids=["e1"]),
            AIInterpretation(claim="b", confidence=ConfidenceLevel.HIGH, model_name="m", based_on_evidence_ids=["e2"]),
            AIInterpretation(claim="c", confidence=ConfidenceLevel.HIGH, model_name="m", based_on_evidence_ids=["e3"]),
        ]
        result = score_business_management(interps)
        assert result.score == 85.0
        assert result.confidence == ConfidenceLevel.MEDIUM  # >=3 interpretations

    def test_empty_list_unavailable(self):
        result = score_business_management([])
        assert result.status == DataStatus.UNAVAILABLE
        assert result.score is None

    def test_fewer_than_three_interpretations_lower_confidence(self):
        interps = [AIInterpretation(claim="a", confidence=ConfidenceLevel.HIGH, model_name="m", based_on_evidence_ids=["e1"])]
        result = score_business_management(interps)
        assert result.confidence == ConfidenceLevel.LOW

    def test_evidence_ids_traceable_to_interpretations(self):
        interps = [AIInterpretation(claim="a", confidence=ConfidenceLevel.MEDIUM, model_name="m", based_on_evidence_ids=["e1"])]
        result = score_business_management(interps)
        assert result.evidence_ids == [interps[0].interpretation_id]


class TestScoreValuation:
    def test_deep_discount_scores_high(self):
        comparisons = [
            PeerComparisonResult(multiple_name="P/E", company_value=10.0, peer_median=20.0,
                                  peer_count=3, peers_with_data=3, premium_discount_pct=-0.5, status=DataStatus.OK)
        ]
        result = score_valuation(comparisons)
        assert result.score == 100.0

    def test_large_premium_scores_low(self):
        comparisons = [
            PeerComparisonResult(multiple_name="P/E", company_value=60.0, peer_median=20.0,
                                  peer_count=3, peers_with_data=3, premium_discount_pct=0.5, status=DataStatus.OK)
        ]
        result = score_valuation(comparisons)
        assert result.score == 20.0

    def test_no_usable_comparisons_unavailable(self):
        comparisons = [
            PeerComparisonResult(multiple_name="P/E", company_value=None, peer_median=None,
                                  peer_count=0, peers_with_data=0, status=DataStatus.MISSING_INPUT)
        ]
        result = score_valuation(comparisons)
        assert result.status == DataStatus.UNAVAILABLE


class TestScoreTechnical:
    def test_no_rsi_returns_unavailable(self):
        result = score_technical([])
        assert result.status == DataStatus.UNAVAILABLE
        assert result.score is None

    def test_neutral_rsi_scores_higher_than_overbought(self):
        neutral = score_technical([_metric("RSI (14)", 50.0)])
        overbought = score_technical([_metric("RSI (14)", 85.0)])
        assert neutral.score > overbought.score

    def test_price_above_sma200_boosts_score(self):
        rsi = _metric("RSI (14)", 50.0)
        sma = MetricResult(
            metric_name="SMA 200", formula="f", inputs={"latest_close": 500.0}, value=450.0,
            unit=UnitOfMeasure.INR_ABSOLUTE, period="latest", status=DataStatus.OK,
        )
        result = score_technical([rsi, sma])
        neutral_only = score_technical([rsi])
        assert result.score > neutral_only.score


class TestScoreRiskGovernance:
    def test_empty_risk_list_is_unavailable_not_perfect_score(self):
        # Critical: absence of supplied risks must NOT be rewarded as "no risk = 100".
        result = score_risk_governance([])
        assert result.status == DataStatus.UNAVAILABLE
        assert result.score is None

    def test_low_severity_risks_score_high(self):
        risks = [RiskItem(category=RiskCategory.MARKET, description="minor", severity=RiskSeverity.LOW)]
        result = score_risk_governance(risks)
        assert result.score == 95.0

    def test_severe_risks_score_low(self):
        risks = [
            RiskItem(category=RiskCategory.GOVERNANCE, description="major issue", severity=RiskSeverity.SEVERE),
            RiskItem(category=RiskCategory.FINANCIAL, description="major issue 2", severity=RiskSeverity.SEVERE),
        ]
        result = score_risk_governance(risks)
        assert result.score == 0.0  # floored, not negative

    def test_score_never_goes_negative(self):
        risks = [RiskItem(category=RiskCategory.MARKET, description=f"risk {i}", severity=RiskSeverity.SEVERE) for i in range(5)]
        result = score_risk_governance(risks)
        assert result.score == 0.0


class TestComputeInvestmentScore:
    def test_all_components_available_sums_to_declared_weights(self):
        components = [
            ScoreComponent(name="Fundamentals", score=80.0, weight=0.0, status=DataStatus.OK),
            ScoreComponent(name="Cash Flow Quality", score=70.0, weight=0.0, status=DataStatus.OK),
            ScoreComponent(name="Business/Management", score=60.0, weight=0.0, status=DataStatus.OK),
            ScoreComponent(name="Valuation", score=50.0, weight=0.0, status=DataStatus.OK),
            ScoreComponent(name="Technical", score=90.0, weight=0.0, status=DataStatus.OK),
            ScoreComponent(name="Risk/Governance", score=100.0, weight=0.0, status=DataStatus.OK),
        ]
        result = compute_investment_score(components)
        expected = 80 * 0.3 + 70 * 0.15 + 60 * 0.15 + 50 * 0.2 + 90 * 0.1 + 100 * 0.1
        assert abs(result.overall_score - expected) < 0.01
        assert result.renormalized is False
        assert result.unavailable_components == []

    def test_missing_components_never_zero_filled(self):
        components = [
            ScoreComponent(name="Fundamentals", score=80.0, weight=0.0, status=DataStatus.OK),
            ScoreComponent(name="Cash Flow Quality", score=None, weight=0.0, status=DataStatus.UNAVAILABLE),
            ScoreComponent(name="Business/Management", score=None, weight=0.0, status=DataStatus.UNAVAILABLE),
            ScoreComponent(name="Valuation", score=None, weight=0.0, status=DataStatus.UNAVAILABLE),
            ScoreComponent(name="Technical", score=None, weight=0.0, status=DataStatus.UNAVAILABLE),
            ScoreComponent(name="Risk/Governance", score=None, weight=0.0, status=DataStatus.UNAVAILABLE),
        ]
        result = compute_investment_score(components)
        # Only Fundamentals available -> renormalized weight = 1.0 -> overall = 80.0 exactly,
        # NOT 80*0.3=24 (which is what zero-filling the rest would silently produce).
        assert result.overall_score == 80.0
        assert result.renormalized is True
        assert set(result.unavailable_components) == {
            "Cash Flow Quality", "Business/Management", "Valuation", "Technical", "Risk/Governance"
        }

    def test_all_components_unavailable_overall_score_is_none(self):
        components = [
            ScoreComponent(name=n, score=None, weight=0.0, status=DataStatus.UNAVAILABLE)
            for n in ("Fundamentals", "Cash Flow Quality", "Business/Management",
                      "Valuation", "Technical", "Risk/Governance")
        ]
        result = compute_investment_score(components)
        assert result.overall_score is None
        assert result.renormalized is False  # nothing to renormalize against

    def test_unknown_component_name_raises(self):
        components = [ScoreComponent(name="Not A Real Component", score=50.0, weight=0.0, status=DataStatus.OK)]
        with pytest.raises(ValueError):
            compute_investment_score(components)

    def test_custom_weights_respected(self):
        components = [
            ScoreComponent(name="Fundamentals", score=100.0, weight=0.0, status=DataStatus.OK),
            ScoreComponent(name="Cash Flow Quality", score=0.0, weight=0.0, status=DataStatus.OK),
        ]
        custom_weights = {"Fundamentals": 0.9, "Cash Flow Quality": 0.1}
        result = compute_investment_score(components, weights=custom_weights)
        assert result.overall_score == 90.0

    def test_renormalization_math_explicit_two_component_case(self):
        # Fundamentals (weight .30, score 84) and Cash Flow Quality (weight
        # .15, score 55) available; everything else unavailable.
        # Renormalized weights: .30/.45=.6667, .15/.45=.3333
        # Expected overall = 84*.6667 + 55*.3333 = 56.0 + 18.33 = 74.33
        components = [
            ScoreComponent(name="Fundamentals", score=84.0, weight=0.0, status=DataStatus.OK),
            ScoreComponent(name="Cash Flow Quality", score=55.0, weight=0.0, status=DataStatus.OK),
            ScoreComponent(name="Business/Management", score=None, weight=0.0, status=DataStatus.UNAVAILABLE),
            ScoreComponent(name="Valuation", score=None, weight=0.0, status=DataStatus.UNAVAILABLE),
            ScoreComponent(name="Technical", score=None, weight=0.0, status=DataStatus.UNAVAILABLE),
            ScoreComponent(name="Risk/Governance", score=None, weight=0.0, status=DataStatus.UNAVAILABLE),
        ]
        result = compute_investment_score(components)
        assert abs(result.overall_score - 74.33) < 0.05

    def test_weighted_scores_sum_to_overall_score(self):
        components = [
            ScoreComponent(name="Fundamentals", score=80.0, weight=0.0, status=DataStatus.OK),
            ScoreComponent(name="Valuation", score=40.0, weight=0.0, status=DataStatus.OK),
        ]
        result = compute_investment_score(components)
        weighted_sum = sum(c.weighted_score for c in result.components if c.weighted_score is not None)
        assert abs(weighted_sum - result.overall_score) < 0.01
