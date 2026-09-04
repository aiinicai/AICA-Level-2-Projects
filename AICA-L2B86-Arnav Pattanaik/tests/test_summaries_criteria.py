import sys
import pandas as pd
from PyQt6.QtWidgets import QApplication

from gui.app_state import AppState
from gui.screen_summaries import ScreenSummaries, SummaryFilterRowWidget

def test_screen_summaries_selection_criteria():
    app = QApplication.instance() or QApplication(sys.argv)
    
    state = AppState()
    df = pd.DataFrame({
        "CONSUMER_STATUS": ["BILL STOPTED", "DISCONNECTED", "BILL STOPTED", "REGULAR", "REGULAR"],
        "SUBDIVISION": ["SDO BASTA", "SDO JALESWAR", "SDO JAMSULI", "SDO TIHIDI", "SDO BASTA"],
        "ENERGY_CHG": [916.59, 14807.30, 100.0, 5000.0, 6000.0]
    })
    state.compiled_df = df
    state.is_compiled = True
    
    screen = ScreenSummaries(state)
    screen.refresh()
    
    # Verify initial unfiltered state
    assert screen._filtered_df is not None
    assert len(screen._filtered_df) == 5
    assert "Active Selection: All 5 rows" in screen.criteria_status_label.text()
    
    # Add a criteria row: CONSUMER_STATUS = BILL STOPTED
    screen._add_criteria_row()
    assert len(screen.criteria_widgets) == 1
    
    widget = screen.criteria_widgets[0]
    widget.field_combo.setCurrentText("CONSUMER_STATUS")
    widget.op_combo.setCurrentText("equals")
    widget.value_edit.setText("BILL STOPTED")
    
    # Trigger filtering
    screen._apply_criteria()
    
    assert len(screen._filtered_df) == 2
    assert set(screen._filtered_df["CONSUMER_STATUS"]) == {"BILL STOPTED"}
    assert "Active Selection: 2 of 5 rows" in screen.criteria_status_label.text()
    
    # Add a second criteria row using + Add Criteria button: SUBDIVISION = SDO BASTA
    screen._add_criteria_row()
    assert len(screen.criteria_widgets) == 2
    
    widget2 = screen.criteria_widgets[1]
    widget2.field_combo.setCurrentText("SUBDIVISION")
    widget2.op_combo.setCurrentText("equals")
    widget2.value_edit.setText("SDO BASTA")
    
    screen._apply_criteria()
    assert len(screen._filtered_df) == 1
    assert screen._filtered_df.iloc[0]["SUBDIVISION"] == "SDO BASTA"
    
    # Clear criteria
    screen._clear_criteria()
    assert len(screen.criteria_widgets) == 0
    assert len(screen._filtered_df) == 5
    
    print("ALL SUMMARIES SELECTION CRITERIA TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_screen_summaries_selection_criteria()
