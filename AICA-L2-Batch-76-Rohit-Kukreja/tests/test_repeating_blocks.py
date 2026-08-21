"""Repeating blocks. Build Prompt v2 §3.2.

§19: directors, KMP, litigation, statutory dues and IFC deficiencies are
never stored as free text.
"""

from __future__ import annotations

from app.clauses.loader import clause_from_dict, validate
from app.clauses.model import CarryForward, ClauseSet, DataType, RenderBlock
from app.clauses.resolve import resolve


class TestRule11ALitigation:
    def test_block_declared(self, clause_set: ClauseSet) -> None:
        block = clause_set.get("rule11.a").repeating_block
        assert block is not None
        assert block.entity == "litigation"
        assert block.min_rows == 1
        assert block.carry_forward is CarryForward.PROMPT

    def test_columns_match_the_specified_shape(self, clause_set: ClauseSet) -> None:
        block = clause_set.get("rule11.a").repeating_block
        assert block is not None
        assert block.column_keys == (
            "forum",
            "case_number",
            "nature",
            "amount",
            "period",
            "status",
            "mgmt_assessment",
        )

    def test_required_columns_marked(self, clause_set: ClauseSet) -> None:
        block = clause_set.get("rule11.a").repeating_block
        assert block is not None
        required = {c.key for c in block.columns if c.required}
        assert required == {"forum", "nature"}

    def test_amount_is_typed_not_text(self, clause_set: ClauseSet) -> None:
        # §19 — do not store formatted currency in the database.
        block = clause_set.get("rule11.a").repeating_block
        assert block is not None
        amount = next(c for c in block.columns if c.key == "amount")
        assert amount.datatype is DataType.AMOUNT

    def test_status_column_is_a_closed_set(self, clause_set: ClauseSet) -> None:
        block = clause_set.get("rule11.a").repeating_block
        assert block is not None
        status = next(c for c in block.columns if c.key == "status")
        assert status.options == ("pending", "decided", "appealed", "settled")

    def test_table_renders_only_on_the_disclosed_variant(
        self, clause_set: ClauseSet, render_context: dict[str, object]
    ) -> None:
        clause = clause_set.get("rule11.a")
        nil = resolve(clause, {**render_context, "value": "none"})
        disclosed = resolve(clause, {**render_context, "value": "disclosed"})
        assert nil.variant.render_block is None
        assert disclosed.variant.render_block is RenderBlock.TABLE


class TestCaroViiB:
    def test_disputed_dues_is_a_table(self, clause_set: ClauseSet) -> None:
        block = clause_set.get("caro.vii.b").repeating_block
        assert block is not None
        assert block.entity == "statutory_due"
        assert {"statute", "nature", "amount", "period", "forum"} <= set(block.column_keys)


class TestOrphanedBlockRejected:
    def test_block_with_no_rendering_variant_is_rejected(self) -> None:
        """Child rows collected and never printed is a silent data loss."""
        clause = clause_from_dict(
            {
                "id": "t.orphan",
                "document": "caro_2020",
                "title": "T",
                "input": {
                    "key": "t.orphan",
                    "datatype": "select",
                    "options": [{"value": "none"}, {"value": "some"}],
                },
                "repeating_block": {
                    "when": "value == 'some'",
                    "entity": "thing",
                    "columns": [{"key": "a", "label": "A"}],
                },
                "variants": [
                    {"when": "value == 'none'", "body": "None."},
                    {"when": "value == 'some'", "body": "Some."},
                ],
            }
        )
        problems = validate([clause])
        assert any("no variant renders it" in p for p in problems)


class TestEveryDeclaredBlockIsStorable:
    """A clause that declares a table must have somewhere to put the rows.

    Ten clauses authored in Phase 2 declared a `repeating_block` with no
    model behind it. The workspace raised `KeyError` on three of the six
    documents and every test still passed, because the fixture repository has
    no repeating blocks and the render harness supplied child rows directly
    instead of going through `child_row_dicts`.

    So this checks the production repository against the real registry.
    """

    def test_every_entity_has_a_model_or_is_computed(self, production_clause_set) -> None:
        """A block is storable if it has a table, or derivable if it is computed.

        `director_changes_in_year` is deliberately in the second group: §18.8
        wants directors computed from the client's register, so there is no
        table and nothing for a user to type.
        """
        from app.services.engagement import CHILD_MODELS, COMPUTED_CHILD_ROWS

        known = set(CHILD_MODELS) | set(COMPUTED_CHILD_ROWS)
        missing = [
            f"{c.id} declares {c.repeating_block.entity!r}"
            for c in production_clause_set.clauses
            if c.repeating_block and c.repeating_block.entity not in known
        ]
        assert not missing, "repeating blocks with nothing to store them:\n  " + "\n  ".join(
            missing
        )

    def test_every_declared_column_exists_on_its_model(self, production_clause_set) -> None:
        """The subtler half. `ifc_deficiency` had a model all along, but the
        clause named columns the table did not have — so the table rendered
        empty cells rather than failing."""
        from app.services.engagement import CHILD_MODELS

        problems: list[str] = []
        for clause in production_clause_set.clauses:
            block = clause.repeating_block
            if block is None:
                continue
            from app.services.engagement import COMPUTED_CHILD_ROWS

            if block.entity in COMPUTED_CHILD_ROWS:
                continue  # no table, so no columns to compare against
            model = CHILD_MODELS.get(block.entity)
            if model is None:
                continue
            absent = [key for key in block.column_keys if not hasattr(model, key)]
            if absent:
                problems.append(f"{clause.id} -> {block.entity}: {absent}")
        assert (
            not problems
        ), "columns declared in YAML but absent from the model:\n  " + "\n  ".join(problems)
