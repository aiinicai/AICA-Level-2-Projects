from datetime import date
import pytest
from PySide6.QtCore import Qt
from app.services.demo import load_demo
from app.ui.theme import STYLE
from app.ui.window import MainWindow


@pytest.fixture
def window(db,qtbot,qapp):
    load_demo(db,date(2026,11,13))
    qapp.setStyleSheet(STYLE)
    view=MainWindow(db,background=False)
    qtbot.addWidget(view)
    view.show()
    yield view
    view.quitting=True
    view.tray.hide()
    view.close()


def test_all_navigation_and_calendar_views(window,qtbot):
    for index in range(10):
        window.navigation.setCurrentRow(index)
        qtbot.wait(10)
        assert window.page_title.text()
    window.navigation.setCurrentRow(1)
    for view in ("Day","Week","Month","Agenda"):
        window.view.setCurrentText(view)
        qtbot.wait(10)
    assert window.model.rowCount()>0


def test_gui_search_detail_knowledge_timezone(window,qtbot):
    window.search.setText("CPI")
    qtbot.wait(300)
    assert window.model.rowCount()>0
    window.table.selectRow(0)
    qtbot.wait(10)
    assert "SYNTHETIC SAMPLE" in window.details.overview.toPlainText()
    window.zone.setCurrentText("Australia/Sydney")
    assert window.db.setting("timezone")=="Australia/Sydney"
    window.navigation.setCurrentRow(6)
    assert "SOURCE REFERENCES" in window.article_view.toPlainText()


def test_watchlist_and_notification_simulation_ui(window,qtbot):
    window.navigation.setCurrentRow(7)
    window.member_input.setText("DEMOASTER"); window.add_member()
    assert window.members.count()==1
    window.navigation.setCurrentRow(8)
    window.simulate()
    assert window.rules_table.rowCount()==1
    assert window.notification_table.rowCount()==1
    assert window.notification_rows[0]["state"]=="Pending"

