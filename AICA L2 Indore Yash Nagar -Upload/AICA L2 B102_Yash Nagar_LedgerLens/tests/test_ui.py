import json
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

PAGES = {name: str(ROOT / "ui" / f"{name}.py") for name in ("home", "settings", "statements", "day_book")}


def run(path, **state):
    at = AppTest.from_file(path, default_timeout=120)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def loaded(monkeypatch, **state):
    """The Financial Statements Builder with the sample trial balance uploaded and loaded."""
    from fsbuilder import pipeline as P
    from test_builder_page import _run_upload
    return _run_upload(monkeypatch, P.SAMPLE_TB, "tb.csv", **state)


def html(at):
    return " ".join(m.value for m in at.markdown)


# ------------------------------------------------------------------ the whole app
def test_the_app_starts_and_shows_the_brand():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    text = html(at)
    assert "LedgerLens" in text and "Financial Statements Builder" in text and "Day Book Audit" in text


@pytest.mark.parametrize("name", list(PAGES))
def test_every_page_runs_on_its_own(name):
    run(PAGES[name])


def test_home_is_accurate_about_what_the_tool_is_not():
    text = html(run(PAGES["home"]))
    assert "not an audit opinion" in text and "AI is optional" in text and "FY 2025-26" in text


# ------------------------------------------------------------------ settings and the shared AI key
def test_settings_stores_the_key_and_consent_for_other_pages():
    at = run(PAGES["settings"])
    at.text_input[0].set_value("secret-key").run()
    at.checkbox[0].check().run()
    assert at.session_state["gemini_key"] == "secret-key" and at.session_state["ai_consent"] is True
    assert "AI ready" in html(at)


def test_key_without_consent_is_not_ready(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)    # the real .env may hold a key
    at = run(PAGES["settings"], gemini_key="k", ai_consent=False)
    assert "consent not given" in html(at)
    assert "AI off" in html(run(PAGES["settings"], gemini_key="", ai_consent=True))


def test_the_connection_test_reports_success_and_failure(monkeypatch):
    from fsbuilder.reviewer import llm

    class Good:
        def __init__(self, key, model): pass
        def __call__(self, system, prompt): return '{"ok": true}'

    class Bad:
        def __init__(self, key, model): raise llm.LLMError("quota exceeded")

    monkeypatch.setattr(llm, "GeminiLLM", Good)
    at = run(PAGES["settings"], gemini_key="k", ai_consent=True)
    next(b for b in at.button if b.label == "Test the connection").click().run()
    assert any("Connected" in s.value for s in at.success)
    monkeypatch.setattr(llm, "GeminiLLM", Bad)
    at = run(PAGES["settings"], gemini_key="k", ai_consent=True)
    next(b for b in at.button if b.label == "Test the connection").click().run()
    assert any("Could not connect" in e.value and "quota exceeded" in e.value for e in at.error)


def test_the_connection_test_is_disabled_without_a_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)    # the real .env may hold a key
    at = run(PAGES["settings"], gemini_key="")
    assert next(b for b in at.button if b.label == "Test the connection").disabled


def test_the_env_file_key_is_used_when_nothing_is_typed(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    from ui import ai
    at = run(PAGES["settings"], ai_consent=True)
    assert "AI ready" in html(at) and "the .env file" in " ".join(c.value for c in at.caption)


def test_the_statements_page_uses_the_shared_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    off = loaded(monkeypatch)
    assert next(b for b in off.button if b.label == "Run AI review").disabled
    on = loaded(monkeypatch, gemini_key="k", ai_consent=True)
    assert not next(b for b in on.button if b.label == "Run AI review").disabled


def test_the_ai_review_runs_with_the_shared_key_and_results_appear(monkeypatch):
    from fsbuilder.reviewer import llm

    class Fake:
        def __init__(self, key, model): pass
        def __call__(self, system, prompt):
            if "changed by more than 25%" in prompt:
                return json.dumps({"ratios": []})
            return json.dumps({"observations": []})

    monkeypatch.setattr(llm, "GeminiLLM", Fake)
    at = loaded(monkeypatch, gemini_key="k", ai_consent=True)
    next(b for b in at.button if b.label == "Run AI review").click().run()
    assert not at.exception, at.exception
    assert {m.label: m.value for m in at.metric}["AI observations"] == "0"


# ------------------------------------------------------------------ the page is five tabs, one per phase
def test_the_statements_page_is_organised_in_five_phases(monkeypatch):
    at = loaded(monkeypatch)
    labels = [t.label for t in at.tabs]
    assert ["1 · Load", "2 · Check & map", "3 · Statements", "4 · Review & AI", "5 · Download"] == [x for x in labels if x[:1].isdigit()]
    assert "AI review of the statements" in labels
    assert not at.exception


def test_before_a_trial_balance_is_loaded_the_other_tabs_say_what_to_do():
    at = run(PAGES["statements"])
    assert sum("Load a trial balance on the first tab" in i.value for i in at.info) == 4


def test_each_ai_review_says_what_it_covers(monkeypatch):
    at = loaded(monkeypatch)
    assert any("This AI reviews the financial statements" in i.value and "does not read the Day Book" in i.value for i in at.info)


# ------------------------------------------------------------------ notes drill-down
def test_a_note_can_be_opened_and_shows_which_line_uses_it(monkeypatch):
    at = loaded(monkeypatch)
    pick = next(s for s in at.selectbox if s.key == "note_pick")
    assert "Note 4: Trade payables" in pick.options
    pick.set_value("Note 4: Trade payables").run()
    assert not at.exception, at.exception
    assert any("Note 4: Trade payables" in m.value for m in at.markdown)
    assert any("Used by: (a) Trade payables" in c.value for c in at.caption)


def test_notes_that_need_information_say_so(monkeypatch):
    at = loaded(monkeypatch)
    next(s for s in at.selectbox if s.key == "note_pick").set_value("Note 1: Share capital").run()
    assert any("Information required (not available in Tally)" in w.value and "Authorised, issued" in w.value for w in at.warning)


def test_the_ppe_note_shows_its_movement_table(monkeypatch):
    at = loaded(monkeypatch)
    next(s for s in at.selectbox if s.key == "note_pick").set_value("Note 6: Property, plant and equipment").run()
    assert any("Movement in net book value" in m.value for m in at.markdown)


def test_consent_can_be_given_where_the_ai_review_runs(monkeypatch):
    at = loaded(monkeypatch, gemini_key="k", ai_consent=False)
    run_btn = next(b for b in at.button if b.label == "Run AI review")
    assert run_btn.disabled
    next(c for c in at.checkbox if c.key == "ai_consent_inline").check().run()
    assert not at.exception, at.exception
    assert not next(b for b in at.button if b.label == "Run AI review").disabled
    assert at.session_state["ai_consent"] is True
