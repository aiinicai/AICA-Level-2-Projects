"""Phase 4 exit test — Slowly Changing Dimension Type 2 (§5.1, §16).

The rule under test: **never UPDATE a current profile's business fields.**
A change closes the current row and opens a new one, so a document finalised
last year keeps printing the address it was signed with.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import CompanyType
from app.models.issuance import AuditLog
from app.models.masters import ClientProfile
from app.services.client import (
    ProfileError,
    change_profile,
    current_profile,
    diff_profile,
    profile_as_on,
)

MOVE_DATE = date(2025, 9, 1)
OLD_ADDRESS = "401, Nariman Point, Mumbai 400021"
NEW_ADDRESS = "12th Floor, Cyber City, Gurugram 122002"


class TestVersioning:
    def test_a_change_opens_a_new_version(self, db: Session, client_id: int) -> None:
        before = db.scalar(
            select(func.count())
            .select_from(ClientProfile)
            .where(ClientProfile.client_id == client_id)
        )
        change_profile(
            db,
            client_id,
            {"registered_addr": NEW_ADDRESS},
            change_date=MOVE_DATE,
            changed_by="manager@firm.local",
            reason="Registered office shifted",
        )
        after = db.scalar(
            select(func.count())
            .select_from(ClientProfile)
            .where(ClientProfile.client_id == client_id)
        )
        assert after == (before or 0) + 1

    def test_the_old_row_keeps_its_values(self, db: Session, client_id: int) -> None:
        original = current_profile(db, client_id)
        original_id = original.profile_id

        change_profile(
            db,
            client_id,
            {"registered_addr": NEW_ADDRESS},
            change_date=MOVE_DATE,
            changed_by="manager@firm.local",
            reason="Registered office shifted",
        )
        db.expire_all()

        historical = db.get(ClientProfile, original_id)
        assert historical is not None
        # This is the whole point: the prior version is untouched.
        assert historical.registered_addr == OLD_ADDRESS
        assert historical.is_current is False
        assert historical.valid_to == date(2025, 8, 31)

    def test_the_new_row_is_current_and_carries_unchanged_fields(
        self, db: Session, client_id: int
    ) -> None:
        change_profile(
            db,
            client_id,
            {"registered_addr": NEW_ADDRESS},
            change_date=MOVE_DATE,
            changed_by="manager@firm.local",
            reason="Registered office shifted",
        )
        latest = current_profile(db, client_id)
        assert latest.registered_addr == NEW_ADDRESS
        assert latest.is_current is True
        assert latest.valid_from == MOVE_DATE
        assert latest.valid_to is None
        # Fields not named in the change must survive the copy.
        assert latest.company_name == "ABC Private Limited"
        assert latest.company_type is CompanyType.PVT

    def test_only_one_current_row_survives(self, db: Session, client_id: int) -> None:
        change_profile(
            db,
            client_id,
            {"registered_addr": NEW_ADDRESS},
            change_date=MOVE_DATE,
            changed_by="m@firm.local",
            reason="Moved",
        )
        current_count = db.scalar(
            select(func.count())
            .select_from(ClientProfile)
            .where(ClientProfile.client_id == client_id, ClientProfile.is_current.is_(True))
        )
        assert current_count == 1

    def test_database_refuses_a_second_current_row(self, db: Session, client_id: int) -> None:
        """The partial unique index is the backstop for a service-layer bug."""
        existing = current_profile(db, client_id)
        db.add(
            ClientProfile(
                client_id=client_id,
                valid_from=date(2026, 1, 1),
                is_current=True,
                company_name=existing.company_name,
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


class TestPointInTimeReads:
    def test_a_prior_year_read_returns_the_old_address(self, db: Session, client_id: int) -> None:
        # §18.6 — reprinting a prior-year document must reproduce it. If this
        # fails, changing master data silently rewrites signed documents.
        change_profile(
            db,
            client_id,
            {"registered_addr": NEW_ADDRESS},
            change_date=MOVE_DATE,
            changed_by="m@firm.local",
            reason="Moved",
        )
        as_at_fy2425 = profile_as_on(db, client_id, date(2025, 3, 31))
        assert as_at_fy2425.registered_addr == OLD_ADDRESS

    def test_a_current_year_read_returns_the_new_address(self, db: Session, client_id: int) -> None:
        change_profile(
            db,
            client_id,
            {"registered_addr": NEW_ADDRESS},
            change_date=MOVE_DATE,
            changed_by="m@firm.local",
            reason="Moved",
        )
        assert profile_as_on(db, client_id, date(2026, 3, 31)).registered_addr == NEW_ADDRESS

    def test_a_date_before_any_profile_raises(self, db: Session, client_id: int) -> None:
        with pytest.raises(ProfileError):
            profile_as_on(db, client_id, date(1999, 1, 1))


class TestGuards:
    def test_a_no_op_change_creates_no_version(self, db: Session, client_id: int) -> None:
        before = current_profile(db, client_id).profile_id
        result = change_profile(
            db,
            client_id,
            {"registered_addr": OLD_ADDRESS},
            change_date=MOVE_DATE,
            changed_by="m@firm.local",
            reason="No actual change",
        )
        assert result.profile_id == before

    def test_a_reason_is_required(self, db: Session, client_id: int) -> None:
        with pytest.raises(ProfileError, match="reason is required"):
            change_profile(
                db,
                client_id,
                {"registered_addr": NEW_ADDRESS},
                change_date=MOVE_DATE,
                changed_by="m@firm.local",
                reason="   ",
            )

    def test_backdating_before_the_current_version_is_refused(
        self, db: Session, client_id: int
    ) -> None:
        # Otherwise two versions would claim the same day and a point-in-time
        # read becomes ambiguous.
        with pytest.raises(ProfileError, match="must fall after"):
            change_profile(
                db,
                client_id,
                {"registered_addr": NEW_ADDRESS},
                change_date=date(2009, 1, 1),
                changed_by="m@firm.local",
                reason="Backdated",
            )

    def test_an_unknown_field_is_refused(self, db: Session, client_id: int) -> None:
        with pytest.raises(ProfileError, match="not a versioned profile field"):
            diff_profile(current_profile(db, client_id), {"not_a_column": 1})

    def test_versioning_fields_are_not_business_fields(self, db: Session, client_id: int) -> None:
        with pytest.raises(ProfileError, match="not a versioned profile field"):
            diff_profile(current_profile(db, client_id), {"is_current": False})


class TestAuditTrail:
    def test_a_version_is_logged_with_before_and_after(self, db: Session, client_id: int) -> None:
        change_profile(
            db,
            client_id,
            {"registered_addr": NEW_ADDRESS},
            change_date=MOVE_DATE,
            changed_by="manager@firm.local",
            reason="Registered office shifted",
        )
        log = db.scalar(
            select(AuditLog)
            .where(AuditLog.entity == "client_profile", AuditLog.action == "version")
            .order_by(AuditLog.log_id.desc())
        )
        assert log is not None
        assert log.actor == "manager@firm.local"
        assert log.reason == "Registered office shifted"
        assert OLD_ADDRESS in log.before_json
        assert NEW_ADDRESS in log.after_json


class TestAtomicity:
    """Versioning closes one row and inserts another. Both, or neither.

    pysqlite does not emit BEGIN for DML on its own, so without the fix in
    `app.db._fix_pysqlite_transactions` a failure between the two steps would
    leave the old profile closed and no current profile at all — a client
    with no master data.
    """

    def test_a_failure_midway_leaves_the_original_intact(
        self, db: Session, client_id: int, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import app.services.client as client_service

        original = current_profile(db, client_id)
        original_id = original.profile_id
        original_valid_from = original.valid_from

        def _explode(*_args: object, **_kwargs: object) -> ClientProfile:
            raise RuntimeError("simulated failure after the old row was closed")

        monkeypatch.setattr(client_service, "ClientProfile", _explode)

        with pytest.raises(RuntimeError, match="simulated failure"):
            change_profile(
                db,
                client_id,
                {"registered_addr": NEW_ADDRESS},
                change_date=MOVE_DATE,
                changed_by="m@firm.local",
                reason="Will fail",
            )

        db.rollback()
        # Restore the real model before reading back, or the read itself
        # goes through the exploding stand-in.
        monkeypatch.undo()

        survivor = current_profile(db, client_id)
        assert survivor.profile_id == original_id
        assert survivor.is_current is True
        assert survivor.valid_to is None
        assert survivor.valid_from == original_valid_from
        assert survivor.registered_addr == OLD_ADDRESS
