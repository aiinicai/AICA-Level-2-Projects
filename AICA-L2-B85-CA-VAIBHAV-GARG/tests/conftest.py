"""Pytest fixtures and test utilities."""
import os
from pathlib import Path
import pytest

from src.database.repository import Repository

SAMPLE_DIRS = [
    Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "Sample Data",
    Path.cwd(),
]


def _find_sample_file(filenames):
    for d in SAMPLE_DIRS:
        for fn in filenames:
            p = d / fn
            if p.exists():
                return str(p)
    return None


@pytest.fixture
def temp_db_repo(tmp_path):
    """Provide a fresh temporary SQLite repository."""
    db_file = tmp_path / "test_ratio_analyser.db"
    repo = Repository(db_file)
    return repo


@pytest.fixture
def sample_cy_path():
    """Return path to Sample_CY.xlsx from Desktop Sample Data folder."""
    return _find_sample_file(["Sample_CY.xlsx", "SampleCY.xlsx"])


@pytest.fixture
def sample_py_path():
    """Return path to Sample_PY-1.xlsx from Desktop Sample Data folder."""
    return _find_sample_file(["Sample_PY-1.xlsx", "SamplePY-1.xlsx"])


@pytest.fixture
def sample_cy_copy_path():
    """Return path to Sample_CY - Copy.xlsx from Desktop Sample Data folder."""
    return _find_sample_file(["SampleCYCopy.xlsx", "Sample_CY - Copy.xlsx", "Sample_CY_-_Copy.xlsx"])


@pytest.fixture
def sample_py_copy_path():
    """Return path to Sample_PY-1 - Copy.xlsx from Desktop Sample Data folder."""
    return _find_sample_file(["SamplePY-1Copy.xlsx", "Sample_PY-1 - Copy.xlsx", "Sample_PY-1_-_Copy.xlsx"])
