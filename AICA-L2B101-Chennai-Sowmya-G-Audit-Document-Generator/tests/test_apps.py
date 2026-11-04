"""Tests for the two screens: the desktop window and the browser (Streamlit) app.

The desktop tests need a display; on a server run them with:
    xvfb-run -a python -m pytest -v tests
"""
import glob
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
FIX = os.path.join(HERE, "fixtures")


# ------------------------------------------------------------------
# Desktop window (tkinter) - the same code that becomes the .exe
# ------------------------------------------------------------------

def _display_available():
    if sys.platform.startswith("win") or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY"))


needs_display = pytest.mark.skipif(not _display_available(), reason="no display")


@pytest.fixture
def window(monkeypatch):
    import tkinter as tk
    import desktop_app as app
    messages = []
    for name in ("showinfo", "showwarning", "showerror"):
        monkeypatch.setattr(app.messagebox, name,
                            lambda title, text, n=name: messages.append((n, text)))
    monkeypatch.setattr(app.messagebox, "askyesno", lambda *a, **k: False)
    root = tk.Tk()
    gui = app.GeneratorApp(root)
    yield app, gui, messages
    root.destroy()


@needs_display
def test_window_loads_mca_pdf(window, monkeypatch):
    app, gui, messages = window
    pdf = os.path.join(FIX, "mca_v3_two_line_address.pdf")
    monkeypatch.setattr(app.filedialog, "askopenfilename", lambda **k: pdf)
    gui.load_from_pdf()
    assert gui.vars["company"].get() == "MEENAKSHI TEXTILE TRADERS PRIVATE LIMITED"
    assert gui.vars["address"].get().startswith("NO 12, SOUTH MASI STREET")
    assert gui.vars["dir_name_1"].get() == "VALLIAMMAI RAMANATHAN"
    assert gui.vars["dir_desig_0"].get() == "Director"         # designation not taken
    assert gui.vars["private"].get() is True
    assert messages[-1][0] == "showinfo"


@needs_display
def test_window_rejects_incomplete_form(window):
    app, gui, messages = window
    gui.generate()
    kind, text = messages[-1]
    assert kind == "showwarning"
    for missing in ("Company name", "CIN", "FRN", "Membership no.", "director"):
        assert missing in text


@needs_display
def test_window_needs_audit_trail_date(window, monkeypatch):
    app, gui, messages = window
    gui.vars["audit_trail"].set(app.AUDIT_TRAIL_OPTIONS[1])
    gui.update_audit_trail()
    assert str(gui.audit_trail_entry.cget("state")) == "normal"
    gui.generate()
    assert "enabled from" in messages[-1][1]
    gui.vars["audit_trail"].set(app.AUDIT_TRAIL_OPTIONS[0])
    gui.update_audit_trail()
    assert str(gui.audit_trail_entry.cget("state")) == "disabled"


@needs_display
def test_window_generates_four_documents(window, monkeypatch, tmp_path):
    app, gui, messages = window
    pdf = os.path.join(FIX, "mca_v3_three_line_address.pdf")
    monkeypatch.setattr(app.filedialog, "askopenfilename", lambda **k: pdf)
    gui.load_from_pdf()
    gui.vars["frn"].set("012345S")
    gui.vars["membership"].set("234567")
    gui.vars["folder"].set(str(tmp_path))
    gui.generate()
    files = sorted(os.path.basename(f) for f in glob.glob(str(tmp_path / "*" / "*.docx")))
    assert files == ["1_Letter_of_Engagement.docx", "2_DSC_Authorisation_Letter.docx",
                     "3_Letter_of_Representation.docx", "4_Independent_Auditors_Report.docx"]
    assert "Saved 4 document(s)" in gui.status.cget("text")


# ------------------------------------------------------------------
# Browser app (Streamlit)
# ------------------------------------------------------------------

def _app():
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(os.path.join(ROOT, "streamlit_app.py"), default_timeout=60)


def test_streamlit_app_starts():
    at = _app().run()
    assert not at.exception
    assert [t.label for t in at.tabs] == ["1. Company & Directors", "2. Opinion & Reporting",
                                          "3. Company facts", "4. Dates"]


def test_streamlit_lists_missing_details():
    at = _app().run()
    at.button[0].click().run()
    text = at.error[0].value
    for missing in ("Company name", "CIN", "FRN", "director"):
        assert missing in text


def test_streamlit_generates_audit_report():
    at = _app().run()
    at.text_input(key="company").set_value("MEENAKSHI TEXTILE TRADERS PRIVATE LIMITED")
    at.text_input(key="cin").set_value("U74999TN2019PTC123456")
    at.text_area(key="address").set_value("NO 12, SOUTH MASI STREET, MADURAI, 625001")
    at.text_input(key="frn").set_value("012345S")
    at.text_input(key="membership").set_value("234567")
    for key in ("gen_eng", "gen_dsc", "gen_mrl"):          # letters need directors
        at.checkbox(key=key).uncheck()
    at.run()
    at.button[0].click().run()
    assert not at.exception
    assert "Created 1 document(s)" in at.success[0].value
    folder, files, bundle = at.session_state["output"]
    assert folder == "MEENAKSHI_TEXTILE_TRADERS_PRIVATE_LIMITED_FY_" + at.session_state["fy"]
    assert list(files) == ["4_Independent_Auditors_Report.docx"]
    assert bundle[:2] == b"PK"                             # a real zip file
