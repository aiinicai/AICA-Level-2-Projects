"""
End-to-end UI smoke test.

Drives the real Streamlit application headlessly through all five screens and
every navigation control, asserting that no screen raises and — critically —
that the findings screen does not blow up the element count. The original build
rendered one expander per raw exception (1,103 expanders / 16,567 markdown
elements) which froze the browser; the assertions below are the regression
guard against that returning.
"""
import os
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.py")

# Streamlit renders a browser element per component; beyond a few hundred the
# client becomes unusable. Screen 4 must stay well inside this.
MAX_MARKDOWN_ELEMENTS = 700
MAX_EXPANDERS = 60


def _no_exceptions(at, where):
    assert not at.exception, f"{where} raised: {[str(e.value) for e in at.exception]}"


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(APP, default_timeout=900)
    at.run()
    return at


def _click(at, predicate, where):
    matches = [b for b in at.button if predicate(b.label)]
    assert matches, f"No button matching {where}. Available: {[b.label for b in at.button]}"
    matches[0].click().run()
    _no_exceptions(at, where)
    return at


def test_full_journey_all_screens_and_buttons():
    at = AppTest.from_file(APP, default_timeout=900)
    at.run()
    _no_exceptions(at, "screen 1 initial render")

    # Screen 1 — the primary action is gated until predication is supplied
    cont = [b for b in at.button if "Continue to Upload" in b.label][0]
    assert cont.disabled, "Continue must be disabled without a predication note"

    _click(at, lambda l: "demo" in l.lower(), "load demo engagement")
    cont = [b for b in at.button if "Continue to Upload" in b.label][0]
    assert not cont.disabled, "Continue must enable once predication is present"

    _click(at, lambda l: "Continue to Upload" in l, "continue to upload")
    assert at.session_state["screen"] == 2

    # Screen 2 — sample data, custody hashing, arithmetic verification
    _click(at, lambda l: "sample" in l.lower(), "load sample trial balance")
    assert at.session_state["ledgers_df"] is not None
    assert at.session_state["file_custody_info"][0]["sha256"]

    _click(at, lambda l: "Proceed to Governance" in l, "proceed to governance")
    assert at.session_state["screen"] == 3
    assert at.session_state["custody_entry"]["run_id"]

    # Screen 3 — questionnaire and presets
    assert len(at.radio) == 15, "15 governance questions expected"
    _click(at, lambda l: "Partly" in l, "set all to partly")
    _click(at, lambda l: "Run Full Forensic Analysis" in l, "run analysis")
    assert at.session_state["screen"] == 4

    # Screen 4 — the regression guard
    assert len(at.markdown) < MAX_MARKDOWN_ELEMENTS, (
        f"Findings screen rendered {len(at.markdown)} markdown elements — "
        f"the browser cannot cope beyond ~{MAX_MARKDOWN_ELEMENTS}."
    )
    assert len(at.expander) < MAX_EXPANDERS, (
        f"Findings screen rendered {len(at.expander)} expanders — must be paginated."
    )
    assert len(at.tabs) == 6, "Six findings tabs expected"

    scoring = at.session_state["analysis_results"]["scoring"]
    assert 0 <= scoring["entity_score"] <= 100, "Entity score must be bounded 0-100"
    assert scoring["bucket"] in ("RED", "YELLOW", "GREEN")
    assert scoring["stats"]["retained"] < scoring["stats"]["raw_instances"], \
        "De-duplication and suppression must reduce the raw instance count"

    # pagination both ways
    _click(at, lambda l: l == "Next →", "next page")
    _click(at, lambda l: l == "← Previous", "previous page")

    # filters
    at.multiselect[0].set_value(["RED"]); at.run()
    _no_exceptions(at, "severity filter")
    at.text_input[0].set_value("Suspense"); at.run()
    _no_exceptions(at, "keyword search")
    at.text_input[0].set_value(""); at.multiselect[0].set_value(["RED", "YELLOW"]); at.run()

    # Screen 5 — exports
    _click(at, lambda l: "Export & Requisition" in l, "proceed to export")
    assert at.session_state["screen"] == 5

    _click(at, lambda l: l == "Generate working paper", "generate working paper")
    wp = at.session_state["exports"]["wp"]
    assert wp[:2] == b"PK", "Working paper must be a valid xlsx (zip) container"
    assert len(wp) > 20_000

    _click(at, lambda l: l == "Generate requisition list", "generate requisition")
    pdf = at.session_state["exports"]["req"]
    assert pdf[:4] == b"%PDF", "Requisition must be a valid PDF"

    labels = [d.label for d in at.get("download_button")]
    for expected in ("working paper", "requisition list", "custody log", "Save engagement"):
        assert any(expected.lower() in l.lower() for l in labels), \
            f"Missing download control for {expected}. Present: {labels}"

    # back-navigation and reset
    _click(at, lambda l: "Back to Findings" in l, "back to findings")
    assert at.session_state["screen"] == 4
    _click(at, lambda l: "Reset Engagement" in l, "reset")
    assert at.session_state["screen"] == 1
    assert at.session_state["analysis_results"] is None


def test_skip_questionnaire_path():
    at = AppTest.from_file(APP, default_timeout=900)
    at.run()
    _click(at, lambda l: "demo" in l.lower(), "demo")
    _click(at, lambda l: "Continue to Upload" in l, "continue")
    _click(at, lambda l: "sample" in l.lower(), "sample")
    _click(at, lambda l: "Proceed to Governance" in l, "governance")
    _click(at, lambda l: "not assessed" in l, "skip questionnaire")

    assert at.session_state["screen"] == 4
    scoring = at.session_state["analysis_results"]["scoring"]
    assert scoring["governance_status"] == "not assessed"
    assert scoring["governance_factor"] == 1.0, "Skipping must apply no overlay"
