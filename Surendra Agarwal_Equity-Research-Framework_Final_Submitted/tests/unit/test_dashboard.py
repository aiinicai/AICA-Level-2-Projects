"""Tests for the Streamlit dashboard.

Two kinds of coverage here:
1. AppTest smoke tests - genuinely launch the app via Streamlit's own
   testing framework and confirm it starts and every page navigates
   without an unhandled exception. This is real verification of
   "dashboard startup," not just an import check.
2. Pure-function unit tests for the non-Streamlit logic embedded in
   page modules (e.g. company_input.run_deterministic_pipeline,
   the *_to_rows table-formatting helpers) - these are ordinary
   functions with no st.* calls and are tested directly.

HONEST LIMIT: AppTest can simulate widget interactions (button clicks,
form submission, file upload via at.session_state injection) but doing
so for the full upload -> analysis -> render flow is significantly more
involved than the smoke tests below. That full flow is verified
instead via the underlying pure function
(run_deterministic_pipeline) tested directly against the real Sona BLW
files, plus the AppTest smoke tests confirming every page's rendering
code path is at least exception-free on load.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.core.enums import DataStatus, ExchangeCode, UnitOfMeasure
from app.core.models import MetricResult, RiskItem
from app.core.enums import RiskCategory, RiskSeverity

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_EXCEL = PROJECT_ROOT / "data" / "sample" / "Sona_BLW_Precis_screener_export.xlsx"
SAMPLE_CSV = PROJECT_ROOT / "data" / "sample" / "SONACOMS_NSE_price_history.csv"

_ALL_PAGES = [
    "Company Input", "Financial Dashboard", "Technical Dashboard",
    "Valuation Dashboard", "Risk Dashboard", "AI-IDS Score", "Human Review",
    "Final Thesis & Report",
]


class TestDashboardStartup:
    def test_app_starts_without_exception(self):
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=30)
        at.run()
        assert list(at.exception) == []

    def test_all_seven_nav_pages_registered(self):
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=30)
        at.run()
        assert at.sidebar.radio[0].options == _ALL_PAGES

    def test_defaults_to_company_input_page(self):
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=30)
        at.run()
        assert at.header[0].value == "Company Input"

    @pytest.mark.parametrize("page", _ALL_PAGES)
    def test_every_page_renders_without_exception_on_empty_state(self, page):
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=30)
        at.run()
        at.sidebar.radio[0].set_value(page).run()
        assert list(at.exception) == [], f"{page} raised: {list(at.exception)}"

    def test_sidebar_disclaimer_present(self):
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=30)
        at.run()
        captions = [c.value for c in at.sidebar.caption]
        assert any("human professional judgement" in c for c in captions)


class TestCompanyInputPipeline:
    """Direct tests of the pure orchestration function behind the
    Company Input page, against the real Sona BLW sample files."""

    def test_full_pipeline_with_excel_and_csv(self):
        from app.ui.pages.company_input import run_deterministic_pipeline

        result = run_deterministic_pipeline(
            excel_path=SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd",
            ticker="SONACOMS", exchange=ExchangeCode.NSE, sector="Auto Ancillary",
            csv_path=SAMPLE_CSV,
        )
        assert result["company"].name == "Sona BLW Precision Forgings Ltd"
        assert len(result["statements"]) == 10
        assert len(result["fundamental_metrics"]) > 0
        assert len(result["technical_metrics"]) > 0
        assert result["price_df"] is not None

    def test_pipeline_without_csv_skips_technical(self):
        from app.ui.pages.company_input import run_deterministic_pipeline

        result = run_deterministic_pipeline(
            excel_path=SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd",
            ticker="SONACOMS", exchange=ExchangeCode.NSE, sector=None, csv_path=None,
        )
        assert result["technical_metrics"] == []
        assert result["price_df"] is None
        # financials still work independently of price data
        assert len(result["fundamental_metrics"]) > 0

    def test_validation_issues_surfaced_not_silently_dropped(self):
        from app.ui.pages.company_input import run_deterministic_pipeline

        result = run_deterministic_pipeline(
            excel_path=SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd",
            ticker="SONACOMS", exchange=ExchangeCode.NSE, sector=None, csv_path=None,
        )
        # Known real finding from earlier milestones: the IPO share-count
        # discontinuity produces WARNING-level validation issues.
        assert len(result["validation_issues"]) >= 1


class TestPageHelperFunctions:
    def test_financial_dashboard_metrics_to_rows(self):
        from app.ui.pages.financial_dashboard import metrics_to_rows

        m = MetricResult(metric_name="ROE", formula="f", inputs={}, value=0.15,
                          unit=UnitOfMeasure.PERCENT, period="FY2026", status=DataStatus.OK)
        rows = metrics_to_rows([m])
        assert rows[0]["Metric"] == "ROE"
        assert rows[0]["Value"] == "15.00%"
        assert rows[0]["Status"] == "ok"

    def test_financial_dashboard_handles_missing_value(self):
        from app.ui.pages.financial_dashboard import metrics_to_rows

        m = MetricResult(metric_name="ROE", formula="f", inputs={}, value=None,
                          unit=UnitOfMeasure.PERCENT, period="FY2026", status=DataStatus.MISSING_INPUT)
        rows = metrics_to_rows([m])
        assert rows[0]["Value"] == "N/A"

    def test_technical_dashboard_format_summary(self):
        from app.ui.pages.technical_dashboard import format_technical_summary

        m = MetricResult(metric_name="RSI (14)", formula="f", inputs={}, value=75.42,
                          unit=UnitOfMeasure.RATIO, period="latest", status=DataStatus.OK)
        rows = format_technical_summary([m])
        assert rows[0]["Indicator"] == "RSI (14)"
        assert rows[0]["Value"] == "75.42"

    def test_valuation_dashboard_multiples_to_rows(self):
        from app.ui.pages.valuation_dashboard import multiples_to_rows

        m = MetricResult(metric_name="P/E", formula="f", inputs={}, value=46.3,
                          unit=UnitOfMeasure.RATIO, period="FY2026", status=DataStatus.OK)
        rows = multiples_to_rows([m])
        assert rows[0]["Multiple"] == "P/E"
        assert rows[0]["Value"] == "46.30"

    def test_risk_dashboard_risks_to_rows(self):
        from app.ui.pages.risk_dashboard import risks_to_rows

        r = RiskItem(category=RiskCategory.FINANCIAL, description="Negative FCF",
                     severity=RiskSeverity.LOW, mitigation="Capex cycle expected to normalize")
        rows = risks_to_rows([r])
        assert rows[0]["Category"] == "Financial"
        assert rows[0]["Severity"] == "LOW"
        assert rows[0]["Mitigation"] == "Capex cycle expected to normalize"

    def test_risk_dashboard_missing_mitigation_shows_dash(self):
        from app.ui.pages.risk_dashboard import risks_to_rows

        r = RiskItem(category=RiskCategory.MARKET, description="Some risk", severity=RiskSeverity.MODERATE)
        rows = risks_to_rows([r])
        assert rows[0]["Mitigation"] == "\u2014"


class TestRealStreamlitRunSysPath:
    """Regression test for a real bug a user hit running the actual
    `streamlit run app\\main.py` command from a fresh terminal: Streamlit
    only adds the SCRIPT'S OWN DIRECTORY (app/) to sys.path, not the
    project root above it, so `from app.ui.dashboard import run` failed
    with ModuleNotFoundError. AppTest could never catch this class of
    bug — it runs in-process, inheriting whatever sys.path pytest
    itself was already invoked with (which already includes the project
    root). This test spawns a genuinely separate subprocess with
    sys.path constrained to exactly what Streamlit provides, faithfully
    reproducing the real failure mode rather than testing around it."""

    def test_app_main_fixes_sys_path_so_app_package_imports_cleanly(self):
        import subprocess
        import sys

        app_dir = PROJECT_ROOT / "app"
        code = (
            "import sys\n"
            f"sys.path = [p for p in sys.path if p not in ('', r'{PROJECT_ROOT}')]\n"
            f"sys.path.insert(0, r'{app_dir}')\n"
            "import main\n"  # app/main.py loaded as top-level 'main', matching how
                              # Streamlit loads the script when only app/ is on sys.path
            "import app.ui.dashboard\n"  # must succeed only because main.py's own
                                           # module-level code fixed sys.path first
            "print('IMPORT_SUCCEEDED')\n"
        )
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert "IMPORT_SUCCEEDED" in result.stdout, (
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "ModuleNotFoundError" not in result.stderr
