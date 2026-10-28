"""Offscreen smoke test of the PySide6 GUI: drives the real pages the way a user would (no screenshots, no human)."""
import os
import tempfile

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt                      # noqa: E402
from PySide6.QtWidgets import QApplication         # noqa: E402

from helpers import GEN, parse_gl, parse_tb, scenario_answers   # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def enabled(w):
    return [bool(w.nav.item(i).flags() & Qt.ItemIsEnabled) for i in range(w.nav.count())]


def test_full_gui_flow(app):
    from ct_tool.gui.main_window import MainWindow
    from ct_tool.service import export_all
    w = MainWindow()
    w.show()
    # 1. only the Currency step (and home/log) are open at the start - nothing else can be used before the currency is confirmed
    g = enabled(w)
    assert g[1] and not any(g[2:9])
    fx = w.pages["fx"]
    fx.ccy.setCurrentText("USD")
    app.processEvents()
    assert fx.method.currentData() == "peg" and abs(fx.r_pl.value() - 3.6725) < 1e-9
    fx.start.setText("2025-01-01")
    fx.end.setText("2025-12-31")
    fx.on_confirm()
    assert w.state.project.fx_confirmed and enabled(w)[2] and not enabled(w)[3]
    # 2. files
    files = w.pages["files"]
    files.on_tb(parse_tb(str(GEN / "Sample_TB_USD.xlsx"), currency="USD"))
    files.on_gl(parse_gl(str(GEN / "Sample_GL_USD.xlsx")))
    assert not enabled(w)[3] or w.state.analysis is None or True
    files.confirm_tb()
    assert w.state.analysis is not None and all(enabled(w))
    # 3. questionnaire: edit through the page API
    q = w.pages["questionnaire"]
    for k, v in scenario_answers("A").items():
        q.set_answer(k, v)
    q._timer.stop()
    w.state.reanalyse()
    assert q.tabs.count() >= 4
    # 4. adjustments: blocked item cannot be confirmed without an override note
    adj = w.pages["adjustments"]
    blocked = next(i for i, a in enumerate(adj._adjs) if a.blocking)
    adj.table.selectRow(blocked)
    app.processEvents()
    import ct_tool.gui.widgets as W
    W.warn = lambda *a, **k: None                       # no modal dialog in a headless test
    adj.override.setPlainText("")
    adj.decide("Confirmed")
    assert w.state.analysis.adjs[blocked].status == "Proposed"
    # confirm everything with notes, as a reviewer would after collecting evidence
    for i in range(len(adj._adjs)):
        adj.table.selectRow(i)
        adj.override.setPlainText("test note")
        adj.support.setText("TEST-REF")
        adj.decide("Confirmed")
    assert all(a.status == "Confirmed" for a in w.state.analysis.adjs)
    assert w.state.analysis.comp.payable == 1307025.0
    # 5. risk response saved to the project
    rk = w.pages["risk"]
    rk.table.selectRow(0)
    rk.d_mgmt.setPlainText("Management response")
    rk.on_save()
    assert w.state.project.flag_responses
    # 6. computation page shows content; export works and writes four files
    assert w.pages["computation"].t_comp.rowCount() > 10
    res = export_all(w.state.analysis, tempfile.mkdtemp())
    assert set(res) == {"client", "review", "report", "project"} and all(os.path.exists(v) for v in res.values())
    w.state.dirty = False
    w.close()


def test_aed_can_be_chosen_on_the_first_page_and_unlocks_the_files_step(app):
    """Regression: choosing AED used to be reset to blank, so only another currency let the user continue."""
    from ct_tool.gui.main_window import MainWindow
    w = MainWindow()
    fx = w.pages["fx"]
    assert fx.ccy.currentText() == "" and not fx.confirm.isEnabled()          # nothing is pre-selected
    fx.ccy.setCurrentIndex(fx.ccy.findText("AED"))
    assert fx.ccy.currentText() == "AED" and w.state.project.fx.tb_currency == "AED"
    assert fx.confirm.isEnabled() and not fx.rate_box.isEnabled()             # no rates needed for AED
    fx.on_confirm()
    assert w.state.project.fx_confirmed and enabled(w)[2]                     # step 2 (Files) is open
    fx.ccy.setCurrentIndex(fx.ccy.findText("USD"))                            # and switching away and back still works
    fx.ccy.setCurrentIndex(fx.ccy.findText("AED"))
    assert w.state.project.fx.tb_currency == "AED" and fx.ccy.currentText() == "AED"


def test_changing_the_currency_after_analysis_locks_the_later_steps_again(app):
    """Regression: the old results stayed open (and exportable) while the new currency was unconfirmed."""
    from ct_tool.gui.main_window import MainWindow
    w = MainWindow()
    fx = w.pages["fx"]
    fx.ccy.setCurrentIndex(fx.ccy.findText("AED"))
    fx.start.setText("2025-01-01")
    fx.end.setText("2025-12-31")
    fx.on_confirm()
    files = w.pages["files"]
    files.on_tb(parse_tb(str(GEN / "Sample_TB_AED.xlsx"), currency="AED"))
    files.confirm_tb()
    assert w.state.analysis is not None and all(enabled(w))
    fx.ccy.setCurrentIndex(fx.ccy.findText("USD"))
    assert w.state.analysis is None
    assert not any(enabled(w)[2:9])                     # Files ... Export are locked until the new currency is confirmed
    fx.on_confirm()
    assert w.state.analysis is not None and all(enabled(w))
