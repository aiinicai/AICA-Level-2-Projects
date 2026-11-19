import app  # noqa: F401  (install pure-Python SQLAlchemy hook before anything imports sqlalchemy)
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])
