"""Tests for app/analysis/risk.py."""

from __future__ import annotations

import pytest

from app.core.enums import (
    ConfidenceLevel, DataStatus, RiskCategory, RiskSeverity,
    TrendDirection, UnitOfMeasure,
)
from app.core.exceptions import LLMProviderError
from app.core.models import DocumentEvidence, MetricResult, TrendResult
from app.ai.llm_client import FakeLLMClient
from app.analysis.risk import (
    build_risk_register,
    detect_financial_risks,
    extract_risk_from_evidence,
    extract_risks_batch,
)


def _metric(name, value, period="FY2026"):
    return MetricResult(
        metric_name=name, formula="f", inputs={}, value=value,
        unit=UnitOfMeasure.RATIO, period=period, status=DataStatus.OK,
    )


class TestDeterministicFinancialRisks:
    def test_low_leverage_flags_no_debt_risk(self):
        metrics = [_metric("Debt/Equity", 0.06)]
        risks = detect_financial_risks(metrics)
        assert risks == []

    def test_high_debt_equity_flags_high_severity(self):
        metrics = [_metric("Debt/Equity", 1.8)]
        risks = detect_financial_risks(metrics)
        assert len(risks) == 1
        assert risks[0].severity == RiskSeverity.HIGH
        assert risks[0].category == RiskCategory.FINANCIAL

    def test_moderate_debt_equity_flags_moderate_severity(self):
        metrics = [_metric("Debt/Equity", 1.2)]
        risks = detect_financial_risks(metrics)
        assert risks[0].severity == RiskSeverity.MODERATE

    def test_healthy_net_debt_ebitda_flags_nothing(self):
        metrics = [_metric("Net Debt/EBITDA", 0.14)]
        risks = detect_financial_risks(metrics)
        assert risks == []

    def test_high_net_debt_ebitda_flags_high(self):
        metrics = [_metric("Net Debt/EBITDA", 5.0)]
        risks = detect_financial_risks(metrics)
        assert any(r.severity == RiskSeverity.HIGH for r in risks)

    def test_low_cash_conversion_flagged(self):
        metrics = [_metric("CFO/PAT", 0.3)]
        risks = detect_financial_risks(metrics)
        assert len(risks) == 1
        assert risks[0].severity == RiskSeverity.MODERATE

    def test_healthy_cash_conversion_not_flagged(self):
        metrics = [_metric("CFO/PAT", 0.95)]
        risks = detect_financial_risks(metrics)
        assert risks == []

    def test_negative_fcf_flagged_as_low_severity_by_default(self):
        metrics = [_metric("Free Cash Flow", -1074.41)]
        risks = detect_financial_risks(metrics)
        assert len(risks) == 1
        assert risks[0].severity == RiskSeverity.LOW

    def test_positive_fcf_not_flagged(self):
        metrics = [_metric("Free Cash Flow", 500.0)]
        risks = detect_financial_risks(metrics)
        assert risks == []

    def test_every_risk_carries_evidence_id(self):
        metrics = [_metric("Debt/Equity", 2.0)]
        risks = detect_financial_risks(metrics)
        assert risks[0].evidence_ids == [metrics[0].metric_id]

    def test_missing_metric_does_not_crash(self):
        risks = detect_financial_risks([])
        assert risks == []

    def test_non_ok_status_metric_ignored(self):
        bad_metric = MetricResult(
            metric_name="Debt/Equity", formula="f", inputs={}, value=None,
            unit=UnitOfMeasure.RATIO, period="FY2026", status=DataStatus.MISSING_INPUT,
        )
        risks = detect_financial_risks([bad_metric])
        assert risks == []

    def test_deteriorating_trend_flagged(self):
        trend = TrendResult(
            metric_name="PAT Margin", periods=["FY24", "FY25", "FY26"],
            values=[0.15, 0.10, 0.05], direction=TrendDirection.DETERIORATING,
            significance=ConfidenceLevel.HIGH,
        )
        risks = detect_financial_risks([], [trend])
        assert len(risks) == 1
        assert risks[0].severity == RiskSeverity.HIGH

    def test_improving_trend_not_flagged(self):
        trend = TrendResult(
            metric_name="Revenue", periods=["FY24", "FY25", "FY26"],
            values=[100.0, 120.0, 150.0], direction=TrendDirection.IMPROVING,
        )
        risks = detect_financial_risks([], [trend])
        assert risks == []

    def test_multiple_rules_can_fire_together(self):
        metrics = [_metric("Debt/Equity", 2.0), _metric("CFO/PAT", 0.3), _metric("Free Cash Flow", -100.0)]
        risks = detect_financial_risks(metrics)
        assert len(risks) == 3


