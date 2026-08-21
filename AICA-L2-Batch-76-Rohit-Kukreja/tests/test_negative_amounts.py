"""Negative figures in the Board's Report financial summary. Decision 71.

The firm's team reported the tool closing on them when they entered negative
values. The cause was one unguarded conversion: `Decimal(text)` in
`_coerce_child`. `decimal.InvalidOperation` inherits from `ArithmeticError`,
not `ValueError`, so it slipped through every router's
`except (CsrfError, EngagementError, ValueError)` and left the request with no
handler at all.

A loss written the way an accountant writes it -- "(1,23,456)" -- was enough to
trigger it, which is why it showed up on the financial summary first.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engagement import Engagement, FinancialSummary
from app.models.enums import EngagementStatus
from app.services.engagement import EngagementError, add_child_row, coerce, parse_amount


class TestTheExceptionNeverMatchedTheHandler:
    def test_invalid_operation_is_not_a_value_error(self) -> None:
        """The premise of the bug, asserted so it cannot quietly come back."""
        assert not issubclass(InvalidOperation, ValueError)
        assert issubclass(InvalidOperation, ArithmeticError)


class TestAmountsAreParsedTheWayAccountantsWriteThem:
    @pytest.mark.parametrize(
        ("typed", "expected"),
        [
            ("1234", "1234"),
            ("-1234", "-1234"),
            ("1,23,456", "123456"),
            ("(1,23,456)", "-123456"),
            ("(1234)", "-1234"),
            ("- 1234", "-1234"),
            ("1234-", "-1234"),
            ("\u22121234", "-1234"),  # unicode minus, pasted from Word
            ("\u20b9 1,234.50", "1234.50"),  # rupee sign and a space
            ("Rs. 1,234", "1234"),
            ("(1,234.75)", "-1234.75"),
        ],
    )
    def test_it_reads(self, typed: str, expected: str) -> None:
        assert parse_amount(typed) == Decimal(expected)

    @pytest.mark.parametrize("typed", ["", "abc", "-", "()", "1.2.3", "(12", "12)"])
    def test_nonsense_is_refused_in_a_way_a_router_can_catch(self, typed: str) -> None:
        with pytest.raises(EngagementError):
            parse_amount(typed)

    def test_the_eav_path_agrees(self) -> None:
        _, num, _ = coerce("(1,23,456)", "amount")
        assert num == Decimal("-123456")


def _open_engagement(db: Session) -> Engagement:
    """The fixture's first year is finalised, and a finalised year is read-only."""
    engagement = db.scalars(
        select(Engagement).where(Engagement.status != EngagementStatus.FINALISED)
    ).first()
    assert engagement is not None, "no editable engagement in the fixture"
    return engagement


class TestTheFinancialSummaryTakesALoss:
    def test_a_bracketed_loss_is_stored_negative(self, db: Session) -> None:
        engagement = _open_engagement(db)
        add_child_row(
            db,
            engagement.engagement_id,
            "financial_summary",
            {
                "particulars": "Profit/(Loss) after Depreciation & Tax",
                "current_year": "(4,52,310)",
                "previous_year": "1,10,000",
            },
            added_by="tester",
        )
        db.flush()
        row = db.scalar(
            select(FinancialSummary).where(
                FinancialSummary.engagement_id == engagement.engagement_id
            )
        )
        assert row is not None
        assert row.current_year == Decimal("-452310")
        assert row.previous_year == Decimal("110000")

    def test_a_bad_figure_raises_something_the_router_handles(self, db: Session) -> None:
        """Not a 500. The workspace re-renders with the message."""
        engagement = _open_engagement(db)
        with pytest.raises(EngagementError):
            add_child_row(
                db,
                engagement.engagement_id,
                "financial_summary",
                {"particulars": "Revenue", "current_year": "twelve lakh"},
                added_by="tester",
            )


class TestEveryFormHandlerCatchesArithmetic:
    """The routers meant "bad input"; they wrote `ValueError`.

    Swept rather than listed, so a handler added next month is covered too.
    """

    def test_no_handler_catches_value_error_without_arithmetic_error(self) -> None:
        from pathlib import Path

        offenders = []
        for path in (Path("app") / "routers").glob("*.py"):
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "except (" not in line or "ValueError" not in line:
                    continue
                if "ArithmeticError" not in line:
                    offenders.append(f"{path.name}:{line_no}")
        assert offenders == [], f"a typed figure can still escape: {offenders}"
