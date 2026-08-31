"""The validation screen and the export gate must not disagree. Decision 76.

The firm hit this on 21 August 2026: "1 finding(s) block export of this
document", beside a findings table reading "Nothing to report" and a badge
reading "no blocking findings". Export refused; the screen that exists to say
why showed nothing to fix, so there was no way forward at all.

Two different computations answered the same question. Export asks
`build_document`. The validation screen asked the FIELD CATALOGUE, filtered by
what the build had found — so a blocking item the catalogue has no row for
produced no finding. A table with no rows has no catalogue row by its nature,
and so could never have appeared.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.core.consistency import DocumentBlocks, Severity, blocking, check
from app.models.engagement import Engagement


def _engagement(db: Session) -> Engagement:
    engagement = db.scalar(select(Engagement))
    assert engagement is not None
    return engagement


class TestNothingBlocksInSilence:
    """Every kind of block `build_document` reports must reach the screen."""

    def test_a_clause_the_catalogue_has_never_heard_of_still_reports(
        self, db: Session, clause_set: ClauseSet
    ) -> None:
        """The exact shape of the defect.

        Before decision 76 this returned nothing at all: the sweep walked the
        catalogue and skipped anything not in it, so an unresolved clause with
        no catalogue row vanished.
        """
        findings = check(
            db,
            _engagement(db),
            clause_set,
            blocks=DocumentBlocks(unanswered=frozenset({"no.catalogue.row.at.all"})),
        )
        assert any(f.rule == "clause_unresolved" for f in blocking(findings))

    def test_a_table_with_no_rows_reports(self, db: Session, clause_set: ClauseSet) -> None:
        """A repeating block has no catalogue field by its nature, so this was
        the case most certain never to appear."""
        findings = check(
            db,
            _engagement(db),
            clause_set,
            blocks=DocumentBlocks(missing_rows=frozenset({"iar.litigation"})),
        )
        found = [f for f in blocking(findings) if f.rule == "rows_missing"]
        assert found, "a table needing rows produced no finding"
        assert "at least one row" in found[0].message

    def test_a_missing_narrative_reports(self, db: Session, clause_set: ClauseSet) -> None:
        findings = check(
            db,
            _engagement(db),
            clause_set,
            blocks=DocumentBlocks(missing_narratives=frozenset({"caro.viii"})),
        )
        found = [f for f in blocking(findings) if f.rule == "narrative_missing"]
        assert found, "a missing explanation produced no finding"
        assert found[0].field_key == "caro.viii.narrative"

    def test_the_three_kinds_read_differently(self, db: Session, clause_set: ClauseSet) -> None:
        """Merged into one set they all said "unanswered", which helps nobody
        find any of them."""
        findings = check(
            db,
            _engagement(db),
            clause_set,
            blocks=DocumentBlocks(
                unanswered=frozenset({"caro.viii"}),
                missing_narratives=frozenset({"caro.vii.b"}),
                missing_rows=frozenset({"iar.litigation"}),
            ),
        )
        rules = {f.rule for f in blocking(findings)}
        assert {"narrative_missing", "rows_missing"} <= rules
        assert len({f.message for f in blocking(findings)}) >= 3

    @pytest.mark.parametrize(
        "blocks",
        [
            DocumentBlocks(unanswered=frozenset({"caro.viii"})),
            DocumentBlocks(missing_narratives=frozenset({"caro.viii"})),
            DocumentBlocks(missing_rows=frozenset({"caro.viii"})),
        ],
    )
    def test_any_block_at_all_produces_at_least_one_finding(
        self, db: Session, clause_set: ClauseSet, blocks: DocumentBlocks
    ) -> None:
        """The invariant, stated plainly: if anything blocks, something shows.

        `blocking_count` on the badge and the findings list are both derived
        from this, so they cannot disagree the way they did.
        """
        findings = check(db, _engagement(db), clause_set, blocks=blocks)
        assert blocking(findings), f"{blocks} blocked export and reported nothing"


class TestTheScreenAndTheGateAgree:
    def test_a_clean_build_reports_no_completeness_block(
        self, db: Session, clause_set: ClauseSet
    ) -> None:
        """The other direction. Nothing unresolved must not invent a block —
        that was the 41-of-129 complaint, and this holds the fix in place."""
        findings = check(db, _engagement(db), clause_set, blocks=DocumentBlocks())
        invented = [
            f
            for f in findings
            if f.severity is Severity.BLOCK
            and f.rule in {"mandatory_empty", "clause_unresolved", "rows_missing"}
        ]
        assert invented == [], f"the gate invented blocks: {[f.message for f in invented]}"

    def test_the_carry_forward_rule_runs_with_and_without_a_build(
        self, db: Session, clause_set: ClauseSet
    ) -> None:
        """It was inside the completeness sweep, behind its early return, and a
        rewrite of that sweep dropped it silently.

        It cannot be derived from a build: a carried answer resolves, prints and
        exports exactly like a confirmed one. The only thing wrong with it is
        that nobody has looked at it, which no renderer can discover.
        """
        from app.models.engagement import EngagementResponse
        from app.models.enums import ResponseSource

        # Written straight to the row: the fixture's first year is finalised,
        # and a finalised year refuses `set_response` — which is correct, and
        # beside the point of this test.
        engagement = _engagement(db)
        db.add(
            EngagementResponse(
                engagement_id=engagement.engagement_id,
                field_key="caro.viii",
                value_text="none",
                source=ResponseSource.CARRIED_FORWARD,
                reviewed=False,
                updated_by="t",
            )
        )
        db.flush()

        for blocks in (None, DocumentBlocks()):
            findings = check(db, engagement, clause_set, blocks=blocks)
            assert any(
                f.rule == "unconfirmed_carry_forward" for f in blocking(findings)
            ), f"the carry-forward gate vanished when blocks={blocks!r}"
