import sys
import pandas as pd
from PyQt6.QtWidgets import QApplication

from gui.app_state import AppState
from core.session_manager import save_session, load_session, clear_session, get_session_dir

def test_session_persistence():
    app = QApplication.instance() or QApplication(sys.argv)

    # 1. Clean previous test session
    temp_state = AppState()
    clear_session(temp_state)
    
    session_dir = get_session_dir()
    df_path = session_dir / "compiled_data.pkl"
    meta_path = session_dir / "metadata.json"
    assert not df_path.exists()
    assert not meta_path.exists()

    # 2. Setup mock compiled AppState
    state = AppState()
    df = pd.DataFrame({
        "SC_NO": ["SC1", "SC2", "SC3"],
        "CONSUMER_STATUS": ["BILL STOPTED", "REGULAR", "DISCONNECTED"],
        "ENERGY_CHG": [100.5, 200.0, 300.75]
    })
    state.compiled_df = df
    state.is_compiled = True
    state.total_rows_read = 3

    # 3. Test saving session
    success = save_session(state)
    assert success
    assert df_path.exists()
    assert meta_path.exists()

    # 4. Test loading session into new AppState
    new_state = AppState()
    assert not new_state.is_compiled
    assert new_state.compiled_df is None

    loaded = load_session(new_state)
    assert loaded
    assert new_state.is_compiled
    assert new_state.compiled_df is not None
    assert len(new_state.compiled_df) == 3
    assert list(new_state.compiled_df["SC_NO"]) == ["SC1", "SC2", "SC3"]

    # 5. Test clearing session
    clear_session(new_state)
    assert not df_path.exists()
    assert not meta_path.exists()
    assert not new_state.is_compiled
    assert new_state.compiled_df is None

    print("SESSION PERSISTENCE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_session_persistence()
