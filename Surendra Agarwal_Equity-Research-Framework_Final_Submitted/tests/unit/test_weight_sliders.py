"""Tests for app/ui/pages/ai_ids_dashboard.py's weight-slider support:
the pure normalize_weights() function, and real Streamlit AppTest
interaction confirming sliders actually recompute the score and the
reset button genuinely resets widget state (not just a tracking dict).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.core.enums import DataStatus, ExchangeCode, UnitOfMeasure
from app.core.models import Company, MetricResult
from app.ui.pages.ai_ids_dashboard import _WEIGHT_KEY_MAP, normalize_weights

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestNormalizeWeights:
    def test_already_normalized_stays_unchanged(self):
        weights = {"A": 0.3, "B": 0.3, "C": 0.4}
        result = normalize_weights(weights)
        assert result["A"] == pytest.approx(0.3)
        assert result["B"] == pytest.approx(0.3)
        assert result["C"] == pytest.approx(0.4)

    def test_arbitrary_values_renormalize_to_sum_one(self):
        weights = {"A": 10.0, "B": 20.0, "C": 70.0}
        result = normalize_weights(weights)
        assert sum(result.values()) == pytest.approx(1.0)
        assert result["A"] == pytest.approx(0.10)
        assert result["B"] == pytest.approx(0.20)
        assert result["C"] == pytest.approx(0.70)

    def test_over_100_percent_still_renormalizes_correctly(self):
        weights = {"A": 100.0, "B": 100.0}
        result = normalize_weights(weights)
        assert result["A"] == pytest.approx(0.5)
        assert result["B"] == pytest.approx(0.5)

    def test_single_nonzero_dominates_after_normalization(self):
        weights = {"A": 100.0, "B": 0.0, "C": 0.0}
        result = normalize_weights(weights)
        assert result["A"] == pytest.approx(1.0)
        assert result["B"] == 0.0
        assert result["C"] == 0.0

    def test_all_zero_falls_back_to_equal_weighting(self):
        weights = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}
        result = normalize_weights(weights)
        assert all(v == pytest.approx(0.25) for v in result.values())
        assert sum(result.values()) == pytest.approx(1.0)

    def test_empty_dict_does_not_crash(self):
        result = normalize_weights({})
        assert result == {}

    def test_result_keys_match_input_keys(self):
        weights = {"X": 5.0, "Y": 15.0}
        result = normalize_weights(weights)
        assert set(result.keys()) == {"X", "Y"}


class TestWeightKeyMapping:
    def test_all_six_components_mapped(self):
        assert len(_WEIGHT_KEY_MAP) == 6
        assert set(_WEIGHT_KEY_MAP.keys()) == {
            "Fundamentals", "Cash Flow Quality", "Business/Management",
            "Valuation", "Technical", "Risk/Governance",
        }

    def test_maps_to_valid_config_keys(self):
        from app.config import get_settings

        settings = get_settings()
        for config_key in _WEIGHT_KEY_MAP.values():
            assert config_key in settings.score_weights


class TestSlidersRealAppInteraction:
    def _app_with_company(self):
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=30)
        at.session_state["company"] = Company(name="Test Co", ticker="TEST", exchange=ExchangeCode.NSE)
        at.run()
        at.sidebar.radio[0].set_value("AI-IDS Score").run()
        return at

    def test_six_sliders_render_with_configured_defaults(self):
        at = self._app_with_company()
        assert len(at.slider) == 6
        values = {s.label: s.value for s in at.slider}
        assert values["Fundamentals"] == 30.0
        assert values["Cash Flow Quality"] == 15.0
        assert values["Business/Management"] == 15.0
        assert values["Valuation"] == 20.0
        assert values["Technical"] == 10.0
        assert values["Risk/Governance"] == 10.0

    def test_slider_change_reflected_in_effective_weights_caption(self):
        at = self._app_with_company()
        for s in at.slider:
            if s.label == "Fundamentals":
                s.set_value(100.0).run()
            else:
                s.set_value(0.0).run()
        captions = [c.value for c in at.caption]
        effective_caption = next(c for c in captions if "Effective" in c)
        assert "Fundamentals: 100%" in effective_caption

    def test_slider_weighted_score_computation_end_to_end(self):
        at = self._app_with_company()
        at.session_state["fundamental_metrics"] = [
            MetricResult(metric_name="EBITDA Margin", formula="f", inputs={}, value=0.25,
                         unit=UnitOfMeasure.PERCENT, period="FY2026", status=DataStatus.OK),
            MetricResult(metric_name="ROE", formula="f", inputs={}, value=0.20,
                         unit=UnitOfMeasure.PERCENT, period="FY2026", status=DataStatus.OK),
        ]
        at.run()
        at.sidebar.radio[0].set_value("AI-IDS Score").run()

        for s in at.slider:
            if s.label == "Fundamentals":
                s.set_value(100.0).run()
            else:
                s.set_value(0.0).run()

        compute_btn = next(b for b in at.button if b.label == "Compute AI-IDS Score")
        compute_btn.click().run()
        assert list(at.exception) == []

        overall_metric = next(m for m in at.metric if m.label == "Overall AI-IDS Score")
        assert "100.0" in overall_metric.value

    def test_reset_button_actually_resets_widget_state(self):
        at = self._app_with_company()
        fund_slider = next(s for s in at.slider if s.label == "Fundamentals")
        fund_slider.set_value(90.0).run()
        assert next(s for s in at.slider if s.label == "Fundamentals").value == 90.0

        reset_btn = next(b for b in at.button if b.label == "Reset to Configured Defaults")
        reset_btn.click().run()
        assert list(at.exception) == []

        fund_slider_after = next(s for s in at.slider if s.label == "Fundamentals")
        assert fund_slider_after.value == 30.0

    def test_weights_never_change_env_configured_defaults(self):
        from app.config import get_settings

        before = dict(get_settings().score_weights)
        at = self._app_with_company()
        fund_slider = next(s for s in at.slider if s.label == "Fundamentals")
        fund_slider.set_value(99.0).run()
        after = dict(get_settings().score_weights)
        assert before == after
