"""The Board's Report financial summary as a fixed schedule. Decision 73.

Item 4 of the firm's team's fifth round. The particulars used to be typed, so
every preparer produced a different set of lines in a different order. The
lines are now declared in `content/`, and the three profit lines are
calculated from the ones above them.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet, RepeatingBlock
from app.core import arithmetic
from app.models.engagement import Engagement
from app.models.enums import EngagementStatus
from app.services.engagement import EngagementError, child_rows, save_schedule, schedule_state

ENTITY = "financial_summary"

#: What the firm asked for, in the order it asked for it.
EXPECTED = (
    "Revenue",
    "Expenses",
    "Profit/(Loss) before depreciation",
    "Less: Depreciation",
    "Profit/(Loss) after depreciation",
    "Provision for Tax",
    "Provision for Deferred Tax Asset/(Liability)",
    "Profit/(Loss) after Depreciation & Tax",
)


def _block(clause_set: ClauseSet) -> RepeatingBlock:
    clause = clause_set.get("bdr.financial.summary")
    assert clause is not None and clause.repeating_block is not None
    return clause.repeating_block


def _open_engagement(db: Session) -> Engagement:
    """The fixture's first year is finalised, and a finalised year is read-only."""
    engagement = db.scalars(
        select(Engagement).where(Engagement.status != EngagementStatus.FINALISED)
    ).first()
    assert engagement is not None
    return engagement


def _current(db: Session, engagement: Engagement) -> dict[str, Decimal | None]:
    return {r.particulars: r.current_year for r in child_rows(db, engagement.engagement_id, ENTITY)}


class TestTheLinesArePrescribed:
    def test_the_schedule_is_the_eight_lines_in_order(
        self, production_clause_set: ClauseSet
    ) -> None:
        block = _block(production_clause_set)
        assert block.is_schedule
        assert tuple(r.particulars for r in block.fixed_rows) == EXPECTED

    def test_the_three_profit_lines_are_calculated(self, production_clause_set: ClauseSet) -> None:
        block = _block(production_clause_set)
        computed = {r.particulars for r in block.fixed_rows if r.is_computed}
        assert computed == {
            "Profit/(Loss) before depreciation",
            "Profit/(Loss) after depreciation",
            "Profit/(Loss) after Depreciation & Tax",
        }


class TestTheArithmetic:
    def test_a_loss_year_adds_up(self, db: Session, production_clause_set: ClauseSet) -> None:
        """The figures the schedule was first driven with, kept as a worked
        example: a loss year with a deferred tax CREDIT, which is the case the
        sign convention is easiest to get wrong on.
        """
        block = _block(production_clause_set)
        engagement = _open_engagement(db)
        typed = {
            ("revenue", "current_year"): "85,00,000",
            ("expenses", "current_year"): "90,00,000",
            ("depreciation", "current_year"): "3,50,000",
            ("tax", "current_year"): "0",
            # Entered in brackets, the way it is written in the accounts.
            ("deferred_tax", "current_year"): "(1,20,000)",
        }
        save_schedule(db, engagement.engagement_id, ENTITY, block, typed, saved_by="tester")
        db.flush()

        rows = _current(db, engagement)
        assert rows["Profit/(Loss) before depreciation"] == Decimal("-500000")
        assert rows["Profit/(Loss) after depreciation"] == Decimal("-850000")
        # A deferred tax credit reduces the charge, so it improves the result.
        assert rows["Profit/(Loss) after Depreciation & Tax"] == Decimal("-730000")

    def test_a_blank_line_leaves_the_subtotal_blank(
        self, db: Session, production_clause_set: ClauseSet
    ) -> None:
        """Not nought. Nought is a figure someone arrived at."""
        block = _block(production_clause_set)
        engagement = _open_engagement(db)
        save_schedule(
            db,
            engagement.engagement_id,
            ENTITY,
            block,
            {("revenue", "current_year"): "10,00,000"},
            saved_by="tester",
        )
        db.flush()
        assert _current(db, engagement)["Profit/(Loss) before depreciation"] is None

    def test_a_sub_total_cannot_be_typed_over(
        self, db: Session, production_clause_set: ClauseSet
    ) -> None:
        """A figure posted against a computed row is ignored, not stored.

        This is the whole point of the change: a sub-total that can be typed is
        a sub-total that can disagree with the lines above it.
        """
        block = _block(production_clause_set)
        engagement = _open_engagement(db)
        save_schedule(
            db,
            engagement.engagement_id,
            ENTITY,
            block,
            {
                ("revenue", "current_year"): "10,00,000",
                ("expenses", "current_year"): "4,00,000",
                ("pbd", "current_year"): "99,99,999",
            },
            saved_by="tester",
        )
        db.flush()
        assert _current(db, engagement)["Profit/(Loss) before depreciation"] == Decimal("600000")

    def test_saving_twice_is_saving_once(
        self, db: Session, production_clause_set: ClauseSet
    ) -> None:
        """The rows are replaced, not appended, so the schedule stays eight
        lines however many times it is saved.
        """
        block = _block(production_clause_set)
        engagement = _open_engagement(db)
        typed = {("revenue", "current_year"): "1,00,000"}
        for _ in range(3):
            save_schedule(db, engagement.engagement_id, ENTITY, block, typed, saved_by="tester")
            db.flush()
        assert len(child_rows(db, engagement.engagement_id, ENTITY)) == len(EXPECTED)

    def test_both_year_columns_are_calculated(
        self, db: Session, production_clause_set: ClauseSet
    ) -> None:
        """The previous year is a column, not an afterthought."""
        block = _block(production_clause_set)
        engagement = _open_engagement(db)
        save_schedule(
            db,
            engagement.engagement_id,
            ENTITY,
            block,
            {
                ("revenue", "previous_year"): "92,00,000",
                ("expenses", "previous_year"): "80,00,000",
            },
            saved_by="tester",
        )
        db.flush()
        rows = {
            r.particulars: r.previous_year for r in child_rows(db, engagement.engagement_id, ENTITY)
        }
        assert rows["Profit/(Loss) before depreciation"] == Decimal("1200000")


