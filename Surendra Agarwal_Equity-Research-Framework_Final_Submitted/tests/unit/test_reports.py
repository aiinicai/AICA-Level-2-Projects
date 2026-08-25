"""Tests for app/reports/templates.py and app/reports/generator.py."""

from __future__ import annotations

from app.core.enums import (
    ConfidenceLevel, DataStatus, ExchangeCode, Recommendation,
    RiskCategory, RiskSeverity, TrendDirection, UnitOfMeasure,
)
from app.core.models import (
    AIInterpretation, Company, HumanReview, InvestmentScore,
    InvestmentThesis, MetricResult, RiskItem, ScoreComponent,
    ThesisInvalidationTrigger, TrendResult,
)
from app.reports.generator import ReportContext, generate_report
from app.reports.templates import (
    DISCLAIMER,
    format_ai_interpretation,
    format_human_review_checklist,
    format_investment_score,
    format_metric,
    format_risk_item,
    format_trend,
)


def _ok_metric(name="Revenue", value=100.0, unit=UnitOfMeasure.INR_CRORE, period="FY2026"):
    return MetricResult(
        metric_name=name, formula="f", inputs={}, value=value, unit=unit,
        period=period, status=DataStatus.OK,
    )


class TestFormatMetric:
    def test_ok_metric_shows_level1_label(self):
        m = _ok_metric()
        rendered = format_metric(m)
        assert "LEVEL 1" in rendered
        assert "Revenue" in rendered

    def test_missing_metric_shows_not_available(self):
        m = MetricResult(metric_name="X", formula="f", inputs={}, value=None,
                          unit=UnitOfMeasure.RATIO, period="FY2026", status=DataStatus.MISSING_INPUT)
        rendered = format_metric(m)
        assert "not available" in rendered
        assert "missing_input" in rendered

    def test_percent_formatted_as_percentage(self):
        m = _ok_metric(name="EBITDA Margin", value=0.2524, unit=UnitOfMeasure.PERCENT)
        rendered = format_metric(m)
        assert "25.24%" in rendered

    def test_ratio_formatted_with_x_suffix(self):
        m = _ok_metric(name="Debt/Equity", value=0.06, unit=UnitOfMeasure.RATIO)
        rendered = format_metric(m)
        assert "0.06x" in rendered

    def test_rsi_ratio_not_given_x_suffix(self):
        m = _ok_metric(name="RSI (14)", value=75.42, unit=UnitOfMeasure.RATIO)
        rendered = format_metric(m)
        assert "75.42x" not in rendered
        assert "75.42" in rendered

    def test_data_quality_notes_included(self):
        m = MetricResult(
            metric_name="ROE", formula="f", inputs={}, value=0.11, unit=UnitOfMeasure.PERCENT,
            period="FY2026", status=DataStatus.OK, data_quality_notes=["Uses period-end equity."],
        )
        rendered = format_metric(m)
        assert "Uses period-end equity" in rendered


class TestFormatTrend:
    def test_trend_rendered_with_direction_and_change(self):
        t = TrendResult(
            metric_name="Sales", periods=["FY25", "FY26"], values=[100.0, 120.0],
            direction=TrendDirection.IMPROVING, percentage_change=0.2,
        )
        rendered = format_trend(t)
        assert "IMPROVING" in rendered
        assert "+20.0%" in rendered

    def test_missing_percentage_change_shows_na(self):
        t = TrendResult(
            metric_name="Sales", periods=["FY26"], values=[100.0],
            direction=TrendDirection.INSUFFICIENT_DATA,
        )
        rendered = format_trend(t)
        assert "n/a" in rendered


class TestFormatAiInterpretation:
    def test_always_level2_never_level1(self):
        a = AIInterpretation(claim="test claim", confidence=ConfidenceLevel.HIGH, model_name="m")
        rendered = format_ai_interpretation(a)
        assert "LEVEL 2" in rendered
        assert "LEVEL 1" not in rendered
        assert "confidence=high" in rendered


class TestFormatRiskItem:
    def test_all_fields_rendered_when_present(self):
        r = RiskItem(
            category=RiskCategory.FINANCIAL, description="High leverage", severity=RiskSeverity.HIGH,
            potential_impact="Refinancing risk", mitigation="Deleveraging plan", monitoring_trigger="D/E > 2.0",
        )
        rendered = format_risk_item(r)
        assert "[HIGH] Financial" in rendered
        assert "Refinancing risk" in rendered
        assert "Deleveraging plan" in rendered
        assert "D/E > 2.0" in rendered

    def test_optional_fields_omitted_when_absent(self):
        r = RiskItem(category=RiskCategory.MARKET, description="Some risk", severity=RiskSeverity.LOW)
        rendered = format_risk_item(r)
        assert "Potential impact" not in rendered
        assert "Mitigation" not in rendered


class TestFormatInvestmentScore:
    def test_none_overall_score_shown_explicitly(self):
        score = InvestmentScore(overall_score=None, components=[], weights_used={})
        rendered = format_investment_score(score)
        assert "not available" in rendered

    def test_renormalized_flag_mentioned(self):
        score = InvestmentScore(
            overall_score=80.0, components=[], weights_used={},
            renormalized=True, unavailable_components=["Technical"],
        )
        rendered = format_investment_score(score)
        assert "renormalized" in rendered.lower()
        assert "Technical" in rendered

    def test_component_table_includes_all_components(self):
        components = [
            ScoreComponent(name="Fundamentals", score=80.0, weight=0.3, status=DataStatus.OK, weighted_score=24.0),
            ScoreComponent(name="Technical", score=None, weight=0.1, status=DataStatus.UNAVAILABLE),
        ]
        score = InvestmentScore(overall_score=24.0, components=components, weights_used={})
        rendered = format_investment_score(score)
        assert "Fundamentals" in rendered
        assert "80.0" in rendered
        assert "N/A" in rendered


