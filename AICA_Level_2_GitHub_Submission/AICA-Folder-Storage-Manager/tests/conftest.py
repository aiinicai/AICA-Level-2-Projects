import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))


@pytest.fixture
def env(tmp_path, monkeypatch):
    data = tmp_path / "appdata"
    monkeypatch.setenv("AICA_FSM_DATA", str(data))
    from aica_fsm.store import Catalog
    cat = Catalog()
    yield tmp_path, cat
    cat.close()
