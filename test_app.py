from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def click(app, label):
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception


def prepared_sample(app):
    click(app, "Try Sample Notice")
    assert next(b for b in app.button if b.label == "Generate Comprehensive Reply").disabled
    click(app, "Research law & case law")
    click(app, "Prepare strategy")
    click(app, "Generate Comprehensive Reply")


def test_sample_edit_style_regenerate_restore_and_clear():
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert not app.exception
    assert not app.sidebar.children
    prepared_sample(app)
    assert app.session_state["demo"] is True
    edited = app.text_area(key="draft_reply").value + "\nA user edit to preserve."
    app.text_area(key="draft_reply").set_value(edited).run()
    app.checkbox[0].check().run()
    assert app.text_area(key="draft_reply").value == edited
    app.radio[0].set_value("Firm").run()
    assert app.text_area(key="draft_reply").value == edited
    click(app, "Regenerate Draft")
    assert "We respectfully request" in app.text_area(key="draft_reply").value
    click(app, "Restore previous draft")
    assert app.text_area(key="draft_reply").value == edited
    click(app, "Clear notice & start again")
    assert len(app.text_area) == 0
    assert "analysis" not in app.session_state


def test_failed_regeneration_keeps_edits(monkeypatch):
    from utils.validators import AppError
    app = AppTest.from_file(APP, default_timeout=30).run()
    prepared_sample(app)
    app.text_area(key="draft_reply").set_value("My reviewed reply").run()
    app.session_state["demo"] = False
    def fail(*_args, **_kwargs):
        raise AppError("The provider is unavailable. Please retry.")
    monkeypatch.setattr("services.case_service.CaseService.comprehensive_draft", fail)
    monkeypatch.setattr("services.llm_service.LLMService.__init__", lambda self: None)
    click(app, "Regenerate Draft")
    assert app.text_area(key="draft_reply").value == "My reviewed reply"
    assert "unavailable" in app.error[0].value


def test_evidence_notes_invalidate_strategy_without_losing_editor():
    app = AppTest.from_file(APP, default_timeout=30).run()
    prepared_sample(app)
    app.text_area(key="draft_reply").set_value("A valuable manual edit").run()
    app.text_area(key="case_client_notes").set_value("Certificates are not yet available.").run()
    assert not app.exception
    assert "case_strategy" not in app.session_state
    assert app.text_area(key="draft_reply").value == "A valuable manual edit"
    assert next(b for b in app.button if b.label == "Regenerate Draft").disabled
    click(app, "Prepare strategy")
    assert app.text_area(key="draft_reply").value == "A valuable manual edit"
    assert any("predates changes" in w.value for w in app.warning)


def test_public_topic_changes_invalidate_research_and_strategy():
    app = AppTest.from_file(APP, default_timeout=30).run()
    prepared_sample(app)
    app.text_area(key="case_topics").set_value("Different legal period and jurisdiction").run()
    assert "case_research" not in app.session_state
    assert "case_strategy" not in app.session_state
    assert next(b for b in app.button if b.label == "Prepare strategy").disabled


def test_explicit_research_gap_path_works_without_inventing_authorities():
    app = AppTest.from_file(APP, default_timeout=30).run()
    click(app, "Try Sample Notice")
    app.checkbox(key="case_skip_research").check().run()
    click(app, "Prepare strategy")
    click(app, "Generate Comprehensive Reply")
    assert "case_research" not in app.session_state
    assert app.session_state["case_strategy"].issues[0].authorities_to_use == []
