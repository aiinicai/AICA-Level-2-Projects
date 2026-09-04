import sys
import pandas as pd
from PyQt6.QtWidgets import QApplication

from core.energy_charge_calculator import run_energy_charge_audit, calculate_row_expected_ec
from gui.app_state import AppState
from gui.screen_energy_audit import ScreenEnergyAudit


def test_energy_charge_formulas():
    # 1. Domestic slab testing
    # 0 - 50 @ 2.90
    assert calculate_row_expected_ec("DOMESTIC", 50) == 50 * 2.90
    # 50 @ 2.90 + 50 @ 4.70 = 145 + 235 = 380
    assert calculate_row_expected_ec("DOMESTIC", 100) == 50 * 2.90 + 50 * 4.70
    # 420 kWh: 50*2.90 (145) + 150*4.70 (705) + 200*5.70 (1140) + 20*6.10 (122) = 2112
    assert calculate_row_expected_ec("DOMESTIC", 420) == 2112.0

    # 2. General Purpose slab testing
    # 0 - 100 @ 5.90
    assert calculate_row_expected_ec("GENERAL PURPOSE < 110 KVA", 100) == 100 * 5.90
    # 100 @ 5.90 + 100 @ 7.00 = 590 + 700 = 1290
    assert calculate_row_expected_ec("GENERAL PURPOSE < 110 KVA", 200) == 1290.0

    # 3. Flat rate testing
    assert calculate_row_expected_ec("IRRIGATION PUMPING AND AGRICULTURE", 100) == 150.0
    assert calculate_row_expected_ec("PUBLIC LIGHT", 100) == 620.0

    print("ENERGY CHARGE FORMULA TESTS PASSED SUCCESSFULLY!")


def test_discrepancy_audit_engine():
    df = pd.DataFrame({
        "SCNO": ["SC1", "SC2", "SC3", "SC4"],
        "CAT_CODE": ["DOMESTIC", "DOMESTIC", "GENERAL PURPOSE < 110 KVA", "PUBLIC LIGHT"],
        "KWH_UNITS": [420.0, 100.0, 200.0, 100.0],
        "ENERGY_CHG": [2112.00, 100.00, 1290.00, 600.00]  # SC1 matches, SC2 under-billed, SC3 matches, SC4 under-billed
    })

    discrepancy_df, metrics = run_energy_charge_audit(df, target_category="All", tolerance=1.0)

    assert metrics["total_audited"] == 4
    assert metrics["total_mismatched"] == 2
    assert len(discrepancy_df) == 2
    assert set(discrepancy_df["SCNO"]) == {"SC2", "SC4"}

    # Test filtering by specific category
    discrepancy_dom, metrics_dom = run_energy_charge_audit(df, target_category="DOMESTIC", tolerance=1.0)
    assert metrics_dom["total_audited"] == 2
    assert metrics_dom["total_mismatched"] == 1
    assert list(discrepancy_dom["SCNO"]) == ["SC2"]

    print("DISCREPANCY AUDIT ENGINE TESTS PASSED SUCCESSFULLY!")


def test_screen_energy_audit():
    app = QApplication.instance() or QApplication(sys.argv)

    state = AppState()
    df = pd.DataFrame({
        "SCNO": ["SC1", "SC2"],
        "CAT_CODE": ["DOMESTIC", "DOMESTIC"],
        "KWH_UNITS": [100.0, 100.0],
        "ENERGY_CHG": [380.00, 100.00]
    })
    state.compiled_df = df
    state.is_compiled = True

    screen = ScreenEnergyAudit(state)
    screen.refresh()

    assert screen._discrepancy_df is not None
    assert len(screen._discrepancy_df) == 1
    assert screen._discrepancy_df.iloc[0]["SCNO"] == "SC2"

    print("SCREEN ENERGY AUDIT UI TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_energy_charge_formulas()
    test_discrepancy_audit_engine()
    test_screen_energy_audit()
