import pytest
from PyQt6.QtWidgets import QApplication, QPushButton
from PyQt6.QtCore import Qt, QTimer
from ui.calculator_view import CalculatorView
from ui.widgets import IndianCurrencyInput


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_improvement_amount_cell_formatting(qapp):
    """Verifies that the amount cell displays clean Indian format without duplicate preview."""
    calc = CalculatorView()
    # Initial prompt case loads 1 row
    assert calc.imp_table.rowCount() == 1

    amt_widget = calc.imp_table.cellWidget(0, 3)
    assert isinstance(amt_widget, IndianCurrencyInput)
    assert amt_widget.show_preview is False
    assert amt_widget.preview_label is None
    assert amt_widget.value() == 1000000.0
    assert amt_widget.line_edit.text() == "10,00,000"


def test_add_and_delete_improvement_rows(qapp):
    """Verifies that adding and deleting rows works smoothly without crashing or errors."""
    calc = CalculatorView()
    assert calc.imp_table.rowCount() == 1

    # Add a second row via button click
    calc.btn_add_imp.click()
    qapp.processEvents()
    assert calc.imp_table.rowCount() == 2

    # Verify action buttons
    action_w1 = calc.imp_table.cellWidget(1, 4)
    btn_del1 = action_w1.findChild(QPushButton)
    assert btn_del1 is not None
    assert btn_del1.text() == "Delete"

    # Click delete on row 1
    btn_del1.click()
    qapp.processEvents()
    assert calc.imp_table.rowCount() == 1

    # Click delete on remaining row 0
    action_w0 = calc.imp_table.cellWidget(0, 4)
    btn_del0 = action_w0.findChild(QPushButton)
    assert btn_del0 is not None
    assert btn_del0.text() == "Delete"

    btn_del0.click()
    qapp.processEvents()
    assert calc.imp_table.rowCount() == 0

    # Summary labels should reflect 0
    assert "₹0" in calc.imp_total_actual_lbl.text()
    assert "₹0" in calc.imp_total_indexed_lbl.text()


def test_improvement_amount_editing(qapp):
    """Verifies editing amount updates totals and form data."""
    calc = CalculatorView()
    amt_widget = calc.imp_table.cellWidget(0, 3)

    # Change amount to 25,00,000
    amt_widget.setValue(2500000.0)
    assert amt_widget.value() == 2500000.0
    assert amt_widget.line_edit.text() == "25,00,000"

    form_data = calc.get_form_data()
    assert len(form_data["improvements"]) == 1
    assert form_data["improvements"][0]["amount"] == 2500000.0
