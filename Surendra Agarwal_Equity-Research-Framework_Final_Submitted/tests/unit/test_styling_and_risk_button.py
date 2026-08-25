"""Tests for app/ui/styling.py's CSS injection, and real AppTest
interaction confirming the Risk Dashboard's new "Extract Business &
Management Commentary" button is wired correctly."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.core.enums import DocumentSectionType, DocumentType, ExchangeCode
from app.core.models import Company, DocumentEvidence
from app.ui.styling import ELECTRIC_TEAL

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestStylingModule:
    def test_electric_teal_matches_theme_toml_accent_comment(self):
        theme_text = (PROJECT_ROOT / ".streamlit" / "config.toml").read_text()
        assert ELECTRIC_TEAL in theme_text

    def test_inject_accent_css_targets_stable_metric_testid(self):
        from app.ui.styling import _CSS
        assert 'data-testid="stMetricValue"' in _CSS
        assert ELECTRIC_TEAL in _CSS


class TestRiskDashboardBusinessManagementButtonRealInteraction:
    def test_button_present_and_click_fails_gracefully_without_api_key(self):
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=30)
        at.session_state["company"] = Company(
            name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE,
        )
        at.session_state["document_evidence"] = [
            DocumentEvidence(
                source_document="Test Annual Report", page_number=1,
                section=DocumentSectionType.BUSINESS,
                document_type=DocumentType.ANNUAL_REPORT,
                raw_text="The company is a leading manufacturer of precision-forged components.",
            ),
        ]
        at.run()
        at.sidebar.radio[0].set_value("Risk Dashboard").run()
        assert list(at.exception) == []

        extract_btn = next(
            (b for b in at.button if "Business & Management" in b.label), None,
        )
        assert extract_btn is not None, "Extract Business & Management Commentary button not found"

        extract_btn.click().run()
        assert list(at.exception) == []
