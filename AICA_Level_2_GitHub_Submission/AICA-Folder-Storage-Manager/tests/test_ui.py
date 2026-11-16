import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from make_test_data import make_bulk  # noqa


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def wait_until(app, cond, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.02)
    raise TimeoutError


def test_switch_project_during_scan(env, qapp, monkeypatch):
    tmp, cat = env
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    from aica_fsm.ui.main_window import MainWindow
    make_bulk(str(tmp / "A"), 1200, seed=1)
    make_bulk(str(tmp / "B"), 100, seed=2)
    a = cat.create("Project A", str(tmp / "A"))
    b = cat.create("Project B", str(tmp / "B"))
    w = MainWindow(cat)
    w.set_active(b)
    w.start_scan(b)
    wait_until(qapp, lambda: b.project_id not in w.scan_workers)
    ov = w.pages[1]
    assert ov.cards["files"].text() == "100"
    # new project with no scan: empty dashboard
    w.set_active(a)
    assert ov.body.isHidden() and "no completed scan" in ov.empty_text.text().lower()
    # start A, switch to B before it finishes
    w.start_scan(a)
    w.set_active(b)
    snap_b = w.st.snapshot_id
    wait_until(qapp, lambda: a.project_id not in w.scan_workers)
    assert w.st.project.project_id == b.project_id
    assert w.st.snapshot_id == snap_b
    assert ov.cards["files"].text() == "100"
    assert w.pages[2].model.total == 100
    assert w.scan_panel.isHidden()
    hist = w.pages[7]
    assert all("Project A" not in (e["source"] + e["detail"]) and str(tmp / "A") not in e["source"] for e in hist.items)
    # A has its results
    w.set_active(a)
    assert ov.cards["files"].text() == "1,200"
    assert w.pages[2].model.total == 1200
    w.set_active(b)
    assert ov.cards["files"].text() == "100"
    w.close()
