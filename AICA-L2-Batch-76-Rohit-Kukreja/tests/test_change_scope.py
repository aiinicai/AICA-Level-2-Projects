"""Master-data change scope. Build Prompt v2 §8.3.

The rule that matters: **never silently alter a finalised engagement.** No
scope option overrides it, which is what keeps a signed prior-year document
reproducible (§18.6).

Seeded engagements for ABC Private Limited:
    2024-25  finalised and locked
    2025-26  open, data collection
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engagement import Engagement
from app.services.client import ChangeScope, change_profile, current_profile

NEW_ADDRESS = "12th Floor, Cyber City, Gurugram 122002"
DURING_FY_2025_26 = date(2025, 9, 1)


def _engagement(db: Session, client_id: int, fy_code: str) -> Engagement:
    engagement = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == fy_code)
    )
    assert engagement is not None, f"seed missing engagement {fy_code}"
    return engagement


def _change(db: Session, client_id: int, scope: ChangeScope) -> int:
    profile = change_profile(
        db,
        client_id,
        {"registered_addr": NEW_ADDRESS},
        change_date=DURING_FY_2025_26,
        changed_by="manager@firm.local",
        reason="Registered office shifted",
        scope=scope,
    )
    return profile.profile_id


class TestFinalisedEngagementsAreNeverTouched:
    @pytest.mark.parametrize("scope", list(ChangeScope))
    def test_under_every_scope(self, db: Session, client_id: int, scope: ChangeScope) -> None:
        finalised = _engagement(db, client_id, "2024-25")
        pinned = finalised.profile_id

        new_profile_id = _change(db, client_id, scope)
        db.expire_all()

        assert _engagement(db, client_id, "2024-25").profile_id == pinned
        assert _engagement(db, client_id, "2024-25").profile_id != new_profile_id

    def test_the_locked_engagement_still_reads_the_old_address(
        self, db: Session, client_id: int
    ) -> None:
        _change(db, client_id, ChangeScope.CURRENT_AND_FUTURE)
        db.expire_all()

        finalised = _engagement(db, client_id, "2024-25")
        pinned_profile = db.get(type(current_profile(db, client_id)), finalised.profile_id)
        assert pinned_profile is not None
        assert pinned_profile.registered_addr != NEW_ADDRESS


class TestScopes:
    def test_master_only_repoints_nothing(self, db: Session, client_id: int) -> None:
        before = _engagement(db, client_id, "2025-26").profile_id
        _change(db, client_id, ChangeScope.MASTER_ONLY)
        db.expire_all()
        assert _engagement(db, client_id, "2025-26").profile_id == before

    def test_current_fy_repoints_the_open_year(self, db: Session, client_id: int) -> None:
        new_profile_id = _change(db, client_id, ChangeScope.CURRENT_FY)
        db.expire_all()
        assert _engagement(db, client_id, "2025-26").profile_id == new_profile_id

    def test_current_and_future_repoints_the_open_year(self, db: Session, client_id: int) -> None:
        new_profile_id = _change(db, client_id, ChangeScope.CURRENT_AND_FUTURE)
        db.expire_all()
        assert _engagement(db, client_id, "2025-26").profile_id == new_profile_id

    def test_current_fy_skips_a_year_the_date_does_not_fall_in(
        self, db: Session, client_id: int
    ) -> None:
        # A change dated in FY 2026-27 is not "the current financial year"
        # for the FY 2025-26 engagement.
        before = _engagement(db, client_id, "2025-26").profile_id
        change_profile(
            db,
            client_id,
            {"registered_addr": NEW_ADDRESS},
            change_date=date(2026, 9, 1),
            changed_by="m@firm.local",
            reason="Later move",
            scope=ChangeScope.CURRENT_FY,
        )
        db.expire_all()
        assert _engagement(db, client_id, "2025-26").profile_id == before


class TestAuditTrail:
    def test_the_scope_and_affected_years_are_recorded(self, db: Session, client_id: int) -> None:
        from app.services.client import change_history

        _change(db, client_id, ChangeScope.CURRENT_FY)
        latest = change_history(db, client_id)[0]
        assert "current_fy" in latest.after_json
        assert "2025-26" in latest.after_json
        # The finalised year must not appear as affected.
        assert "2024-25" not in latest.after_json


class TestComparisonFormatting:
    """§12 — the What Changed screen groups amounts like every other surface.

    It did not. `_fmt` fell through to `str(value)`, so a Decimal turnover
    reached the page as "186500000.00" — the same defect §19 names for
    documents, on the screen a partner uses to decide whether anything moved
    since last year. Found by driving a real rollover, not by a test.
    """

    def test_an_amount_is_grouped_in_the_indian_style(self) -> None:
        from decimal import Decimal

        from app.core.comparison import _fmt

        assert _fmt(Decimal("186500000.00")) == "18,65,00,000"
        assert _fmt(Decimal("4260000")) == "42,60,000"

    def test_a_date_is_written_out(self) -> None:
        from datetime import date

        from app.core.comparison import _fmt

        assert _fmt(date(2026, 3, 31)) == "31st March, 2026"

    def test_nothing_renders_as_a_dash_not_none(self) -> None:
        from app.core.comparison import _fmt

        assert _fmt(None) == "—"
        assert _fmt("") == "—"

    def test_no_raw_decimal_reaches_a_comparison_row(self, db, clause_set) -> None:
        """The property that matters, asserted over every row rather than a
        sample: nothing on the screen may look like `123456.00`."""
        import re

        from sqlalchemy import select

        from app.core.comparison import compare
        from app.models.engagement import Engagement

        engagements = list(db.scalars(select(Engagement).order_by(Engagement.fy_end)))
        rows = compare(db, engagements[0], engagements[-1])
        offenders = [
            f"{r.item}: {r.previous!r} / {r.current!r}"
            for r in rows
            if re.fullmatch(r"-?\d{4,}\.\d{2}", r.previous)
            or re.fullmatch(r"-?\d{4,}\.\d{2}", r.current)
        ]
        assert not offenders, "ungrouped amounts on the comparison screen:\n  " + "\n  ".join(
            offenders
        )
