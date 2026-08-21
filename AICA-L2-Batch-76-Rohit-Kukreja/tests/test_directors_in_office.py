"""Directors computed from effective dates, never typed (§5.2, §18.8).

This is the Phase 5 exit test. The function lives in the Phase 4 model
layer, so it is tested here alongside the schema that supports it.

Seeded register for ABC Private Limited:
    R. Mehta   appointed 14-06-2010, still in office
    K. Iyer    appointed 01-04-2015, ceased 17-10-2025
    N. Bose    appointed 12-01-2026
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.enums import Designation
from app.services.client import (
    directors_during_fy,
    directors_in_office,
    kmp_in_office,
)

FY_START = date(2025, 4, 1)
FY_END = date(2026, 3, 31)


def _names(directors: list) -> set[str]:
    return {d.name for d in directors}


class TestInOffice:
    def test_at_the_year_end(self, db: Session, client_id: int) -> None:
        assert _names(directors_in_office(db, client_id, FY_END)) == {"R. Mehta", "N. Bose"}

    def test_at_the_year_start(self, db: Session, client_id: int) -> None:
        assert _names(directors_in_office(db, client_id, FY_START)) == {"R. Mehta", "K. Iyer"}

    def test_on_the_day_of_cessation_still_in_office(self, db: Session, client_id: int) -> None:
        # A director who resigns on the 17th held office on the 17th.
        assert "K. Iyer" in _names(directors_in_office(db, client_id, date(2025, 10, 17)))

    def test_the_day_after_cessation(self, db: Session, client_id: int) -> None:
        assert "K. Iyer" not in _names(directors_in_office(db, client_id, date(2025, 10, 18)))

    def test_on_the_day_of_appointment(self, db: Session, client_id: int) -> None:
        assert "N. Bose" in _names(directors_in_office(db, client_id, date(2026, 1, 12)))

    def test_the_day_before_appointment(self, db: Session, client_id: int) -> None:
        assert "N. Bose" not in _names(directors_in_office(db, client_id, date(2026, 1, 11)))

    def test_before_the_company_had_directors(self, db: Session, client_id: int) -> None:
        assert directors_in_office(db, client_id, date(2000, 1, 1)) == []


class TestDuringFinancialYear:
    def test_includes_everyone_who_held_office_at_any_point(
        self, db: Session, client_id: int
    ) -> None:
        # This is what the Directors' Report changes disclosure needs: the
        # resigning director must appear even though he is gone by year end.
        assert _names(directors_during_fy(db, client_id, FY_START, FY_END)) == {
            "R. Mehta",
            "K. Iyer",
            "N. Bose",
        }

    def test_a_prior_year_excludes_the_later_appointment(self, db: Session, client_id: int) -> None:
        during = directors_during_fy(db, client_id, date(2024, 4, 1), date(2025, 3, 31))
        assert _names(during) == {"R. Mehta", "K. Iyer"}

    def test_a_later_year_excludes_the_departed_director(self, db: Session, client_id: int) -> None:
        during = directors_during_fy(db, client_id, date(2026, 4, 1), date(2027, 3, 31))
        assert _names(during) == {"R. Mehta", "N. Bose"}

    def test_in_office_is_a_subset_of_during_the_year(self, db: Session, client_id: int) -> None:
        at_end = _names(directors_in_office(db, client_id, FY_END))
        during = _names(directors_during_fy(db, client_id, FY_START, FY_END))
        assert at_end <= during


class TestKmp:
    def test_cfo_in_office(self, db: Session, client_id: int) -> None:
        assert _names(kmp_in_office(db, client_id, FY_END)) == {"D. Shah"}

    def test_before_appointment(self, db: Session, client_id: int) -> None:
        assert kmp_in_office(db, client_id, date(2024, 1, 1)) == []


class TestBoardReportDirectorsAreComputed:
    """§18.8 — the Board's Report reads the register, it does not retype it.

    `bdr.directors.kmp` first wrote to a typed table, so the report could name
    a director the register did not have, or omit one it did. The entity
    `director_changes_in_year` has no table at all.
    """

    def test_only_changes_within_the_year_appear(self, db: Session, client_id: int) -> None:
        from sqlalchemy import select

        from app.models.engagement import Engagement
        from app.services.engagement import child_row_dicts

        engagement = db.scalar(
            select(Engagement).where(
                Engagement.client_id == client_id, Engagement.fy_code == "2025-26"
            )
        )
        assert engagement is not None
        rows = child_row_dicts(db, engagement.engagement_id, "director_changes_in_year")

        by_name = {row["name"]: row["change"] for row in rows}
        # The seed has a resignation in October and an appointment in January.
        assert by_name.get("K. Iyer") == "Resigned"
        assert by_name.get("N. Bose") == "Appointed"
        # A director who served the whole year had no change to disclose.
        assert "R. Mehta" not in by_name

    def test_it_has_no_table_and_is_read_only(self) -> None:
        from app.services.engagement import CHILD_MODELS, is_computed

        assert is_computed("director_changes_in_year")
        assert "director_changes_in_year" not in CHILD_MODELS

    def test_correcting_the_register_changes_the_report(self, db: Session, client_id: int) -> None:
        """The property that makes this worth doing: one source of truth."""
        from sqlalchemy import select

        from app.models.engagement import Engagement
        from app.models.masters import Director
        from app.services.engagement import child_row_dicts

        engagement = db.scalar(
            select(Engagement).where(
                Engagement.client_id == client_id, Engagement.fy_code == "2025-26"
            )
        )
        assert engagement is not None
        before = child_row_dicts(db, engagement.engagement_id, "director_changes_in_year")

        db.add(
            Director(
                client_id=client_id,
                name="Z. Late Joiner",
                din="00999888",
                designation=Designation.NON_EXECUTIVE,
                appointment_date=date(2025, 12, 1),
            )
        )
        db.flush()

        after = child_row_dicts(db, engagement.engagement_id, "director_changes_in_year")
        assert len(after) == len(before) + 1
        assert any(row["name"] == "Z. Late Joiner" for row in after)
