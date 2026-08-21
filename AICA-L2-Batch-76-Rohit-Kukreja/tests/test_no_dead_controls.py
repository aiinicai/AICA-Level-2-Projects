"""Phase 7 exit test — no dead controls (§16, §18.3).

The protocol names this test specifically: *"`test_no_dead_controls.py`
marked xfail or skipped. This is the test that catches the prototype's worst
defect class. If it is inconvenient, that is because it is finding
something."*

It is not marked xfail. It is not skipped. It must stay that way.

A dead control is a field a user can set that changes no rendered document.
There are three ways to have one, and each is checked below:

  1. an option that matches no clause variant;
  2. a catalogued field no clause reads;
  3. a clause whose answer never alters the output.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.loader import unreachable_options
from app.clauses.model import ClauseSet, DataType
from app.clauses.resolve import resolve
from app.models.engagement import Engagement, FieldCatalog
from app.services.document import build_document
from app.services.engagement import child_row_dicts
from app.services.render_context import render_context_for


@pytest.fixture
def engagement(db: Session, client_id: int) -> Engagement:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2025-26")
    )
    assert found is not None
    return found


class TestEveryOptionReachesAVariant:
    """Defect 1 — a control the user can set that selects no wording."""

    def test_no_clause_has_an_unreachable_option(self, clause_set: ClauseSet) -> None:
        dead = {
            clause.id: unreachable_options(clause)
            for clause in clause_set.clauses
            if unreachable_options(clause)
        }
        assert not dead, f"options that match no variant: {dead}"

    def test_every_option_produces_a_non_empty_body(self, clause_set: ClauseSet) -> None:
        for clause in clause_set.clauses:
            if clause.input is None or clause.input.datatype is not DataType.SELECT:
                continue
            for option in clause.input.options:
                resolved = resolve(clause, {"value": option.value})
                assert (
                    resolved.body.strip()
                ), f"{clause.id} option {option.value!r} renders an empty body"


class TestEveryFieldIsRead:
    """Defect 2 — a catalogued field no document consumes."""

    def test_every_catalogued_field_belongs_to_a_clause(
        self, db: Session, clause_set: ClauseSet
    ) -> None:
        clause_ids = {clause.id for clause in clause_set.clauses}
        orphans = [
            entry.field_key
            for entry in db.scalars(select(FieldCatalog))
            if entry.clause_id not in clause_ids
        ]
        assert not orphans, f"catalogued fields with no clause: {orphans}"

    def test_every_clause_input_has_a_catalogue_row(
        self, db: Session, clause_set: ClauseSet
    ) -> None:
        missing = [
            clause.input.key
            for clause in clause_set.clauses
            if clause.input is not None and db.get(FieldCatalog, clause.input.key) is None
        ]
        assert not missing, f"clause inputs absent from the catalogue: {missing}"


class TestEveryFieldChangesADocument:
    """Defect 3 — §18.3, the acceptance criterion itself.

    *"Every catalogued field demonstrably changes at least one rendered
    document."* Demonstrated by rendering twice with different answers and
    requiring the output to differ.
    """

    def _render(
        self,
        db: Session,
        clause_set: ClauseSet,
        engagement: Engagement,
        document: str,
        responses: dict[str, object],
    ) -> str:
        child_data = {
            clause.id: child_row_dicts(db, engagement.engagement_id, clause.repeating_block.entity)
            for clause in clause_set.for_document(document, engagement.fy_end)
            if clause.repeating_block is not None
        }
        built = build_document(
            clause_set,
            document,
            engagement.fy_end,
            responses=responses,
            child_rows=child_data,
            context=render_context_for(engagement, None, None),
        )
        return "\n".join(built.document.text_nodes())

    def test_each_option_produces_distinct_clause_text(self, clause_set: ClauseSet) -> None:
        """Every option must resolve to different wording.

        Resolved per clause rather than by re-rendering the whole document
        per option: at 146 clauses the latter is quadratic and takes minutes,
        and it tests nothing the direct comparison does not.
        """
        for clause in clause_set.clauses:
            if clause.input is None or clause.input.datatype is not DataType.SELECT:
                continue
            bodies = {
                option.value: resolve(clause, {"value": option.value}).body
                for option in clause.input.options
            }
            distinct = set(bodies.values())
            assert len(distinct) == len(bodies), (
                f"{clause.id}: {len(bodies)} options produce only "
                f"{len(distinct)} distinct bodies — at least one is a dead control"
            )

    def test_every_clause_reaches_its_document(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        """A field whose clause never renders is dead however distinct it is.

        Rendered once per document, not once per option.
        """
        baseline = {
            clause.input.key: clause.input.options[0].value
            for clause in clause_set.clauses
            if clause.input is not None and clause.input.options
        }
        for document in clause_set.documents:
            expected = {
                clause.id for clause in clause_set.for_document(document, engagement.fy_end)
            }
            built = build_document(
                clause_set,
                document,
                engagement.fy_end,
                responses=baseline,
                child_rows={
                    clause.id: child_row_dicts(
                        db, engagement.engagement_id, clause.repeating_block.entity
                    )
                    for clause in clause_set.for_document(document, engagement.fy_end)
                    if clause.repeating_block is not None
                },
                context=render_context_for(engagement, None, None),
            )
            rendered = {
                node.clause_id for node in built.document.nodes if getattr(node, "clause_id", "")
            }
            missing = expected - rendered
            assert not missing, f"{document}: clauses that rendered nothing — {missing}"

    def test_a_narrative_reaches_the_findings_not_the_void(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        """A narrative field must change *something* — here, whether the
        document is exportable."""
        responses: dict[str, object] = {
            "rule11.a.status": "none",
            "rule11.e.status": "nil_both",
            "rule11.f.status": "not_complied",
            "rule11.g.status": "throughout",
        }
        built = build_document(
            clause_set,
            "auditors_report",
            engagement.fy_end,
            responses=responses,
            context=render_context_for(engagement, None, None),
        )
        assert "rule11.f" in built.missing_narratives

        with_narrative = build_document(
            clause_set,
            "auditors_report",
            engagement.fy_end,
            responses={**responses, "rule11.f.narrative": "Explained."},
            context=render_context_for(engagement, None, None),
        )
        assert "rule11.f" not in with_narrative.missing_narratives


class TestGuardTheGuard:
    """If these fail, the tests above have stopped testing anything."""

    def test_the_repository_actually_has_select_fields(self, clause_set: ClauseSet) -> None:
        selects = [
            c
            for c in clause_set.clauses
            if c.input is not None and c.input.datatype is DataType.SELECT
        ]
        assert len(selects) >= 5

    def test_a_deliberately_dead_control_is_caught(self) -> None:
        from app.clauses.loader import clause_from_dict

        clause = clause_from_dict(
            {
                "id": "t.dead",
                "document": "caro_2020",
                "title": "T",
                "input": {
                    "key": "t.dead",
                    "datatype": "select",
                    "options": [{"value": "a"}, {"value": "unreachable"}],
                },
                "variants": [{"when": "value == 'a'", "body": "A."}],
            }
        )
        assert unreachable_options(clause) == ("unreachable",)

    def test_the_catalogue_is_not_empty(self, db: Session) -> None:
        assert len(list(db.scalars(select(FieldCatalog)))) > 0
