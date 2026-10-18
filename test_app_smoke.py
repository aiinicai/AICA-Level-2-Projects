"""Smoke test for app.py page logic using a stand-in for streamlit.
This checks the Python in every page runs without errors (wrong column names, typos,
crashes on empty data). It does NOT check how the screens look - run the real app for that.
Developed by CA Sapan"""
import os
import runpy
import sys
import tempfile
from datetime import date
from unittest.mock import MagicMock

import core


class StopApp(Exception):
    pass


def make_st(page, submit, seed_flag):
    st = MagicMock(name="streamlit")
    st.sidebar.radio.return_value = page
    st.sidebar.button.return_value = seed_flag

    class Col:
        """A column behaves like st itself (as in real Streamlit): same widgets, same return values."""
        def __getattr__(self, name):
            return getattr(st, name)
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def columns(spec, **kw):
        n = spec if isinstance(spec, int) else len(spec)
        return [Col() for _ in range(n)]

    def selectbox(label, options=None, format_func=None, index=0, **kw):
        options = list(options or [])
        if format_func:
            for o in options:
                format_func(o)          # exercise label builders
        return options[min(index, len(options) - 1)] if options else None

    def multiselect(label, options=None, default=None, **kw):
        return list(default if default is not None else options)

    st.columns.side_effect = columns
    st.selectbox.side_effect = selectbox
    st.multiselect.side_effect = multiselect
    st.radio.side_effect = lambda label, options, **kw: options[0]
    st.date_input.side_effect = lambda label, value=None, **kw: value or date.today()
    st.text_input.side_effect = lambda label, value="", **kw: value
    st.text_area.side_effect = lambda label, value="", **kw: value
    st.number_input.side_effect = lambda label, value=0, **kw: value
    st.checkbox.return_value = False
    st.button.return_value = False
    st.form_submit_button.return_value = submit
    st.stop.side_effect = StopApp
    return st


def run(page, submit, seed, preload):
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "t.db")
        if preload:
            c = core.connect(db)
            core.seed_sample(c, date.today())
            c.close()
        os.environ["WORK_DIARY_DB"] = db
        st = make_st(page, submit, seed)
        sys.modules["streamlit"] = st
        try:
            runpy.run_path("app.py", run_name="__main__")
        except StopApp:
            pass
        return st


if __name__ == "__main__":
    pages = ["Today", "All tasks", "KPIs", "Dashboard", "Report"]
    failures = 0
    for preload in (True, False):
        for page in pages:
            for submit in (False, True):
                label = f"{page:10s} data={'sample' if preload else 'empty '} submit={submit}"
                try:
                    st = run(page, submit, seed=not preload, preload=preload)
                    assert st.title.called, "page never rendered a title"
                    print("PASS", label)
                except Exception as ex:
                    failures += 1
                    print("FAIL", label, "->", type(ex).__name__, ex)
    print("\nfailures:", failures)
    raise SystemExit(1 if failures else 0)