class TestTheScreenIsBuiltFromTheDeclaration:
    def test_an_untouched_engagement_still_shows_every_line(
        self, db: Session, production_clause_set: ClauseSet
    ) -> None:
        """Built from the declaration and filled in from storage, so a line
        added to the schedule appears on engagements that already exist.
        """
        block = _block(production_clause_set)
        engagement = _open_engagement(db)
        for row in child_rows(db, engagement.engagement_id, ENTITY):
            db.delete(row)
        db.flush()

        state = schedule_state(db, engagement.engagement_id, ENTITY, block)
        assert [r["particulars"] for r in state] == list(EXPECTED)
        assert all(value is None for row in state for value in row["values"].values())

    def test_computed_rows_are_marked_for_the_template(
        self, db: Session, production_clause_set: ClauseSet
    ) -> None:
        block = _block(production_clause_set)
        state = schedule_state(db, _open_engagement(db).engagement_id, ENTITY, block)
        marked = [row["computed"] for row in state]
        assert marked == [False, False, True, False, True, False, False, True]


class TestTheExpressionsAreDataNotCode:
    """Section 3.3 — the repository is data, and data is never executed."""

    @pytest.mark.parametrize(
        "expression",
        [
            "revenue * 2",
            "revenue / 0",
            "revenue ** 2",
            "sum([revenue])",
        ],
    )
    def test_only_addition_and_subtraction_are_accepted(self, expression: str) -> None:
        with pytest.raises(arithmetic.ArithmeticExpressionError):
            arithmetic.parse(expression)

    def test_a_call_is_refused(self) -> None:
        dunder = "__" + "import__"
        with pytest.raises(arithmetic.ArithmeticExpressionError):
            arithmetic.parse(dunder + "('os')")

    def test_every_declared_schedule_only_looks_upwards(
        self, production_clause_set: ClauseSet
    ) -> None:
        """Swept over the repository. A sub-total referring to a row BELOW it
        cannot be evaluated in one pass and would silently come out blank.
        """
        for clause in production_clause_set.clauses:
            block = clause.repeating_block
            if block is None or not block.is_schedule:
                continue
            seen: set[str] = set()
            for row in block.fixed_rows:
                if row.computed is not None:
                    unseen = sorted(arithmetic.names(row.computed) - seen)
                    assert not unseen, f"{clause.id}/{row.key} refers forward to {unseen}"
                seen.add(row.key)


class TestGuards:
    def test_a_free_table_is_refused(self, db: Session, production_clause_set: ClauseSet) -> None:
        """`save_schedule` is for prescribed tables only; a free one still uses
        the add-a-row path and would lose its rows here.
        """
        engagement = _open_engagement(db)
        free = next(
            clause
            for clause in production_clause_set.clauses
            if clause.repeating_block is not None and not clause.repeating_block.is_schedule
        )
        assert free.repeating_block is not None
        with pytest.raises(EngagementError):
            save_schedule(
                db,
                engagement.engagement_id,
                free.repeating_block.entity,
                free.repeating_block,
                {},
                saved_by="tester",
            )

    def test_an_unreadable_figure_is_refused_not_crashed(
        self, db: Session, production_clause_set: ClauseSet
    ) -> None:
        block = _block(production_clause_set)
        with pytest.raises(EngagementError):
            save_schedule(
                db,
                _open_engagement(db).engagement_id,
                ENTITY,
                block,
                {("revenue", "current_year"): "about ten lakh"},
                saved_by="tester",
            )