class TestFormatHumanReviewChecklist:
    def test_unreviewed_item_marked_explicitly(self):
        rendered = format_human_review_checklist([], ["id1"], {"id1": "Some claim"})
        assert "[ ]" in rendered
        assert "not yet reviewed" in rendered

    def test_reviewed_and_accepted_item_marked_correctly(self):
        review = HumanReview(target_id="id1", reviewer_name="Surendra", accepted=True)
        rendered = format_human_review_checklist([review], ["id1"], {"id1": "Some claim"})
        assert "[x]" in rendered
        assert "Accepted" in rendered
        assert "Surendra" in rendered

    def test_never_falsely_claims_validation_for_unlisted_target(self):
        review = HumanReview(target_id="other_id", reviewer_name="Surendra", accepted=True)
        rendered = format_human_review_checklist([review], ["id1"], {"id1": "Some claim"})
        assert "not yet reviewed" in rendered

    def test_empty_target_list_shows_no_items_message(self):
        rendered = format_human_review_checklist([], [], {})
        assert "No items require human validation" in rendered


class TestGenerateReportStructure:
    def _minimal_context(self):
        company = Company(name="Test Co", ticker="TEST", exchange=ExchangeCode.NSE)
        return ReportContext(company=company)

    def test_report_has_exactly_19_sections(self):
        report = generate_report(self._minimal_context())
        assert report.count("\n## ") == 19

    def test_sections_numbered_1_through_19_in_order(self):
        report = generate_report(self._minimal_context())
        for i in range(1, 20):
            assert f"\n## {i}. " in report

    def test_disclaimer_present(self):
        report = generate_report(self._minimal_context())
        assert DISCLAIMER in report
        assert report.count("AI-assisted decision support only") >= 2

    def test_empty_context_produces_placeholders_not_crash(self):
        report = generate_report(self._minimal_context())
        assert "No investment thesis has been generated" in report
        assert "No risks have been identified" in report

    def test_company_name_and_ticker_in_title(self):
        report = generate_report(self._minimal_context())
        assert "Test Co" in report
        assert "TEST" in report

    def test_never_claims_price_prediction_or_guarantee_language(self):
        report = generate_report(self._minimal_context())
        banned_terms = ["guaranteed", "risk-free", "certain multibagger", "predicts the stock will"]
        lowered = report.lower()
        for term in banned_terms:
            assert term not in lowered


class TestGenerateReportWithFullData:
    def _full_context(self):
        company = Company(name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS",
                           exchange=ExchangeCode.NSE, sector="Auto Ancillary")
        thesis = InvestmentThesis(
            recommendation=Recommendation.HOLD,
            core_thesis="Strong growth offset by rich valuation.",
            counterarguments=["Valuation is elevated"],
            catalysts=["New order wins"],
            invalidation_triggers=[
                ThesisInvalidationTrigger(condition="Revenue growth below 10%", threshold_basis="explicit_assumption"),
                ThesisInvalidationTrigger(condition="Debt/Equity above 1.0", threshold_basis="industry_context"),
            ],
            data_limitations=["Peer data not independently audited"],
        )
        score = InvestmentScore(
            overall_score=76.7,
            components=[ScoreComponent(name="Fundamentals", score=84.0, weight=0.3,
                                        status=DataStatus.OK, weighted_score=25.2)],
            weights_used={"Fundamentals": 0.3},
        )
        interp = AIInterpretation(claim="Management guided for capex expansion",
                                   confidence=ConfidenceLevel.HIGH, model_name="test-model")
        risk = RiskItem(category=RiskCategory.FINANCIAL, description="Negative FCF", severity=RiskSeverity.LOW)
        return ReportContext(
            company=company, fundamental_metrics=[_ok_metric("EBITDA Margin", 0.2524, UnitOfMeasure.PERCENT)],
            management_interpretations=[interp], risks=[risk], investment_score=score, thesis=thesis,
        )

    def test_thesis_recommendation_appears_in_executive_summary(self):
        report = generate_report(self._full_context())
        assert "HOLD" in report

    def test_invalidation_triggers_rendered(self):
        report = generate_report(self._full_context())
        assert "Revenue growth below 10%" in report
        assert "Debt/Equity above 1.0" in report

    def test_management_interpretation_labeled_level2(self):
        report = generate_report(self._full_context())
        assert "Management guided for capex expansion" in report
        idx = report.find("Management guided for capex expansion")
        surrounding = report[idx:idx + 200]
        assert "LEVEL 2" in surrounding

    def test_risk_rendered_in_risk_section(self):
        report = generate_report(self._full_context())
        assert "Negative FCF" in report

    def test_ai_ids_score_in_executive_summary(self):
        report = generate_report(self._full_context())
        assert "76.7" in report

    def test_human_validation_checklist_shows_unreviewed_items(self):
        report = generate_report(self._full_context())
        assert "[ ]" in report
