"""v7 UI behaviour: automatic grid lines, ledger fields select-all."""
from decimal import Decimal as D

from app.engine.voucher import VLine, Voucher


def test_grid_adds_balancing_line_and_drops_empty(qapp):
    from app.ui.common import VoucherGrid
    g = VoucherGrid()
    g.set_voucher(Voucher("Journal", "20261101", [VLine("Rent", D("1000"), True), VLine("Bank", D("600"), False)]),
                  ["Rent", "Bank", "Cash"])
    g.table.setCurrentCell(1, 2)
    assert g.tab(True) is True                       # unbalanced: a new line appears
    assert g.table.rowCount() == 3
    assert g.table.item(2, 2).text() == "400.00"     # difference on the short (Cr) side
    g.table.setCurrentCell(0, 0)                     # leave it untouched -> it disappears
    qapp.processEvents()
    assert g.table.rowCount() == 2
    g.table.setCurrentCell(1, 2)
    g.tab(True)
    g.table.cellWidget(2, 0).setCurrentText("Cash")
    g.table.setCurrentCell(0, 0)
    qapp.processEvents()
    assert g.table.rowCount() == 3 and [l.ledger for l in g.lines()] == ["Rent", "Bank", "Cash"]
    g.table.setCurrentCell(2, 2)
    assert g.tab(True) is False                      # balanced: focus leaves the grid


def test_tab_order_ledger_to_amount(qapp):
    from app.ui.common import VoucherGrid
    g = VoucherGrid()
    g.set_voucher(Voucher("Journal", "", [VLine("Rent", D("10"), True), VLine("Bank", D("10"), False)]), ["Rent"])
    g.table.setCurrentCell(1, 0)
    g.tab(True)
    assert g.table.currentColumn() == 2              # credit line -> Cr column


def test_ledger_combo_selects_all_on_focus(qapp):
    from PyQt6.QtWidgets import QWidget, QVBoxLayout
    from app.ui.common import LedgerCombo
    w = QWidget()
    lay = QVBoxLayout(w)
    a, b = LedgerCombo(["Office Rent", "Cash"], "Office Rent"), LedgerCombo(["Office Rent", "Cash"], "Cash")
    lay.addWidget(a)
    lay.addWidget(b)
    w.show()
    w.activateWindow()
    from PyQt6.QtCore import QEvent, Qt
    from PyQt6.QtGui import QFocusEvent
    from PyQt6.QtTest import QTest
    qapp.sendEvent(a.lineEdit(), QFocusEvent(QEvent.Type.FocusIn, Qt.FocusReason.TabFocusReason))
    QTest.qWait(30)
    assert a.lineEdit().selectedText() == "Office Rent"
    assert a.completer().filterMode().name == "MatchContains"
