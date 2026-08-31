from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The production repository: 146 clauses, 140 of them unauthored skeletons.
PRODUCTION_CONTENT = PROJECT_ROOT / "content"

# A small AUTHORED repository. Machinery tests run here, so that "does the
# export pipeline work" and "is the real repository ready to sign" stay
# separate questions — the second answer is currently no, by design.
CONTENT_DIR = PROJECT_ROOT / "tests" / "fixtures" / "content"

# MUST be set before anything under `app` is imported: `app.db` builds its
# engine at module scope, which caches Settings. Import order is load-bearing
# here, so these two lines stay above the app imports.
os.environ["AUDITCRAFT_CONTENT_DIR"] = str(CONTENT_DIR)
# And the database, for the same reason: `app.db` binds `SessionLocal` to
# whatever this resolves to at import. Every test gets its own engine from the
# `db_engine` fixture, but anything reaching for `SessionLocal` directly -- the
# application's own startup does, to sync the field catalogue -- would otherwise
# write to the developer's real `data/auditcraft.db` on every test run.
# Per process, not a fixed name: two runs sharing one file leave each other's
# rows behind, and a suite that passes or fails depending on what ran before it
# is worse than one that fails.
os.environ["AUDITCRAFT_DATABASE_URL"] = (
    f"sqlite:///{Path(tempfile.gettempdir()) / f'auditcraft-tests-{os.getpid()}.db'}"
)
sys.path.insert(0, str(PROJECT_ROOT))

from app.clauses.loader import load_clause_set  # noqa: E402
from app.clauses.model import ClauseSet  # noqa: E402
from app.db import Base, _fix_pysqlite_transactions  # noqa: E402
from app.models.masters import Client  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT))

FY_2025_26 = date(2026, 3, 31)
FY_2022_23 = date(2023, 3, 31)


@pytest.fixture(scope="session")
def clause_set() -> ClauseSet:
    """The authored fixture repository."""
    return load_clause_set(CONTENT_DIR)


@pytest.fixture(scope="session")
def production_clause_set() -> ClauseSet:
    """The real `content/` repository, skeletons and all."""
    return load_clause_set(PRODUCTION_CONTENT)


@pytest.fixture
def render_context() -> dict[str, object]:
    """A minimal context. Real contexts are built once per render (§3.3)."""
    return {
        "company_name": "ABC Private Limited",
        "fy_end_long": "31 March 2026",
        "framework_ref": "Companies (Indian Accounting Standards) Rules, 2015",
        "value": None,
    }


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_engine(tmp_path_factory: pytest.TempPathFactory) -> Engine:
    """One seeded database per test session.

    Seeding is done once because Argon2 hashing is deliberately slow — four
    users per test would dominate the run time.
    """
    from scripts.seed import (
        seed_client,
        seed_engagements,
        seed_firm,
        seed_responses,
        sync_field_catalog,
    )

    path = tmp_path_factory.mktemp("db") / "test.db"
    engine = create_engine(
        f"sqlite:///{path}", future=True, connect_args={"check_same_thread": False}
    )
    # Same transaction fix the application engine gets, or the per-test
    # rollback below silently does nothing and tests leak into each other.
    _fix_pysqlite_transactions(engine)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        firm = seed_firm(session)
        session.flush()
        client = seed_client(session, firm)
        session.flush()
        seed_engagements(session, client)
        session.flush()
        sync_field_catalog(session, load_clause_set(CONTENT_DIR))
        session.flush()
        seed_responses(session, client)
        session.commit()

    return engine


@pytest.fixture
def db(db_engine: Engine) -> Iterator[Session]:
    """A session whose writes are rolled back after each test.

    The outer transaction is never committed, so tests see the seeded data
    and nothing each other wrote.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def app_client(db: Session) -> Iterator[TestClient]:
    """A TestClient whose routes share the rollback-isolated `db` session.

    Route handlers call `session.commit()`. Bound to a savepoint, that
    releases the savepoint rather than the outer transaction, so the test's
    writes still disappear at teardown and cannot leak into another test's
    view of the seeded data.
    """
    from app.db import get_session
    from app.main import app

    def _override() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client_id(db: Session) -> int:
    client = db.scalar(select(Client).where(Client.client_code == "ABC001"))
    assert client is not None, "seed data missing"
    return client.client_id
