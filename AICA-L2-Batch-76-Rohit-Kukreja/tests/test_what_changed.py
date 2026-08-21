"""The What Changed screen and the rollover flow. §6.3, §6.4.

This is the Gate C scenario end to end. The protocol requires it to be run
by hand as well — *"do not accept a written account of it"* — so this file
proves the mechanism, not the sign-off.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.carryforward import roll_forward
from app.core.comparison import Severity, compare, summarise
from app.models.engagement import Engagement
from app.models.enums import Designation, GoingConcern, KmpRole, OpinionType
from app.models.masters import Director, Kmp
from app.services.auth import CSRF_COOKIE
from app.services.client import ChangeScope, change_profile
from tests.test_client_routes import _sign_in


@pytest.fixture
def source(db: Session, client_id: int) -> Engagement:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2025-26")
    )
    assert found is not None
    found.opinion_type = OpinionType.CLEAN
    db.flush()
    return found


def _row(rows: list, item: str):
    return next(r for r in rows if r.item == item)


class TestGateCScenario:
    """ABC Private Limited, FY 2025-26 finalised, rolled to FY 2026-27.

    Registered address unchanged · one director resigned in October, one
    appointed in January · CFO changed · revenue up 40% · new litigation ·
    opinion moves from unmodified to qualified.
    """

    @pytest.fixture
    def rolled(self, db: Session, source: Engagement, client_id: int) -> Engagement:
        target, _ = roll_forward(
            db,
            source.engagement_id,
            fy_start=date(2026, 4, 1),
            fy_end=date(2027, 3, 31),
            profile_id=source.profile_id,
            rolled_by="manager@firm.local",
        )
        # The five changes the protocol lists.
        target.opinion_type = OpinionType.QUALIFIED
        db.add(
            Kmp(
                client_id=client_id,
                name="V. Rao",
                role=KmpRole.CFO,
                appointment_date=date(2026, 7, 1),
            )
        )
        existing_cfo = db.scalar(
            select(Kmp).where(Kmp.client_id == client_id, Kmp.name == "D. Shah")
        )
        if existing_cfo:
            existing_cfo.cessation_date = date(2026, 6, 30)
        db.add(
            Director(
                client_id=client_id,
                name="A. Krishnan",
                din="00456789",
                designation=Designation.INDEPENDENT,
                appointment_date=date(2026, 8, 1),
            )
        )
        change_profile(
            db,
            client_id,
            {"has_subsidiary": True},
            change_date=date(2026, 4, 2),
            changed_by="m@firm.local",
            reason="Acquired a subsidiary",
            scope=ChangeScope.CURRENT_FY,
        )
        db.flush()
        return target

    def test_master_data_is_inherited_without_re_entry(
        self, db: Session, source: Engagement, rolled: Engagement
    ) -> None:
        rows = compare(db, source, rolled)
        assert _row(rows, "Registered address").severity is Severity.SAME
        assert _row(rows, "Company type").severity is Severity.SAME

    def test_directors_are_computed_for_the_year_from_effective_dates(
        self, db: Session, source: Engagement, rolled: Engagement
    ) -> None:
        # §18.8 — never typed. The new appointment must appear on its own.
        rows = compare(db, source, rolled)
        assert _row(rows, "Directors").changed

    def test_the_cfo_change_is_detected(
        self, db: Session, source: Engagement, rolled: Engagement
    ) -> None:
        row = _row(compare(db, source, rolled), "Key Managerial Personnel")
        assert row.changed
        assert "V. Rao" in row.current
        assert "D. Shah" in row.previous

    def test_a_change_in_the_group_is_detected(
        self, db: Session, source: Engagement, rolled: Engagement
    ) -> None:
        """Acquiring a subsidiary changes the Board's Report, so it belongs here.

        This used to assert on turnover, which the comparison screen carried
        until the figures stopped driving anything.
        """
        assert _row(compare(db, source, rolled), "Has a subsidiary").changed

    def test_the_opinion_change_is_flagged_red_not_amber(
        self, db: Session, source: Engagement, rolled: Engagement
    ) -> None:
        # §6.4 — an opinion modification is significant, never merely changed.
        row = _row(compare(db, source, rolled), "Audit opinion")
        assert row.severity is Severity.SIGNIFICANT
        assert row.previous == "clean"
        assert row.current == "qualified"

    def test_the_summary_counts_the_significant_change(
        self, db: Session, source: Engagement, rolled: Engagement
    ) -> None:
        assert summarise(compare(db, source, rolled))["significant"] >= 1

    def test_year_specific_fields_start_blank(self, db: Session, source: Engagement) -> None:
        target, _ = roll_forward(
            db,
            source.engagement_id,
            fy_start=date(2026, 4, 1),
            fy_end=date(2027, 3, 31),
            profile_id=source.profile_id,
            rolled_by="m",
        )
        assert target.opinion_type is None
        assert target.report_date is None
        assert target.locked_at is None


class TestSeverity:
    def test_going_concern_is_significant(self, db: Session, source: Engagement) -> None:
        target, _ = roll_forward(
            db,
            source.engagement_id,
            fy_start=date(2026, 4, 1),
            fy_end=date(2027, 3, 31),
            profile_id=source.profile_id,
            rolled_by="m",
        )
        target.going_concern = GoingConcern.MATERIAL_UNCERTAINTY
        db.flush()
        assert _row(compare(db, source, target), "Going concern").severity is (Severity.SIGNIFICANT)

    def test_an_unchanged_item_is_green(self, db: Session, source: Engagement) -> None:
        target, _ = roll_forward(
            db,
            source.engagement_id,
            fy_start=date(2026, 4, 1),
            fy_end=date(2027, 3, 31),
            profile_id=source.profile_id,
            rolled_by="m",
        )
        assert _row(compare(db, source, target), "Company type").severity is Severity.SAME


class TestOverHttp:
    def test_the_roll_forward_form_renders(
        self, app_client: TestClient, source: Engagement
    ) -> None:
        _sign_in(app_client)
        response = app_client.get(f"/engagements/{source.engagement_id}/roll-forward")
        assert response.status_code == 200
        assert "start blank" in response.text

    def test_rolling_forward_redirects_to_what_changed(
        self, app_client: TestClient, source: Engagement
    ) -> None:
        csrf = _sign_in(app_client)
        response = app_client.post(
            f"/engagements/{source.engagement_id}/roll-forward",
            data={
                "csrf_token": csrf,
                "fy_start": "2026-04-01",
                "fy_end": "2027-03-31",
                "category": ["auditors_report", "caro_2020"],
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "what-changed" in response.headers["location"]

    def test_what_changed_lists_the_unconfirmed_inheritances(
        self, app_client: TestClient, source: Engagement
    ) -> None:
        csrf = _sign_in(app_client)
        redirect = app_client.post(
            f"/engagements/{source.engagement_id}/roll-forward",
            data={
                "csrf_token": csrf,
                "fy_start": "2026-04-01",
                "fy_end": "2027-03-31",
            },
            follow_redirects=False,
        )
        page = app_client.get(redirect.headers["location"])
        assert page.status_code == 200
        assert "await confirmation" in page.text
        assert "caro.viii" in page.text

    def test_a_duplicate_rollover_shows_a_message(
        self, app_client: TestClient, source: Engagement
    ) -> None:
        csrf = _sign_in(app_client)
        payload = {
            "csrf_token": csrf,
            "fy_start": "2026-04-01",
            "fy_end": "2027-03-31",
        }
        app_client.post(
            f"/engagements/{source.engagement_id}/roll-forward",
            data=payload,
            follow_redirects=False,
        )
        second = app_client.post(
            f"/engagements/{source.engagement_id}/roll-forward",
            data=payload,
            follow_redirects=False,
        )
        assert second.status_code == 400
        assert "already exists" in second.text
        assert "Traceback" not in second.text

    def test_what_changed_needs_an_earlier_year(
        self, app_client: TestClient, db: Session, client_id: int
    ) -> None:
        _sign_in(app_client)
        earliest = db.scalar(
            select(Engagement).where(Engagement.client_id == client_id).order_by(Engagement.fy_end)
        )
        assert earliest is not None
        response = app_client.get(f"/engagements/{earliest.engagement_id}/what-changed")
        assert response.status_code == 404
        assert "Traceback" not in response.text

    def test_the_applicability_page_shows_a_basis_for_every_flag(
        self, app_client: TestClient, source: Engagement
    ) -> None:
        _sign_in(app_client)
        body = app_client.get(f"/engagements/{source.engagement_id}/applicability").text
        for flag in ("caro", "ifc", "csr", "kam"):
            assert flag in body
        assert "exemption" in body or "does not apply" in body

    def test_csrf_is_required_to_roll_forward(
        self, app_client: TestClient, source: Engagement
    ) -> None:
        _sign_in(app_client)
        app_client.cookies.delete(CSRF_COOKIE)
        response = app_client.post(
            f"/engagements/{source.engagement_id}/roll-forward",
            data={
                "csrf_token": "forged",
                "fy_start": "2026-04-01",
                "fy_end": "2027-03-31",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
