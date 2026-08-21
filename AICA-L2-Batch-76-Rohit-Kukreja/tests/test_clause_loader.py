"""Phase 1 exit test — sample CARO and Rule 11 clauses parse and resolve
all variants (Build Prompt v2 §16)."""

from __future__ import annotations

from datetime import date

import pytest

from app.clauses.loader import ClauseValidationError, clause_from_dict, validate
from app.clauses.model import CarryForward, ClauseSet, DataType, Severity
from app.clauses.resolve import UnresolvedClauseError, resolve, select_variant
from tests.conftest import FY_2022_23, FY_2025_26


class TestRepositoryLoads:
    def test_loads(self, clause_set: ClauseSet) -> None:
        # The fixture repository — six authored clauses. The production
        # repository is asserted separately in test_repository_state.py.
        assert len(clause_set) == 6

    def test_manifest_version(self, clause_set: ClauseSet) -> None:
        assert clause_set.manifest.template_version == "0.1.0-phase1"

    def test_needs_review_is_not_empty(self, clause_set: ClauseSet) -> None:
        # Protocol §5: an empty needs_review list across authored statutory
        # prose means the agent generated confidently rather than carefully.
        assert len(clause_set.needs_review) > 0

    def test_documents_declared(self, clause_set: ClauseSet) -> None:
        assert set(clause_set.documents) == {"auditors_report", "caro_2020"}


class TestCaroClause:
    def test_shape(self, clause_set: ClauseSet) -> None:
        clause = clause_set.get("caro.viii")
        assert clause.number == "(viii)"
        assert clause.clause_ref == "CARO 2020, para 3(viii)"
        assert clause.effective_from == date(2021, 4, 1)
        assert clause.requires == ("caro",)
        assert clause.input is not None
        assert clause.input.datatype is DataType.SELECT
        assert clause.input.carry_forward is CarryForward.PROMPT

    @pytest.mark.parametrize("value", ["none", "recorded", "not_recorded"])
    def test_every_option_resolves(
        self, clause_set: ClauseSet, render_context: dict[str, object], value: str
    ) -> None:
        clause = clause_set.get("caro.viii")
        resolved = resolve(clause, {**render_context, "value": value})
        assert resolved.body
        assert "Income Tax Act, 1961" in resolved.body

    def test_adverse_answer_is_an_exception_and_forces_a_narrative(
        self, clause_set: ClauseSet, render_context: dict[str, object]
    ) -> None:
        resolved = resolve(clause_set.get("caro.viii"), {**render_context, "value": "not_recorded"})
        assert resolved.variant.severity is Severity.EXCEPTION
        assert resolved.requires_narrative is True

    def test_clean_answer_is_neither(
        self, clause_set: ClauseSet, render_context: dict[str, object]
    ) -> None:
        resolved = resolve(clause_set.get("caro.viii"), {**render_context, "value": "none"})
        assert resolved.variant.severity is None
        assert resolved.requires_narrative is False


class TestRule11:
    def test_no_clause_d_exists(self, clause_set: ClauseSet) -> None:
        # §4.2 and §19 — there is no Rule 11(d); it stands omitted.
        assert "rule11.d" not in clause_set
        assert all(c.number != "(d)" for c in clause_set.for_document("auditors_report"))

    def test_e_is_one_clause_not_two(self, clause_set: ClauseSet) -> None:
        # §19 — do not split Rule 11(e) into two clauses.
        assert "rule11.e" in clause_set
        assert "rule11.e.i" not in clause_set
        assert "rule11.e.ii" not in clause_set

    def test_e_body_carries_all_three_parts(
        self, clause_set: ClauseSet, render_context: dict[str, object]
    ) -> None:
        resolved = resolve(clause_set.get("rule11.e"), {**render_context, "value": "nil_both"})
        assert "(i)" in resolved.body
        assert "(ii)" in resolved.body
        assert "(iii)" in resolved.body

    @pytest.mark.parametrize("value", ["none", "complied", "not_complied"])
    def test_f_reports_even_on_a_nil_answer(
        self, clause_set: ClauseSet, render_context: dict[str, object], value: str
    ) -> None:
        # §4.2 — nil reporting is mandatory; the prototype suppressed it.
        resolved = resolve(clause_set.get("rule11.f"), {**render_context, "value": value})
        assert resolved.body.strip()

    @pytest.mark.parametrize("value", ["none", "disclosed"])
    def test_a_resolves_every_option(
        self, clause_set: ClauseSet, render_context: dict[str, object], value: str
    ) -> None:
        resolved = resolve(clause_set.get("rule11.a"), {**render_context, "value": value})
        assert resolved.body.strip()


