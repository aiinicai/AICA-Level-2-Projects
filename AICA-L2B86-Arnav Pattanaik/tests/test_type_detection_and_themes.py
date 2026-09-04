import sys
import pandas as pd
from PyQt6.QtWidgets import QApplication

from core.query_engine import detect_column_type, get_operators_for_type, evaluate_filters, FilterRow
from gui.styles import THEMES, get_theme_stylesheet
from gui.excel_filter_dropdown import ExcelFilterDropdown


def test_type_detection_and_date_operators():
    df = pd.DataFrame({
        "SUPPLY_RELEASE_DATE": ["2026-01-15", "2026-02-10", "2026-03-20", "2026-04-05"],
        "CONSUMER_STATUS": ["BILL STOPTED", "DISCONNECTED", "BILL STOPTED", "REGULAR"],
        "ENERGY_CHG": [500.0, 1000.0, 1500.0, 2000.0]
    })

    # Test Type Detection
    t_date = detect_column_type(df["SUPPLY_RELEASE_DATE"], "SUPPLY_RELEASE_DATE")
    assert t_date == "date"

    t_num = detect_column_type(df["ENERGY_CHG"], "ENERGY_CHG")
    assert t_num == "numeric"

    t_txt = detect_column_type(df["CONSUMER_STATUS"], "CONSUMER_STATUS")
    assert t_txt == "text"

    # Test Date Operators List
    date_ops = get_operators_for_type("date")
    op_keys = [k for k, _ in date_ops]
    assert "date_equals" in op_keys
    assert "date_before" in op_keys
    assert "date_after" in op_keys

    # Test Date Filtering: before 2026-03-01
    f_date = FilterRow(field="SUPPLY_RELEASE_DATE", operator="date_before", value="2026-03-01")
    res_date = evaluate_filters(df, [f_date])
    assert len(res_date) == 2
    assert set(res_date["SUPPLY_RELEASE_DATE"]) == {"2026-01-15", "2026-02-10"}

    # Test Multi-Select Filter (IN operator)
    f_multi = FilterRow(field="CONSUMER_STATUS", operator="in", value="BILL STOPTED, DISCONNECTED")
    res_multi = evaluate_filters(df, [f_multi])
    assert len(res_multi) == 3

    print("TYPE DETECTION AND DATE OPERATOR TESTS PASSED SUCCESSFULLY!")


def test_excel_filter_dropdown():
    app = QApplication.instance() or QApplication(sys.argv)

    dropdown = ExcelFilterDropdown()
    items = ["BILL STOPTED", "DISCONNECTED", "REGULAR", "FIRST BILL"]
    dropdown.set_items(items)

    assert "(All 4 values)" in dropdown.text()
    assert dropdown.get_selected_text() == ""

    dropdown.set_selected(["BILL STOPTED", "DISCONNECTED"])
    assert "2 values selected" in dropdown.text()
    assert dropdown.get_selected_text() == "BILL STOPTED, DISCONNECTED"

    print("EXCEL FILTER DROPDOWN TESTS PASSED SUCCESSFULLY!")


def test_theme_generator():
    for theme_name in ["Dark", "Light", "Navy Blue", "Sundowner"]:
        qss = get_theme_stylesheet(theme_name)
        assert len(qss) > 500
        assert THEMES[theme_name]["bg_main"] in qss

    print("THEME GENERATOR TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_type_detection_and_date_operators()
    test_excel_filter_dropdown()
    test_theme_generator()
