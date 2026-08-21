import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import database


@pytest.fixture
def db_conn(tmp_path):
    db_path = str(tmp_path / "test_assetdeppro.db")
    database.initialize_database(db_path)
    conn = database.get_connection(db_path)
    yield conn
    conn.close()