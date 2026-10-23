import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGE = str(ROOT / "ui" / "statements.py")


def fresh():
    at = AppTest.from_file(PAGE, default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    return at


def click(at, label):
    next(b for b in at.button if b.label.startswith(label)).click().run()
    assert not at.exception, at.exception


def test_landing_page_asks_for_a_trial_balance():
    at = fresh()
    assert any("Load a trial balance" in i.value for i in at.info)
    assert not at.metric


def test_upload_flow_from_load_to_download(monkeypatch):
    from fsbuilder import pipeline as P
    at = _run_upload(monkeypatch, P.SAMPLE_TB, "tb.csv")
    m = {x.label: x.value for x in at.metric}
    assert m["Ledgers"] == "68" and m["Opening difference"] == "Agrees"
    assert m["Tie-out checks passed"] == "72 of 72" and m["AI observations"] == "not run"
    assert any("already included the year's profit" in i.value for i in at.info)       # the Tally quirk is explained
    assert not at.error
    click(at, "Generate Word")
    labels = [d.proto.label for d in at.get("download_button")]
    assert {"Statements (Word)", "Statements (Excel)", "Review (Word)", "Review (Excel)"} <= set(labels)


def test_upload_source_without_a_file_explains_what_to_do():
    at = fresh()
    at.radio[0].set_value("Upload Excel or CSV").run()
    at.text_input(key="co_Upload Excel or CSV").set_value("Test Co").run()
    click(at, "Load trial balance")
    assert any("Choose a trial balance file" in e.value for e in at.error)
    assert not at.metric


def test_missing_company_name_is_rejected():
    at = fresh()
    at.radio[0].set_value("Pull from TallyPrime").run()
    click(at, "Load trial balance")
    assert any("Enter the company name" in e.value for e in at.error)


def test_unreachable_tally_gives_setup_instructions_not_a_crash():
    at = fresh()
    at.radio[0].set_value("Pull from TallyPrime").run()
    at.text_input(key="co_Pull from TallyPrime").set_value("Some Company").run()
    next(n for n in at.number_input if n.label == "Port").set_value(1).run()      # nothing listens on port 1
    click(at, "Load trial balance")
    assert any("did not answer" in e.value and "Connectivity" in e.value for e in at.error)
    assert not at.metric


def test_ai_button_is_locked_until_consent_and_key(monkeypatch):
    from fsbuilder import pipeline as P
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    at = _run_upload(monkeypatch, P.SAMPLE_TB, "tb.csv")
    btn = next(b for b in at.button if b.label == "Run AI review")
    assert btn.disabled


def _upload_page():
    """The page with the trial balance uploader replaced by a fake that returns the file named in the environment."""
    def page():
        import io
        import os
        from pathlib import Path

        import streamlit as st
        from streamlit.delta_generator import DeltaGenerator

        class Upload(io.BytesIO):
            name = None

        def fake(self, label, *a, **k):
            if label.startswith("Trial balance exported"):
                u = Upload(Path(os.environ["TB_UPLOAD_PATH"]).read_bytes())
                u.name = os.environ["TB_UPLOAD_NAME"]
                return u
            return None
        original = DeltaGenerator.file_uploader
        DeltaGenerator.file_uploader = fake
        try:
            page_path = Path(os.environ["TB_PAGE"])
            exec(compile(page_path.read_text(encoding="utf-8"), "page", "exec"),
                 {"__name__": "__main__", "__file__": str(page_path)})
        finally:
            DeltaGenerator.file_uploader = original    # never leak the fake into other tests
    return AppTest.from_function(page, default_timeout=120)


def _run_upload(monkeypatch, path, name, company="Acme Ltd", **state):
    monkeypatch.setenv("TB_UPLOAD_PATH", str(path))
    monkeypatch.setenv("TB_UPLOAD_NAME", name)
    monkeypatch.setenv("TB_PAGE", PAGE)
    at = _upload_page()
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, at.exception
    at.radio[0].set_value("Upload Excel or CSV").run()
    at.text_input(key="co_Upload Excel or CSV").set_value(company).run()
    click(at, "Load trial balance")
    return at


def test_excel_template_uploads_end_to_end(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT))
    from fsbuilder import pipeline as P
    f = tmp_path / "my_tb.xlsx"
    f.write_bytes(P.sample_xlsx_bytes())
    at = _run_upload(monkeypatch, f, "my_tb.xlsx")
    assert not at.error, [e.value for e in at.error]
    m = {x.label: x.value for x in at.metric}
    assert m["Ledgers"] == "68" and m["Tie-out checks passed"] == "72 of 72"
    assert any("Acme Ltd" in s.value for s in at.success)


def test_csv_upload_still_works_end_to_end(monkeypatch):
    sys.path.insert(0, str(ROOT))
    from fsbuilder import pipeline as P
    at = _run_upload(monkeypatch, P.SAMPLE_TB, "tb.csv")
    assert not at.error and {x.label: x.value for x in at.metric}["Ledgers"] == "68"


def test_a_bad_workbook_shows_the_reason_on_the_page(tmp_path, monkeypatch):
    from openpyxl import Workbook
    wb = Workbook()
    wb.active.append(["just", "some", "numbers"])
    f = tmp_path / "bad.xlsx"
    wb.save(f)
    at = _run_upload(monkeypatch, f, "bad.xlsx")
    assert any("header row" in e.value and "template" in e.value for e in at.error)
    assert not at.metric
