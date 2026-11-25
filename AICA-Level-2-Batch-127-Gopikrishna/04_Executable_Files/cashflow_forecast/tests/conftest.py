import pytest
from sqlalchemy.orm import Session

from app import db as dbmod
from app.core import config


@pytest.fixture(autouse=True)
def isolated_instance(tmp_path, monkeypatch):
    """Every test gets its own instance/ folder and database, so tests never touch real data."""
    monkeypatch.setenv("CFF_INSTANCE_DIR", str(tmp_path / "instance"))
    monkeypatch.setenv("CFF_AUTO_BACKUP", "false")          # no background backup thread in tests
    config.get_settings.cache_clear()
    config.get_business_defaults.cache_clear()
    dbmod.reset_engine()
    yield tmp_path / "instance"
    dbmod.reset_engine()
    config.get_settings.cache_clear()
    config.get_business_defaults.cache_clear()


@pytest.fixture
def engine():
    from app.services.init_db import init_db

    eng = dbmod.get_engine()
    init_db(eng)
    return eng


@pytest.fixture
def db(engine):
    with Session(engine) as s:
        yield s
