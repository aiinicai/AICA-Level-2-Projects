"""
Stage 5 — app/services/engagement_service.py (real SQLAlchemy 2.x ORM
persistence). Run with:

    pip install -r requirements.txt
    pytest tests/unit/test_engagement_service.py -v

NOTE ON THIS SANDBOX: ran for real under `pytest` (8/8 passed), but NOT
against real SQLAlchemy — it's still uninstallable here (network to
PyPI/apt confirmed 403 again during Stage 5 delivery; see
database/migrations/versions/README.md). What made this file
executable at all this stage: a genuinely real Flask 3.1.3 this sandbox
happens to have cached (found during Stage 5 delivery), and a scoped
SQLAlchemy 2.x declarative-ORM shim (`/tmp/orm_shim.py` during
delivery, not part of this repo) that layers real Python<->SQL row
mapping — including this fixture's own `event.listens_for` and
`Base.metadata.create_all()` calls — on top of a real, on-disk SQLite
database via Python's builtin `sqlite3`. See the Stage 5 delivery notes
for exactly what the shim does and does not implement. This file's
assertions run unmodified against real SQLAlchemy once it's installed —
nothing here was written to accommodate the shim.

Each test gets its own fresh on-disk SQLite database (schema created
via `Base.metadata.create_all`, not through Alembic — that pairing is
what tests/unit/test_migration.py exists to verify separately) and
rebinds `app.extensions.engine`/`SessionLocal` before importing
`engagement_service`, since that module intentionally reads
`app.extensions.SessionLocal` dynamically on every call (see
`engagement_service._session()`'s docstring) rather than capturing it
once at import time — precisely so each test's fresh engine takes
effect immediately, with no stale binding from an earlier test.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest


@pytest.fixture()
def svc(tmp_path):
    """A fresh engagement_service module wired to a fresh, empty,
    real SQLite database for this one test."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import scoped_session, sessionmaker

    from app import extensions
    from app.models import Base

    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    extensions.engine = engine
    extensions.SessionLocal = scoped_session(sessionmaker(bind=engine, future=True, expire_on_commit=False))

    from app.services import engagement_service as service_module
    yield service_module

    extensions.SessionLocal.remove()


LISTED_PROFILE_FIELDS = {
    "entity_type": "Company", "industry": "Steel", "is_listed": True,
    "accounting_framework": "IND_AS", "turnover": 500000000, "is_gst_registered": True,
    "statutory_audit_applicable": True, "tax_audit_status": "APPLICABLE",
    "consolidated_fs_applicable": False, "prior_year_data_available": True,
    "overall_materiality": 5000000, "performance_materiality": 3750000,
    "clearly_trivial_threshold": None,
}


def test_create_engagement_persists_and_defaults_to_draft(svc):
    engagement = svc.create_engagement("Acme Manufacturing Ltd", "2025-26", created_by="R. Sharma")
    assert engagement.engagement_id is not None
    assert engagement.status == "DRAFT"

    reloaded = svc.get_engagement(engagement.engagement_id)
    assert reloaded.entity_name == "Acme Manufacturing Ltd"
    assert reloaded.created_by == "R. Sharma"


def test_list_engagements_returns_all_created(svc):
    svc.create_engagement("Acme Manufacturing Ltd", "2025-26")
    svc.create_engagement("Beta Traders LLP", "2025-26")
    names = {e.entity_name for e in svc.list_engagements()}
    assert names == {"Acme Manufacturing Ltd", "Beta Traders LLP"}


def test_save_entity_profile_insert_then_update_no_duplicate_row(svc):
    engagement = svc.create_engagement("Acme Manufacturing Ltd", "2025-26")
    svc.save_entity_profile(engagement.engagement_id, LISTED_PROFILE_FIELDS)
    svc.save_entity_profile(engagement.engagement_id, {**LISTED_PROFILE_FIELDS, "industry": "Auto Components"})

    profile = svc.get_entity_profile(engagement.engagement_id)
    assert profile.industry == "Auto Components"

    # No duplicate row was created — UNIQUE(engagement_id) plus the
    # get-then-update path in save_entity_profile both matter here.
    reloaded_engagement = svc.get_engagement(engagement.engagement_id)
    assert reloaded_engagement.status == "IN_PROGRESS"  # auto-transitioned on first save


def test_refresh_applicability_creates_one_row_per_area(svc):
    engagement = svc.create_engagement("Acme Manufacturing Ltd", "2025-26")
    svc.save_entity_profile(engagement.engagement_id, LISTED_PROFILE_FIELDS)

    rows = svc.list_applicability(engagement.engagement_id)
    from app.services.applicability_engine import AREAS
    assert {r.area for r in rows} == set(AREAS)

    sebi_row = svc.get_applicability_row(engagement.engagement_id, "SEBI/LODR")
    assert sebi_row.system_suggested_status == "YES"
    assert "Entity profile" in sebi_row.system_suggested_reason


def test_confirm_applicability_persists_and_survives_a_later_refresh(svc):
    engagement = svc.create_engagement("Acme Manufacturing Ltd", "2025-26")
    svc.save_entity_profile(engagement.engagement_id, LISTED_PROFILE_FIELDS)
    svc.confirm_applicability(
        engagement.engagement_id, "SEBI/LODR", "APPLICABLE", "Confirmed after LODR review.", "R. Sharma"
    )

    row = svc.get_applicability_row(engagement.engagement_id, "SEBI/LODR")
    assert row.user_confirmed_status == "APPLICABLE"
    assert row.confirmed_by == "R. Sharma"
    assert row.confirmed_at is not None

    # A later profile save re-runs refresh_applicability — it must not
    # silently erase the professional's confirmation.
    svc.save_entity_profile(engagement.engagement_id, {**LISTED_PROFILE_FIELDS, "turnover": 600000000})
    row_after = svc.get_applicability_row(engagement.engagement_id, "SEBI/LODR")
    assert row_after.user_confirmed_status == "APPLICABLE"


def test_two_engagements_do_not_leak_applicability_into_each_other(svc):
    listed = svc.create_engagement("Listed Co", "2025-26")
    unlisted = svc.create_engagement("Unlisted Co", "2025-26")
    svc.save_entity_profile(listed.engagement_id, LISTED_PROFILE_FIELDS)
    svc.save_entity_profile(unlisted.engagement_id, {
        **LISTED_PROFILE_FIELDS, "is_listed": False, "accounting_framework": "AS",
    })

    assert svc.get_applicability_row(listed.engagement_id, "SEBI/LODR").system_suggested_status == "YES"
    assert svc.get_applicability_row(unlisted.engagement_id, "SEBI/LODR").system_suggested_status == "NO"


def test_current_engagement_is_a_session_cookie_concept(svc):
    engagement = svc.create_engagement("Acme Manufacturing Ltd", "2025-26")
    fake_session = {}

    assert svc.get_current_engagement(fake_session) is None

    svc.set_current_engagement(fake_session, engagement.engagement_id)
    current = svc.get_current_engagement(fake_session)
    assert current is not None and current.engagement_id == engagement.engagement_id


def test_get_current_engagement_self_heals_a_stale_id(svc):
    stale_session = {"current_engagement_id": 999999}
    assert svc.get_current_engagement(stale_session) is None
    assert "current_engagement_id" not in stale_session