class TestAiRiskExtraction:
    def _evidence(self, text="Generic risk disclosure text.", page=1):
        return DocumentEvidence(source_document="test.pdf", page_number=page, raw_text=text)

    def test_risk_found_produces_risk_item(self):
        fake = FakeLLMClient(fixed_response=(
            '{"risk_found": true, "category": "regulatory", '
            '"description": "Exposure to changing EV policy", "severity": "moderate", '
            '"potential_impact": "Margin impact", "mitigation": "Diversified product mix"}'
        ))
        result = extract_risk_from_evidence(self._evidence(), fake)
        assert result is not None
        assert result.category == RiskCategory.REGULATORY
        assert result.severity == RiskSeverity.MODERATE
        assert result.mitigation == "Diversified product mix"

    def test_risk_not_found_returns_none(self):
        fake = FakeLLMClient(fixed_response='{"risk_found": false}')
        result = extract_risk_from_evidence(self._evidence(), fake)
        assert result is None

    def test_evidence_id_linked_correctly(self):
        ev = self._evidence()
        fake = FakeLLMClient(fixed_response=(
            '{"risk_found": true, "category": "market", "description": "test risk", "severity": "high"}'
        ))
        result = extract_risk_from_evidence(ev, fake)
        assert result.evidence_ids == [ev.evidence_id]

    def test_unrecognized_category_defaults_to_business(self):
        fake = FakeLLMClient(fixed_response=(
            '{"risk_found": true, "category": "totally_unknown_category", '
            '"description": "test risk", "severity": "moderate"}'
        ))
        result = extract_risk_from_evidence(self._evidence(), fake)
        assert result.category == RiskCategory.BUSINESS

    def test_unrecognized_severity_defaults_to_moderate(self):
        fake = FakeLLMClient(fixed_response=(
            '{"risk_found": true, "category": "business", '
            '"description": "test risk", "severity": "extremely-bad"}'
        ))
        result = extract_risk_from_evidence(self._evidence(), fake)
        assert result.severity == RiskSeverity.MODERATE

    def test_risk_found_true_but_no_description_returns_none(self):
        fake = FakeLLMClient(fixed_response='{"risk_found": true, "category": "business", "severity": "high"}')
        result = extract_risk_from_evidence(self._evidence(), fake)
        assert result is None

    def test_malformed_json_raises(self):
        fake = FakeLLMClient(fixed_response="not json")
        with pytest.raises(LLMProviderError):
            extract_risk_from_evidence(self._evidence(), fake)

    def test_never_infers_mitigation_not_in_text(self):
        fake = FakeLLMClient(fixed_response=(
            '{"risk_found": true, "category": "market", "description": "Customer concentration", '
            '"severity": "high", "mitigation": null}'
        ))
        result = extract_risk_from_evidence(self._evidence(), fake)
        assert result.mitigation is None


class TestExtractRisksBatch:
    def _evidence(self, page):
        return DocumentEvidence(source_document="test.pdf", page_number=page, raw_text=f"text {page}")

    def test_batch_processes_all_pages(self):
        pages = [self._evidence(i) for i in range(1, 4)]
        fake = FakeLLMClient(fixed_response='{"risk_found": true, "category": "business", "description": "d", "severity": "low"}')
        results = extract_risks_batch(pages, fake)
        assert len(results) == 3

    def test_batch_skips_failed_pages(self):
        pages = [self._evidence(1), self._evidence(2)]
        fake = FakeLLMClient(responses=[
            "garbage",
            '{"risk_found": true, "category": "business", "description": "d", "severity": "low"}',
        ])
        results = extract_risks_batch(pages, fake)
        assert len(results) == 1

    def test_batch_skips_pages_with_no_risk(self):
        pages = [self._evidence(1), self._evidence(2)]
        fake = FakeLLMClient(responses=[
            '{"risk_found": false}',
            '{"risk_found": true, "category": "business", "description": "d", "severity": "low"}',
        ])
        results = extract_risks_batch(pages, fake)
        assert len(results) == 1


class TestBuildRiskRegister:
    def test_deterministic_only_when_no_documents_supplied(self):
        metrics = [_metric("Debt/Equity", 2.0)]
        register = build_risk_register(metrics=metrics)
        assert len(register) == 1
        assert register[0].category == RiskCategory.FINANCIAL

    def test_documents_without_llm_client_skipped_gracefully(self):
        metrics = [_metric("Debt/Equity", 2.0)]
        docs = [DocumentEvidence(source_document="test.pdf", page_number=1, raw_text="risk text")]
        register = build_risk_register(metrics=metrics, risk_document_evidence=docs, llm_client=None)
        assert len(register) == 1

    def test_combines_both_sources_when_available(self):
        metrics = [_metric("Debt/Equity", 2.0)]
        docs = [DocumentEvidence(source_document="test.pdf", page_number=1, raw_text="risk text")]
        fake = FakeLLMClient(fixed_response='{"risk_found": true, "category": "market", "description": "d", "severity": "high"}')
        register = build_risk_register(metrics=metrics, risk_document_evidence=docs, llm_client=fake)
        assert len(register) == 2
        categories = {r.category for r in register}
        assert RiskCategory.FINANCIAL in categories
        assert RiskCategory.MARKET in categories

    def test_empty_everything_returns_empty_register(self):
        register = build_risk_register(metrics=[])
        assert register == []


class TestRealSonaBLWData:
    def test_low_leverage_produces_minimal_deterministic_risks(self, sona_blw_statements):
        from app.analysis.fundamentals import compute_debt_to_equity, compute_net_debt_to_ebitda
        from app.analysis.cashflow import compute_cfo_to_pat

        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        metrics = [
            compute_debt_to_equity(fy26), compute_net_debt_to_ebitda(fy26), compute_cfo_to_pat(fy26),
        ]
        risks = detect_financial_risks(metrics)
        assert risks == []

    def test_real_negative_fcf_flagged_low_severity(self, sona_blw_statements):
        from app.analysis.cashflow import compute_fcf

        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        fy25 = next(s for s in sona_blw_statements if s.period == "FY2025")
        metrics = [compute_fcf(fy26, fy25)]
        risks = detect_financial_risks(metrics)
        assert len(risks) == 1
        assert risks[0].severity == RiskSeverity.LOW