class TestEffectiveDates:
    def test_g_is_out_of_force_for_fy_2022_23(self, clause_set: ClauseSet) -> None:
        # If this fails, the tool emits audit-trail reporting for comparative
        # years where the clause did not exist. See the file header note.
        assert clause_set.get("rule11.g").in_force(FY_2022_23) is False

    def test_g_is_in_force_for_fy_2025_26(self, clause_set: ClauseSet) -> None:
        assert clause_set.get("rule11.g").in_force(FY_2025_26) is True

    def test_document_filter_excludes_out_of_force_clauses(self, clause_set: ClauseSet) -> None:
        ids_2022 = {c.id for c in clause_set.for_document("auditors_report", FY_2022_23)}
        ids_2026 = {c.id for c in clause_set.for_document("auditors_report", FY_2025_26)}
        assert "rule11.g" not in ids_2022
        assert "rule11.g" in ids_2026

    def test_clauses_come_back_in_render_order(self, clause_set: ClauseSet) -> None:
        clauses = clause_set.for_document("auditors_report", FY_2025_26)
        assert [c.id for c in clauses] == ["rule11.a", "rule11.e", "rule11.f", "rule11.g"]

    def test_production_caro_is_in_statutory_order(self, production_clause_set: ClauseSet) -> None:
        # The applicability record and the annexure preamble come first and
        # carry no clause number; the numbered clauses start after them.
        numbers = [
            c.number
            for c in production_clause_set.for_document("caro_2020", FY_2025_26)
            if c.number
        ]
        assert numbers[0] == "(i)(a)(A)"
        assert numbers[-1] == "(xxi)"
        # The prototype's numbering shifted after (vii). This one does not.
        assert numbers[numbers.index("(vii)(b)") + 1] == "(viii)"


class TestValidation:
    def _clause(self, **overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "id": "test.x",
            "document": "caro_2020",
            "title": "Test",
            "variants": [{"when": "value == 'a'", "body": "A."}],
            "input": {
                "key": "test.x",
                "datatype": "select",
                "options": [{"value": "a"}, {"value": "b"}],
            },
        }
        return {**base, **overrides}

    def test_dead_control_is_rejected(self) -> None:
        # §18.3 / test_no_dead_controls — option 'b' selects no variant, so
        # setting it would change no document.
        problems = validate([clause_from_dict(self._clause())])
        assert any("dead control" in p for p in problems)

    def test_all_options_reachable_passes(self) -> None:
        clause = self._clause(
            variants=[
                {"when": "value == 'a'", "body": "A."},
                {"when": "value == 'b'", "body": "B."},
            ]
        )
        assert validate([clause_from_dict(clause)]) == []

    def test_fallback_variant_covers_every_option(self) -> None:
        clause = self._clause(variants=[{"body": "Anything."}])
        assert validate([clause_from_dict(clause)]) == []

    def test_duplicate_ids_rejected(self) -> None:
        clause = clause_from_dict(self._clause(variants=[{"body": "X."}]))
        problems = validate([clause, clause])
        assert any("duplicate clause id" in p for p in problems)

    def test_reversed_effective_dates_rejected(self) -> None:
        clause = clause_from_dict(
            self._clause(
                variants=[{"body": "X."}],
                effective_from="2025-04-01",
                effective_to="2021-04-01",
            )
        )
        assert any("effective_from is after" in p for p in validate([clause]))

    def test_select_without_options_rejected(self) -> None:
        clause = clause_from_dict(
            self._clause(
                variants=[{"body": "X."}],
                input={"key": "test.x", "datatype": "select"},
            )
        )
        assert any("select input needs options" in p for p in validate([clause]))

    def test_missing_required_field_rejected(self) -> None:
        with pytest.raises(ClauseValidationError, match="`title` is required"):
            clause_from_dict({"id": "x", "document": "d", "variants": [{"body": "b"}]})

    def test_unknown_carry_forward_policy_rejected(self) -> None:
        # 'auto' is not in the §6.1 vocabulary; only always/prompt/never are.
        with pytest.raises(ClauseValidationError, match="not one of"):
            clause_from_dict(
                self._clause(
                    variants=[{"body": "X."}],
                    input={"key": "k", "datatype": "text", "carry_forward": "auto"},
                )
            )


class TestUnresolvedClause:
    def test_no_matching_variant_is_a_hard_error(self) -> None:
        # §3.3 — a clause with no matching variant is a hard error, never a
        # silent skip. A silently skipped clause is a missing statutory
        # paragraph nobody notices.
        clause = clause_from_dict(
            {
                "id": "t.x",
                "document": "caro_2020",
                "title": "T",
                "variants": [{"when": "value == 'a'", "body": "A."}],
            }
        )
        with pytest.raises(UnresolvedClauseError, match="no variant"):
            select_variant(clause, {"value": "zzz"})
